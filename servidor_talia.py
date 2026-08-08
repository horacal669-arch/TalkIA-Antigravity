import os, re, time, json, base64, asyncio, threading, requests, smtplib, uuid
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from groq import Groq
import edge_tts

# ── CONFIG ──────────────────────────────────────────────
GROQ_API_KEY   = os.environ.get('GROQ_API_KEY','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')
TG_TOKEN_HOTEL = os.environ.get('TG_TOKEN_HOTEL','8377451943:AAFMqMO6GEXGeGbo6JTXXUWeLGYrXzrMyfc')
TG_TOKEN_BOT   = os.environ.get('TG_TOKEN','8401365409:AAFLenDqSSR-SYfSfZFD6967zeTLgAzfMkw')
TG_CHAT_HOTEL  = os.environ.get('TG_CHAT','6618443331')
REPORT_EMAIL   = os.environ.get('REPORT_EMAIL','soyhorazio@gmail.com')

client = Groq(api_key=GROQ_API_KEY)
app    = Flask(__name__)
CORS(app)

AUDIO_FOLDER   = 'responses'
PHOTOS_FOLDER  = 'photos'
STATS_FILE     = 'stats.json'
ROOMS_FILE     = 'rooms.json'
CONFIG_FILE    = 'hotel_config.json'
REPORTS_FOLDER = 'reports'
TG_COUNT_FILE  = 'tg_count.json'

for folder in [AUDIO_FOLDER, PHOTOS_FOLDER, REPORTS_FOLDER]:
    os.makedirs(folder, exist_ok=True)

VOICES = {
    "es":"es-AR-TomasNeural","en":"en-US-ChristopherNeural",
    "ja":"ja-JP-KeitaNeural","ru":"ru-RU-DmitryNeural",
    "zh":"zh-CN-YunxiNeural","de":"de-DE-ConradNeural",
    "it":"it-IT-DiegoNeural","fr":"fr-FR-HenriNeural",
    "pt":"pt-BR-AntonioNeural","he":"he-IL-AvriNeural","hi":"hi-IN-MadhurNeural",
    "ko":"ko-KR-InJoonNeural"
}

LANG_NAMES = {
    "es":"español","en":"inglés","ja":"japonés","ru":"ruso",
    "zh":"chino","de":"alemán","it":"italiano","fr":"francés",
    "pt":"portugués","he":"hebreo","hi":"hindi"
}

ICONS = {
    "coffee":"☕","cleaning":"🧹","taxi":"🚕","towels":"🛁",
    "dinner":"🍽️","wakeup":"⏰","wifi":"📶","emergency":"🚨",
    "tips":"🗺️","weather":"🌤️","general":"💬","complaint":"😤",
    "suggestion":"💡","photo":"📸","info":"ℹ️"
}

GUEST_PROMPT = """Eres TalkIA, Concierge de Lujo de un hotel en Ushuaia, Patagonia Argentina.
REGLA ABSOLUTA: Responde SIEMPRE en el idioma indicado. NUNCA en español salvo que el huesped hable español.
Sé breve, cálido y profesional. Máximo 2 oraciones.
Si pide algo concreto confirma que el staff fue notificado.
Devuelve SOLO este JSON sin backticks:
{"response_text":"respuesta en el idioma del huesped","lang_code":"codigo_iso","request_type":"general","summary_es":"resumen breve en español","sentiment":"positive|neutral|negative"}
request_type: coffee, cleaning, taxi, towels, dinner, wakeup, wifi, emergency, tips, weather, complaint, suggestion, photo, info, general"""

# ── FILE HELPERS ─────────────────────────────────────────
def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(default, dict) and isinstance(data, dict):
                    return {**default, **data}
                return data
        except: pass
    return dict(default) if isinstance(default, dict) else default

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_config():
    return load_json(CONFIG_FILE, {
        "hotel_name":"Mi Hotel","notify_telegram":True,"primary_color":"#d4a843",
        "breakfast_time":"07:00 - 10:00","checkout_time":"12:00","checkin_time":"14:00",
        "wifi_password":"","activities":"","hotel_info":""
    })

