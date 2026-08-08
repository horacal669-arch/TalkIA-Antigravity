import os, uuid, logging, threading, asyncio, time
import telebot, edge_tts
from groq import Groq

TELEGRAM_TOKEN = os.environ.get("TG_TOKEN","8401365409:AAFLenDqSSR-SYfSfZFD6967zeTLgAzfMkw")
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY","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")

client = Groq(api_key=GROQ_API_KEY)
bot    = telebot.TeleBot(TELEGRAM_TOKEN, threaded=True)
telebot.logger.setLevel(logging.CRITICAL)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("traductor")

VOICES = {
    "es":"es-AR-TomasNeural","en":"en-US-ChristopherNeural","ja":"ja-JP-KeitaNeural",
    "ru":"ru-RU-DmitryNeural","zh":"zh-CN-YunxiNeural","de":"de-DE-ConradNeural",
    "it":"it-IT-DiegoNeural","fr":"fr-FR-HenriNeural","pt":"pt-BR-AntonioNeural",
    "ko":"ko-KR-InJoonNeural","he":"he-IL-AvriNeural","hi":"hi-IN-MadhurNeural"
}
LANG_FLAGS = {"es":"🇦🇷","en":"🇺🇸","ja":"🇯🇵","ru":"🇷🇺","zh":"🇨🇳","de":"🇩🇪","it":"🇮🇹","fr":"🇫🇷","pt":"🇧🇷","ko":"🇰🇷","he":"🇮🇱","hi":"🇮🇳"}
FLAG_MAP   = {"🇺🇸":"en","🇫🇷":"fr","🇧🇷":"pt","🇯🇵":"ja","🇷🇺":"ru","🇩🇪":"de","🇮🇱":"he","🇮🇳":"hi","🇨🇳":"zh","🇮🇹":"it","🇰🇷":"ko"}

user_target = {}

def tts(text, voice, path):
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    try:    loop.run_until_complete(edge_tts.Communicate(text, voice).save(path))
    finally: loop.close()

def transcribe(audio_bytes):
    tmp = f"/tmp/tr_{uuid.uuid4().hex[:8]}.ogg"
    with open(tmp,"wb") as f: f.write(audio_bytes)
    try:
        with open(tmp,"rb") as f:
            r = client.audio.transcriptions.create(file=("audio.ogg",f,"audio/ogg"),model="whisper-large-v3-turbo",response_format="verbose_json")
        return r.text.strip(), r.language[:2]
    finally:
        if os.path.exists(tmp): os.remove(tmp)

def translate(text, from_lang, to_lang):
    r = client.chat.completions.create(model="llama-3.3-70b-versatile",messages=[{"role":"user","content":f"Translate from {from_lang} to {to_lang}. Return ONLY the translation.\n\nText: {text}"}],max_tokens=500,temperature=0.2)
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
    bot.send_message(msg.chat.id,"🎙️ *Traductor Personal TalkIA*\n\n• Si hablás en *español* → traduzco al idioma del huésped\n• Si el huésped habla → traduzco al *español*\n\nElegí el idioma del huésped 👇",parse_mode="Markdown",reply_markup=keyboard())

@bot.message_handler(func=lambda m: any(f in m.text for f in FLAG_MAP))
def set_lang(msg):
    for flag,code in FLAG_MAP.items():
        if flag in msg.text:
            user_target[msg.chat.id]=code
            bot.send_message(msg.chat.id,f"✅ Idioma: *{LANG_FLAGS.get(code,'')} {code.upper()}*\n\nMandá el audio.",parse_mode="Markdown")
            return

@bot.message_handler(content_types=["voice"])
def handle_voice(msg):
    chat_id=msg.chat.id
    target=user_target.get(chat_id,"en")
    out=f"/tmp/tr_out_{uuid.uuid4().hex[:8]}.mp3"
    status=bot.send_message(chat_id,"⏳ Traduciendo...")
    try:
        fi=bot.get_file(msg.voice.file_id)
        audio=bot.download_file(fi.file_path)
        original,detected=transcribe(audio)
        if detected=="es":
            translation=translate(original,"Spanish",target)
            voice=VOICES.get(target,VOICES["en"])
            flag=LANG_FLAGS.get(target,"🌍")
            texto=f"🚀 *Vos → {flag} {target.upper()}*\n\n_{original}_\n\n*{translation}*"
        else:
            user_target[chat_id]=detected
            translation=translate(original,detected,"Spanish")
            voice=VOICES["es"]
            flag=LANG_FLAGS.get(detected,"🌍")
            texto=f"🌍 *Huésped {flag} {detected.upper()} → ES*\n\n_{original}_\n\n*{translation}*"
        bot.delete_message(chat_id,status.message_id)
        bot.send_message(chat_id,texto,parse_mode="Markdown")
        def send_audio():
            try:
                tts(translation,voice,out)
                with open(out,"rb") as f: bot.send_voice(chat_id,f)
            except Exception as e: log.error(f"TTS: {e}")
            finally:
                if os.path.exists(out): os.remove(out)
        threading.Thread(target=send_audio,daemon=True).start()
    except Exception as e:
        log.error(f"Error: {e}")
        try: bot.edit_message_text(f"❌ {e}",chat_id,status.message_id)
        except: bot.send_message(chat_id,f"❌ {e}")

log.info("Traductor Personal — ONLINE")
while True:
    try: bot.polling(none_stop=True,interval=0,timeout=20)
    except Exception as e: log.error(f"Conexion: {e}"); time.sleep(5)