def load_stats():
    return load_json(STATS_FILE, {
        "day":"","today":{},"total":0,"by_lang":{},"by_type":{},"by_hour":{},
        "requests":[],"ratings":[],"complaints":[],"suggestions":[],
        "sentiment":{"positive":0,"neutral":0,"negative":0}
    })

def load_rooms():
    return load_json(ROOMS_FILE, {"rooms":{}})

def run_tts_sync(text, voice, filepath):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:    loop.run_until_complete(edge_tts.Communicate(text, voice).save(filepath))
    finally: loop.close()

def translate_text(text, from_lang, to_lang):
    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role":"user","content":
            f"Translate from {from_lang} to {to_lang}. Return ONLY the translation, natural and fluent.\n\nText: {text}"}],
        max_tokens=400, temperature=0.2)
    return r.choices[0].message.content.strip()

def parse_json_safe(text):
    text = re.sub(r'```(?:json)?','',text).strip('`').strip()
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m: return json.loads(m.group())
    raise ValueError(f"JSON invalido: {text}")

def get_weather():
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast?latitude=-54.8&longitude=-68.3"
            "&current=temperature_2m,weathercode,windspeed_10m&timezone=America/Argentina/Ushuaia",timeout=5)
        d = r.json()['current']
        codes={0:"despejado",1:"mayormente despejado",2:"parcialmente nublado",
               3:"nublado",51:"llovizna",61:"lluvia leve",71:"nieve",80:"lluvias",95:"tormenta"}
        return {"temp":d['temperature_2m'],"wind":d['windspeed_10m'],"desc":codes.get(d['weathercode'],"variable")}
    except: return None

def register_stat(room, lang_code, req_type, summary_es, sentiment='neutral'):
    s = load_stats()
    today = datetime.now().strftime('%Y-%m-%d')
    hour  = datetime.now().strftime('%H')
    if s.get('day') != today: s['today']={};s['day']=today;s['by_hour']={}
    s['today'][req_type] = s['today'].get(req_type,0)+1
    s['total'] = s.get('total',0)+1
    s['by_lang'][lang_code] = s['by_lang'].get(lang_code,0)+1
    s['by_type'][req_type]  = s['by_type'].get(req_type,0)+1
    s.setdefault('by_hour',{})[hour] = s['by_hour'].get(hour,0)+1
    s.setdefault('sentiment',{"positive":0,"neutral":0,"negative":0})
    s['sentiment'][sentiment] = s['sentiment'].get(sentiment,0)+1
    entry={"time":datetime.now().strftime('%H:%M'),"room":room,"lang":lang_code,
           "type":req_type,"text":summary_es[:80],"sentiment":sentiment}
    s.setdefault('requests',[]).insert(0,entry)
    s['requests']=s['requests'][:100]
    if req_type=='complaint':
        s.setdefault('complaints',[]).insert(0,{"time":datetime.now().strftime('%H:%M'),"room":room,"text":summary_es[:100]})
        s['complaints']=s['complaints'][:20]
    if req_type=='suggestion':
        s.setdefault('suggestions',[]).insert(0,{"time":datetime.now().strftime('%H:%M'),"room":room,"text":summary_es[:100]})
        s['suggestions']=s['suggestions'][:20]
    save_json(STATS_FILE,s)

def register_room_request(room, lang_code, req_type, summary_es, response_text, sentiment='neutral', audio_url=None):
    data=load_rooms(); rooms=data.get('rooms',{})
    if room not in rooms:
        rooms[room]={"lang":lang_code,"requests":[],"notes":"","checkin":datetime.now().strftime('%Y-%m-%d'),"rating":None}
    rooms[room]['lang']=lang_code
    entry={"time":datetime.now().strftime('%H:%M'),"timestamp":int(time.time()),
           "date":datetime.now().strftime('%Y-%m-%d'),"type":req_type,
           "icon":ICONS.get(req_type,"💬"),"summary_es":summary_es[:100],
           "response":response_text[:100],"sentiment":sentiment,"audio_url":audio_url,
           "status":"pending" if req_type not in ['general','weather','tips','suggestion','info'] else "info"}
    rooms[room].setdefault('requests',[]).insert(0,entry)
    rooms[room]['requests']=rooms[room]['requests'][:50]
    data['rooms']=rooms; save_json(ROOMS_FILE,data)

def notify_telegram_hotel(room, req_type, summary_es, lang_code, sentiment='neutral'):
    cfg=load_config()
    if not cfg.get('notify_telegram',True): return
    icon=ICONS.get(req_type,"💬")
    lang_name=LANG_NAMES.get(lang_code,lang_code)
    if req_type=='emergency':   msg=f"🚨🚨 *EMERGENCIA* — Hab. *{room}* 🚨🚨\n_{summary_es}_"
    elif req_type=='complaint': msg=f"😤 *QUEJA* — Hab. *{room}* [{lang_name}]\n_{summary_es}_"
    elif req_type=='photo':     msg=f"📸 *FOTO* — Hab. *{room}* [{lang_name}]\n_{summary_es}_"
    else:                       msg=f"{icon} *Hab. {room}* — {lang_name}\n_{summary_es}_"
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN_HOTEL}/sendMessage",
                      json={"chat_id":TG_CHAT_HOTEL,"text":msg,"parse_mode":"Markdown"},timeout=5)
        tmp=f"tg_{int(time.time())}.mp3"
        run_tts_sync(summary_es,VOICES['es'],tmp)
        with open(tmp,'rb') as f:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN_HOTEL}/sendVoice",
                         data={"chat_id":TG_CHAT_HOTEL},files={"voice":f},timeout=15)
        if os.path.exists(tmp): os.remove(tmp)
    except Exception as e: print(f"[TG ERROR] {e}")

def send_email_report():
    try:
        s=load_stats(); cfg=load_config()
        fn=f"reporte_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        save_json(os.path.join(REPORTS_FOLDER,fn),{
            "hotel":cfg.get('hotel_name','Hotel'),"fecha":datetime.now().strftime('%d/%m/%Y %H:%M'),
            "total":s.get('total',0),"sentiment":s.get('sentiment',{}),
            "quejas":s.get('complaints',[]),"sugerencias":s.get('suggestions',[]),
            "by_lang":s.get('by_lang',{}),"by_type":s.get('by_type',{}),"by_hour":s.get('by_hour',{})
        })
        print(f"[REPORT] Guardado: {fn}")
    except Exception as e: print(f"[REPORT ERROR] {e}")

def build_excel_report():
    s=load_stats()
    lines=["Habitacion,Idioma,Tipo,Texto,Hora,Fecha,Sentimiento"]
    for r in s.get('requests',[]):
        lines.append(f"{r.get('room','')},{r.get('lang','')},{r.get('type','')},\"{r.get('text','').replace(chr(34),chr(39))}\",{r.get('time','')},{s.get('day','')},{r.get('sentiment','')}")
    return "\n".join(lines)

# ── BOT TRADUCTOR PERSONAL ────────────────────────────────
def start_bot_traductor():
    try:
        import telebot
        bot = telebot.TeleBot(TG_TOKEN_BOT, threaded=True)

        LANG_FLAGS = {"es":"🇦🇷","en":"🇺🇸","ja":"🇯🇵","ru":"🇷🇺","zh":"🇨🇳",
                      "de":"🇩🇪","it":"🇮🇹","fr":"🇫🇷","pt":"🇧🇷","ko":"🇰🇷","he":"🇮🇱","hi":"🇮🇳"}
        FLAG_MAP   = {"🇺🇸":"en","🇫🇷":"fr","🇧🇷":"pt","🇯🇵":"ja","🇷🇺":"ru",
                      "🇩🇪":"de","🇮🇱":"he","🇮🇳":"hi","🇨🇳":"zh","🇮🇹":"it","🇰🇷":"ko"}
        user_target = {}

        def tts_bot(text, voice, path):
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            try:    loop.run_until_complete(edge_tts.Communicate(text, voice).save(path))
            finally: loop.close()

        def transcribe_bot(audio_bytes):
            tmp = f"/tmp/tr_{uuid.uuid4().hex[:8]}.ogg"
            with open(tmp,"wb") as f: f.write(audio_bytes)
            try:
                with open(tmp,"rb") as f:
                    r = client.audio.transcriptions.create(
                        file=("audio.ogg",f,"audio/ogg"),
                        model="whisper-large-v3-turbo",response_format="verbose_json")
                return r.text.strip(), r.language[:2]
            finally:
                if os.path.exists(tmp): os.remove(tmp)

        def translate_bot(text, from_lang, to_lang):
            r = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role":"user","content":f"Translate from {from_lang} to {to_lang}. Return ONLY the translation.\n\nText: {text}"}],
                max_tokens=500, temperature=0.2)
            return r.choices[0].message.content.strip()

        def keyboard():
            m = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            m.row(telebot.types.KeyboardButton("🇺🇸 EN"),telebot.types.KeyboardButton("🇫🇷 FR"),telebot.types.KeyboardButton("🇧🇷 PT"))
            m.row(telebot.types.KeyboardButton("🇯🇵 JA"),telebot.types.KeyboardButton("🇷🇺 RU"),telebot.types.KeyboardButton("🇩🇪 DE"))
            m.row(telebot.types.KeyboardButton("🇮🇱 HE"),telebot.types.KeyboardButton("🇮🇳 HI"),telebot.types.KeyboardButton("🇨🇳 ZH"))
            m.row(telebot.types.KeyboardButton("🇮🇹 IT"),telebot.types.KeyboardButton("🇰🇷 KO"))
            return m

        @bot.message_handler(commands=["start"])
        def start(msg):
            user_target[msg.chat.id]="en"
            bot.send_message(msg.chat.id,
                "🎙️ *Traductor Personal TalkIA*\n\n"
                "Hablás en *español* → traduzco al idioma del huésped\n"
                "El huésped habla → traduzco al *español*\n\n"
                "Elegí el idioma del huésped 👇",
                parse_mode="Markdown", reply_markup=keyboard())

        @bot.message_handler(func=lambda m: any(f in m.text for f in FLAG_MAP))
        def set_lang(msg):
            for flag, code in FLAG_MAP.items():
                if flag in msg.text:
                    user_target[msg.chat.id]=code
                    bot.send_message(msg.chat.id,
                        f"Idioma: *{LANG_FLAGS.get(code,'')} {code.upper()}*\n\nMandá el audio.",
                        parse_mode="Markdown")
                    return

        @bot.message_handler(content_types=["voice"])
        def handle_voice(msg):
            chat_id=msg.chat.id; target=user_target.get(chat_id,"en")
            out=f"/tmp/tr_out_{uuid.uuid4().hex[:8]}.mp3"
            status=bot.send_message(chat_id,"Traduciendo...")
            try:
                fi=bot.get_file(msg.voice.file_id); audio=bot.download_file(fi.file_path)
                original,detected=transcribe_bot(audio)
                if detected=="es":
                    translation=translate_bot(original,"Spanish",target)
                    voice_key=VOICES.get(target,VOICES["en"]); flag=LANG_FLAGS.get(target,"")
                    texto=f"Vos a {flag} {target.upper()}\n\n_{original}_\n\n*{translation}*"
                else:
                    user_target[chat_id]=detected
                    translation=translate_bot(original,detected,"Spanish")
                    voice_key=VOICES["es"]; flag=LANG_FLAGS.get(detected,"")
                    texto=f"Huesped {flag} {detected.upper()} a ES\n\n_{original}_\n\n*{translation}*"
                bot.delete_message(chat_id,status.message_id)
                bot.send_message(chat_id,texto,parse_mode="Markdown")
                def send_audio():
                    try:
                        tts_bot(translation,voice_key,out)
                        with open(out,"rb") as f: bot.send_voice(chat_id,f)
                    except: pass
                    finally:
                        if os.path.exists(out): os.remove(out)
                threading.Thread(target=send_audio,daemon=True).start()
            except Exception as e:
                try: bot.edit_message_text(f"Error: {e}",chat_id,status.message_id)
                except: bot.send_message(chat_id,f"Error: {e}")

        print("[BOT TRADUCTOR] ONLINE")
        while True:
            try: bot.polling(none_stop=True,interval=0,timeout=20)
            except Exception as e:
                print(f"[BOT TRADUCTOR] {e}")
                time.sleep(5)
    except Exception as e:
        print(f"[BOT TRADUCTOR FATAL] {e}")

# Arrancar bot en thread al iniciar
threading.Thread(target=start_bot_traductor, daemon=True).start()

# ── MAIN ENDPOINT ────────────────────────────────────────
@app.route('/process-request', methods=['POST'])
def process_request():
    try:
        data=request.json; text_query=data.get('text'); audio_b64=data.get('audio')
        lang_hint=data.get('lang','en'); room=data.get('room','N/D')
        detected_lang=lang_hint; user_text=""

        if audio_b64:
            audio_data=base64.b64decode(audio_b64)
            tmp=f"tmp_{int(time.time())}.webm"
            with open(tmp,'wb') as f: f.write(audio_data)
            try:
                with open(tmp,'rb') as f:
                    tr=client.audio.transcriptions.create(
                        file=(tmp,f,"audio/webm"),model="whisper-large-v3-turbo",response_format="verbose_json")
                detected_lang=getattr(tr,'language','en')[:2]; user_text=tr.text
            finally:
                if os.path.exists(tmp): os.remove(tmp)
        elif text_query:
            user_text=text_query; detected_lang=lang_hint
        else:
            return jsonify({"status":"error","message":"Sin contenido"}),400

        lang_name=LANG_NAMES.get(detected_lang,detected_lang)
        user_content=(f"Habitacion: {room}.\nIdioma del huesped: {lang_name} (codigo: {detected_lang}). "
                      f"DEBES responder OBLIGATORIAMENTE en {lang_name}.\n\n"
                      f"El huesped {'dijo' if audio_b64 else 'escribio'}: {user_text}")

        cfg=load_config()
        if any(w in user_text.lower() for w in ['breakfast','desayuno','checkout','wifi','password','horario']):
            user_content+=(f"\n\nInfo hotel: Desayuno {cfg.get('breakfast_time','7-10h')}, "
                           f"Checkout {cfg.get('checkout_time','12:00')}, WiFi: {cfg.get('wifi_password','consultar')}. {cfg.get('hotel_info','')}")
        if any(w in user_text.lower() for w in ['weather','clima','tiempo']):
            w=get_weather()
            if w: user_content+=f"\n\nClima Ushuaia: {w['temp']}C, {w['desc']}, viento {w['wind']} km/h."

        resp=client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system","content":GUEST_PROMPT},{"role":"user","content":user_content}],
            max_tokens=400,temperature=0.2)

        res=parse_json_safe(resp.choices[0].message.content)
        text_out=res.get('response_text','Thank you.')
        det_lang=res.get('lang_code',detected_lang)
        req_type=res.get('request_type','general')
        summary_es=res.get('summary_es',user_text[:80])
        sentiment=res.get('sentiment','neutral')

        if det_lang != 'es':
            try: summary_es=translate_text(user_text[:150],det_lang,'Spanish')
            except: pass

        voice=VOICES.get(det_lang,VOICES['en'])
        filename=f"res_{int(time.time())}.mp3"
        filepath=os.path.join(AUDIO_FOLDER,filename)
        tts=threading.Thread(target=run_tts_sync,args=(text_out,voice,filepath))
        tts.start(); tts.join(timeout=15)
        audio_url=f"/audio-response/{filename}"

        filename_es=f"res_es_{int(time.time())}.mp3"
        filepath_es=os.path.join(AUDIO_FOLDER,filename_es)
        tts_es=threading.Thread(target=run_tts_sync,args=(summary_es,VOICES['es'],filepath_es))
        tts_es.start(); tts_es.join(timeout=15)
        audio_url_es=f"/audio-response/{filename_es}"

        threading.Thread(target=register_stat,args=(room,det_lang,req_type,summary_es,sentiment),daemon=True).start()
        threading.Thread(target=register_room_request,args=(room,det_lang,req_type,summary_es,text_out,sentiment,audio_url_es),daemon=True).start()
        threading.Thread(target=notify_telegram_hotel,args=(room,req_type,summary_es,det_lang,sentiment),daemon=True).start()

        return jsonify({"status":"success","text":text_out,"summary_es":summary_es,
                        "lang_code":det_lang,"audio_url":audio_url,"request_type":req_type})
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({"status":"error","message":str(e)}),500

@app.route('/api/photo', methods=['POST'])
def upload_photo():
    try:
        data=request.json; photo_b64=data.get('photo',''); room=data.get('room','?')
        lang=data.get('lang','en'); desc=data.get('description','')
        img_data=base64.b64decode(photo_b64)
        filename=f"photo_{room}_{int(time.time())}.jpg"
        filepath=os.path.join(PHOTOS_FOLDER,filename)
        with open(filepath,'wb') as f: f.write(img_data)
        photo_url=f"/photos/{filename}"
        desc_es=translate_text(desc,lang,'Spanish') if desc and lang!='es' else desc
        summary=f"Foto hab. {room}: {desc_es}" if desc_es else f"Foto hab. {room}"
        threading.Thread(target=notify_telegram_hotel,args=(room,'photo',summary,lang),daemon=True).start()
        threading.Thread(target=register_stat,args=(room,lang,'photo',summary,'neutral'),daemon=True).start()
        threading.Thread(target=register_room_request,args=(room,lang,'photo',summary,'Foto recibida','neutral',photo_url),daemon=True).start()
        def send_photo_tg():
            try:
                with open(filepath,'rb') as f:
                    requests.post(f"https://api.telegram.org/bot{TG_TOKEN_HOTEL}/sendPhoto",
                                 data={"chat_id":TG_CHAT_HOTEL,"caption":f"Hab. {room}: {desc_es}"},
                                 files={"photo":f},timeout=15)
            except: pass
        threading.Thread(target=send_photo_tg,daemon=True).start()
        return jsonify({"status":"ok","photo_url":photo_url,"summary":summary})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}),500

@app.route('/photos/<filename>')
def serve_photo(filename): return send_from_directory(PHOTOS_FOLDER,filename)

@app.route('/api/rooms/<room>/reply', methods=['POST'])
def staff_reply(room):
    try:
        data=request.json; message_es=data.get('message','')
        rooms_data=load_rooms(); guest_lang=rooms_data.get('rooms',{}).get(room,{}).get('lang','en')
        translated=translate_text(message_es,'Spanish',guest_lang) if guest_lang!='es' else message_es
        voice=VOICES.get(guest_lang,VOICES['en'])
        filename=f"reply_{room}_{int(time.time())}.mp3"
        filepath=os.path.join(AUDIO_FOLDER,filename)
        tts=threading.Thread(target=run_tts_sync,args=(translated,voice,filepath))
        tts.start(); tts.join(timeout=15)
        audio_url=f"/audio-response/{filename}"
        if room in rooms_data.get('rooms',{}):
            entry={"time":datetime.now().strftime('%H:%M'),"timestamp":int(time.time()),
                   "date":datetime.now().strftime('%Y-%m-%d'),"type":"staff_reply","icon":"💬",
                   "summary_es":f"Staff: {message_es[:80]}","response":translated,
                   "audio_url":audio_url,"status":"info","sentiment":"neutral","delivered":False}
            rooms_data['rooms'][room].setdefault('requests',[]).insert(0,entry)
            save_json(ROOMS_FILE,rooms_data)
        return jsonify({"status":"ok","translated":translated,"lang":guest_lang,"audio_url":audio_url})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}),500

@app.route('/api/rooms/<room>/reply-audio', methods=['POST'])
def staff_reply_audio(room):
    try:
        data=request.json; audio_b64=data.get('audio',''); guest_lang=data.get('guest_lang','en')
        audio_data=base64.b64decode(audio_b64)
        tmp=f"tmp_staff_{int(time.time())}.webm"
        with open(tmp,'wb') as f: f.write(audio_data)
        try:
            with open(tmp,'rb') as f:
                tr=client.audio.transcriptions.create(
                    file=(tmp,f,"audio/webm"),model="whisper-large-v3-turbo",response_format="text")
            message_es=tr
        finally:
            if os.path.exists(tmp): os.remove(tmp)
        translated=translate_text(message_es,'Spanish',guest_lang) if guest_lang!='es' else message_es
        voice=VOICES.get(guest_lang,VOICES['en'])
        filename=f"reply_{room}_{int(time.time())}.mp3"
        filepath=os.path.join(AUDIO_FOLDER,filename)
        tts=threading.Thread(target=run_tts_sync,args=(translated,voice,filepath))
        tts.start(); tts.join(timeout=15)
        audio_url=f"/audio-response/{filename}"
        rooms_data=load_rooms()
        if room in rooms_data.get('rooms',{}):
            entry={"time":datetime.now().strftime('%H:%M'),"timestamp":int(time.time()),
                   "date":datetime.now().strftime('%Y-%m-%d'),"type":"staff_reply","icon":"🎙️",
                   "summary_es":f"Staff audio: {message_es[:80]}","response":translated,
                   "audio_url":audio_url,"status":"info","sentiment":"neutral","delivered":False}
            rooms_data['rooms'][room].setdefault('requests',[]).insert(0,entry)
            save_json(ROOMS_FILE,rooms_data)
        return jsonify({"status":"ok","transcribed":message_es,"translated":translated,"lang":guest_lang,"audio_url":audio_url})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}),500

@app.route('/api/rooms/<room>/pending')
def get_pending(room):
    data=load_rooms(); rooms=data.get('rooms',{})
    if room not in rooms: return jsonify({"messages":[]})
    reqs=rooms[room].get('requests',[])
    pending=[r for r in reqs if r.get('type')=='staff_reply' and r.get('delivered')==False]
    if pending:
        for r in reqs:
            if r.get('type')=='staff_reply' and r.get('delivered')==False: r['delivered']=True
        data['rooms']=rooms; save_json(ROOMS_FILE,data)
    return jsonify({"messages":pending})

@app.route('/api/rooms/<room>/notes', methods=['POST'])
def update_notes(room):
    data=load_rooms(); rooms=data.get('rooms',{})
    if room not in rooms: rooms[room]={"lang":"en","requests":[],"notes":""}
    rooms[room]['notes']=request.json.get('notes','')
    data['rooms']=rooms; save_json(ROOMS_FILE,data)
    return jsonify({"status":"ok"})

@app.route('/api/rooms')
def api_rooms(): return jsonify(load_rooms())

@app.route('/api/rooms/<room>/reset', methods=['POST'])
def reset_room(room):
    data=load_rooms()
    if room in data.get('rooms',{}): data['rooms'][room]['requests']=[]; save_json(ROOMS_FILE,data)
    return jsonify({"status":"ok"})

@app.route('/api/rooms/<room>/request/<int:idx>/done', methods=['POST'])
def mark_done(room,idx):
    data=load_rooms()
    try: data['rooms'][room]['requests'][idx]['status']='done'; save_json(ROOMS_FILE,data)
    except: pass
    return jsonify({"status":"ok"})

@app.route('/api/report')
def api_report():
    s=load_stats(); cfg=load_config()
    sent=s.get('sentiment',{"positive":0,"neutral":0,"negative":0})
    total_sent=sum(sent.values()) or 1
    sat=round(sent.get('positive',0)/total_sent*100)
    return jsonify({"hotel":cfg.get('hotel_name','Hotel'),"fecha":datetime.now().strftime('%d/%m/%Y %H:%M'),
                    "total":s.get('total',0),"satisfaccion":sat,"sentiment":sent,
                    "by_lang":s.get('by_lang',{}),"by_type":s.get('by_type',{}),"by_hour":s.get('by_hour',{}),
                    "quejas":s.get('complaints',[]),"sugerencias":s.get('suggestions',[])})

@app.route('/api/report/save', methods=['POST'])
def api_save_report():
    threading.Thread(target=send_email_report,daemon=True).start()
    return jsonify({"status":"ok"})

@app.route('/api/report/list')
def list_reports():
    try: files=sorted(os.listdir(REPORTS_FOLDER),reverse=True)[:10]
    except: files=[]
    return jsonify({"reports":files})

@app.route('/api/report/download/<filename>')
def download_report(filename):
    fp=os.path.join(REPORTS_FOLDER,filename)
    if not os.path.exists(fp): return jsonify({"error":"not found"}),404
    with open(fp,encoding='utf-8') as f: content=f.read()
    return Response(content,mimetype='application/json',
                    headers={"Content-Disposition":f"attachment; filename={filename}"})

@app.route('/api/report/excel')
def download_excel():
    csv=build_excel_report()
    return Response(csv,mimetype='text/csv',
                    headers={"Content-Disposition":f"attachment; filename=reporte_{datetime.now().strftime('%Y%m%d')}.csv"})

@app.route('/api/reset-shift', methods=['POST'])
def api_reset_shift():
    threading.Thread(target=send_email_report,daemon=True).start()
    s=load_stats()
    s['today']={};s['day']=datetime.now().strftime('%Y-%m-%d')
    s['sentiment']={"positive":0,"neutral":0,"negative":0}
    s['by_hour']={};s['complaints']=[];s['suggestions']=[];s['ratings']=[]
    save_json(STATS_FILE,s); save_json(ROOMS_FILE,{"rooms":{}})
    return jsonify({"status":"ok"})

@app.route('/api/rating', methods=['POST'])
def save_rating():
    data=request.json; s=load_stats()
    s.setdefault('ratings',[]).append({"stars":data.get('stars',5),"room":data.get('room','?'),"time":datetime.now().strftime('%H:%M')})
    save_json(STATS_FILE,s)
    rd=load_rooms(); room=data.get('room','?')
    if room in rd.get('rooms',{}): rd['rooms'][room]['rating']=data.get('stars',5); save_json(ROOMS_FILE,rd)
    return jsonify({"status":"ok"})

@app.route('/api/complaint', methods=['POST'])
def save_complaint():
    data=request.json; text=data.get('text',''); room=data.get('room','?')
    lang=data.get('lang','en'); comp_type=data.get('type','complaint')
    try: text_es=translate_text(text,lang,'Spanish') if lang!='es' else text
    except: text_es=text
    icon="😤" if comp_type=='complaint' else "💡"
    label="QUEJA" if comp_type=='complaint' else "SUGERENCIA"
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN_HOTEL}/sendMessage",
                      json={"chat_id":TG_CHAT_HOTEL,"text":f"{icon} *{label}* — Hab. *{room}*\n_{text_es}_","parse_mode":"Markdown"},timeout=5)
    except: pass
    s=load_stats()
    entry={"time":datetime.now().strftime('%H:%M'),"room":room,"text":text_es[:100]}
    if comp_type=='complaint':
        s.setdefault('complaints',[]).insert(0,entry); s['complaints']=s['complaints'][:20]
        s.setdefault('by_type',{})['complaint']=s['by_type'].get('complaint',0)+1
        s.setdefault('sentiment',{"positive":0,"neutral":0,"negative":0})['negative']+=1
    else:
        s.setdefault('suggestions',[]).insert(0,entry); s['suggestions']=s['suggestions'][:20]
        s.setdefault('by_type',{})['suggestion']=s['by_type'].get('suggestion',0)+1
    save_json(STATS_FILE,s)
    return jsonify({"status":"ok"})

@app.route('/api/stats')
def api_stats(): return jsonify(load_stats())

@app.route('/api/config', methods=['GET','POST'])
def api_config():
    if request.method=='POST':
        cfg=load_config()
        for k,v in request.json.items(): cfg[k]=v
        save_json(CONFIG_FILE,cfg); return jsonify({"status":"ok"})
    return jsonify(load_config())

@app.route('/api/weather')
def api_weather():
    w=get_weather()
    return jsonify(w) if w else jsonify({"error":"no data"}),503

@app.route('/audio-response/<filename>')
def serve_audio(filename): return send_from_directory(AUDIO_FOLDER,filename)

@app.route('/')
def serve_index(): return send_from_directory('.','index.html')

@app.route('/<path:path>')
def serve_static(path): return send_from_directory('.',path)

if __name__=='__main__':
    print("="*45); print("  TalkIA — ONLINE"); print("="*45)
    port=int(os.environ.get('PORT',5000))
    app.run(host='0.0.0.0',port=port,debug=False)
