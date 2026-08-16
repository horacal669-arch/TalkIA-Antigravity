import os
import sys
import time
import json
import logging
import threading
import asyncio
import uuid
import re
import telebot
import edge_tts
from groq import Groq

# ── RUTA BASE PARA PYINSTALLER O SCRIPT NORMAL ────────────
def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()
CONFIG_FILE = os.path.join(BASE_DIR, "config_traductor.json")
TARGETS_FILE = os.path.join(BASE_DIR, "user_target.json")

# ── LOGGING ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("bot_traductor")

# ── CARGA Y MANEJO DE CONFIGURACIÓN ───────────────────────
DEFAULT_CONFIG = {
    "TG_TOKEN": "8401365409:AAFLenDqSSR-SYfSfZFD6967zeTLgAzfMkw",
    "GROQ_API_KEY": "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",
    "ADMIN_IDS": [],
    "TRIAL_MODE": False,
    "MAX_TRIAL_TRANSLATIONS": 50,
    "TRIAL_USAGE": {}
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_CONFIG, **data}
        except Exception as e:
            log.error(f"Error al leer config_traductor.json: {e}")
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"Error al guardar config_traductor.json: {e}")

# ── PERSISTENCIA DE IDIOMAS SELECCIONADOS POR CHAT ────────
def load_user_targets():
    if os.path.exists(TARGETS_FILE):
        try:
            with open(TARGETS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Convert keys back to int for telegram chat_ids
                return {int(k): v for k, v in data.items()}
        except Exception as e:
            log.error(f"Error al leer user_target.json: {e}")
    return {}

def save_user_targets(targets):
    try:
        with open(TARGETS_FILE, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in targets.items()}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"Error al guardar user_target.json: {e}")

# ── VOCES Y TABLAS DE IDIOMAS ─────────────────────────────
VOICES = {
    "es": "es-AR-TomasNeural",
    "en": "en-US-ChristopherNeural",
    "ja": "ja-JP-KeitaNeural",
    "ru": "ru-RU-DmitryNeural",
    "zh": "zh-CN-YunxiNeural",
    "de": "de-DE-ConradNeural",
    "it": "it-IT-DiegoNeural",
    "fr": "fr-FR-HenriNeural",
    "pt": "pt-BR-AntonioNeural",
    "ko": "ko-KR-InJoonNeural",
    "he": "he-IL-AvriNeural",
    "hi": "hi-IN-MadhurNeural"
}

CODE_TO_LANG_NAME = {
    "es": "Spanish",
    "en": "English",
    "ja": "Japanese",
    "ru": "Russian",
    "zh": "Chinese",
    "de": "German",
    "it": "Italian",
    "fr": "French",
    "pt": "Portuguese",
    "ko": "Korean",
    "he": "Hebrew",
    "hi": "Hindi",
}

LANG_FLAGS = {
    "es": "🇦🇷", "en": "🇺🇸", "ja": "🇯🇵", "ru": "🇷🇺", "zh": "🇨🇳",
    "de": "🇩🇪", "it": "🇮🇹", "fr": "🇫🇷", "pt": "🇧🇷", "ko": "🇰🇷",
    "he": "🇮🇱", "hi": "🇮🇳"
}

FLAG_MAP = {
    "🇺🇸": "en", "🇫🇷": "fr", "🇧🇷": "pt", "🇯🇵": "ja", "🇷🇺": "ru",
    "🇩🇪": "de", "🇮🇱": "he", "🇮🇳": "hi", "🇨🇳": "zh", "🇮🇹": "it", "🇰🇷": "ko"
}

# ── TTS (Edge-TTS Sync wrapper) ───────────────────────────
def tts(text, voice, path):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(edge_tts.Communicate(text, voice).save(path))
    finally:
        loop.close()

# ── TRADUCCIÓN BIDIRECCIONAL INTELIGENTE (Groq Llama 3.3) ──
def process_bidirectional_translation(client, text, guest_code):
    target_guest_name = CODE_TO_LANG_NAME.get(guest_code, "English")
    prompt = f"""You are an expert bi-directional live translator for hotel reception staff.
Current active target language selected by staff: {target_guest_name} ({guest_code}).

Analyze the input text:
1. Detect the ISO 2-letter language code of the input text ("es", "pt", "en", "fr", "de", "it", "ja", "zh", "ru", "ko", "he", "hi", etc.).
2. If the input text is in Spanish ("es"), translate it into {target_guest_name} ({guest_code}). Set "direction": "es_to_guest" and "effective_guest_code": "{guest_code}".
3. If the input text is NOT in Spanish (e.g. Portuguese "pt", German "de", French "fr", English "en", etc.), translate it into fluent Spanish. Set "direction": "guest_to_es" and "effective_guest_code": <detected ISO 2-letter code>.

Input text: "{text}"

Return ONLY a raw valid JSON object without markdown or quotes around JSON in this exact format:
{{"detected_lang_code": "iso_code", "effective_guest_code": "iso_code", "direction": "es_to_guest" | "guest_to_es", "translation": "translated text"}}"""

    try:
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.1
        )
        content = r.choices[0].message.content.strip()
        
        # Limpiar posibles bloques markdown ```json
        content = re.sub(r'^```(?:json)?', '', content).strip('`').strip()
        m = re.search(r'\{.*\}', content, re.DOTALL)
        if m:
            data = json.loads(m.group())
            eff_code = data.get("effective_guest_code", guest_code).lower()
            # Validar que el código esté en nuestro diccionario
            if eff_code not in CODE_TO_LANG_NAME:
                eff_code = guest_code
            return data.get("direction", "es_to_guest"), data.get("translation", text), eff_code
        else:
            return "es_to_guest", content, guest_code
    except Exception as e:
        log.error(f"Error en llamada a Groq Llama 3.3: {e}")
        return "es_to_guest", text, guest_code

# ── TRANSCRIPCIÓN AUDIO CON WHISPER ────────────────────────
def transcribe_audio(client, audio_bytes):
    tmp_folder = os.path.join(os.environ.get("TEMP", get_base_dir()), "talkia_tmp")
    os.makedirs(tmp_folder, exist_ok=True)
    tmp_file = os.path.join(tmp_folder, f"tr_{uuid.uuid4().hex[:8]}.ogg")
    
    with open(tmp_file, "wb") as f:
        f.write(audio_bytes)
        
    try:
        with open(tmp_file, "rb") as f:
            r = client.audio.transcriptions.create(
                file=("audio.ogg", f, "audio/ogg"),
                model="whisper-large-v3-turbo",
                response_format="json"
            )
        return r.text.strip() if hasattr(r, 'text') else str(r).strip()
    except Exception as e:
        log.error(f"Error en transcripción Whisper: {e}")
        return ""
    finally:
        if os.path.exists(tmp_file):
            try: os.remove(tmp_file)
            except: pass

# ── TECLADO TELEGRAM ──────────────────────────────────────
def build_keyboard():
    m = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row(telebot.types.KeyboardButton("🇺🇸 EN"), telebot.types.KeyboardButton("🇫🇷 FR"), telebot.types.KeyboardButton("🇧🇷 PT"))
    m.row(telebot.types.KeyboardButton("🇯🇵 JA"), telebot.types.KeyboardButton("🇷🇺 RU"), telebot.types.KeyboardButton("🇩🇪 DE"))
    m.row(telebot.types.KeyboardButton("🇮🇱 HE"), telebot.types.KeyboardButton("🇮🇳 HI"), telebot.types.KeyboardButton("🇨🇳 ZH"))
    m.row(telebot.types.KeyboardButton("🇮🇹 IT"), telebot.types.KeyboardButton("🇰🇷 KO"))
    return m

# ── CONTROL DE MODO TRIAL (PRUEBA GRATUITA) ───────────────
def check_and_update_trial(config, chat_id):
    if not config.get("TRIAL_MODE", False):
        return True, 0
    
    usage = config.get("TRIAL_USAGE", {})
    chat_str = str(chat_id)
    current_count = usage.get(chat_str, 0)
    max_allowed = config.get("MAX_TRIAL_TRANSLATIONS", 50)
    
    if current_count >= max_allowed:
        return False, current_count
    
    usage[chat_str] = current_count + 1
    config["TRIAL_USAGE"] = usage
    save_config(config)
    return True, current_count + 1

# ── BOT PRINCIPAL ─────────────────────────────────────────
def start_bot():
    cfg = load_config()
    user_targets = load_user_targets()
    
    log.info("==================================================")
    log.info(" TalkIA PRO — Bot Traductor Personal Standalone")
    log.info("==================================================")
    log.info(f"Modo Trial Activo: {cfg.get('TRIAL_MODE', False)}")
    
    while True:
        try:
            bot = telebot.TeleBot(cfg["TG_TOKEN"], threaded=True)
            client = Groq(api_key=cfg["GROQ_API_KEY"])

            @bot.message_handler(commands=["start", "help"])
            def handle_start(msg):
                try:
                    chat_id = msg.chat.id
                    if chat_id not in user_targets:
                        user_targets[chat_id] = "en"
                        save_user_targets(user_targets)
                        
                    curr_code = user_targets[chat_id]
                    flag_icon = LANG_FLAGS.get(curr_code, "🇺🇸")
                    
                    trial_txt = ""
                    if cfg.get("TRIAL_MODE", False):
                        used = cfg.get("TRIAL_USAGE", {}).get(str(chat_id), 0)
                        max_cnt = cfg.get("MAX_TRIAL_TRANSLATIONS", 50)
                        trial_txt = f"\n\n⏳ *Modo Prueba Gratuita:* {used}/{max_cnt} traducciones utilizadas."

                    bot.send_message(
                        chat_id,
                        "🎙️ *TalkIA PRO — Traductor Personal en Vivo*\n\n"
                        "• Hablás en *español* ➔ Traduzco al idioma del huésped con voz.\n"
                        "• El huésped habla o escribe ➔ Traduzco al *español* con voz.\n\n"
                        f"Idioma actual del huésped: {flag_icon} *{curr_code.upper()}*\n\n"
                        "👇 *Seleccioná el idioma del huésped con las banderitas:*"+trial_txt,
                        parse_mode="Markdown",
                        reply_markup=build_keyboard()
                    )
                except Exception as e:
                    log.error(f"Error en /start: {e}")

            @bot.message_handler(func=lambda m: m.text and any(flag in m.text for flag in FLAG_MAP))
            def handle_flag_selection(msg):
                try:
                    chat_id = msg.chat.id
                    for flag, code in FLAG_MAP.items():
                        if flag in msg.text:
                            user_targets[chat_id] = code
                            save_user_targets(user_targets)
                            flag_icon = LANG_FLAGS.get(code, "🌍")
                            bot.send_message(
                                chat_id,
                                f"✅ *Idioma del Huésped activado:* {flag_icon} *{code.upper()}*\n\nMandá tu audio o texto. ¡Traduzco en vivo!",
                                parse_mode="Markdown"
                            )
                            return
                except Exception as e:
                    log.error(f"Error en selección de bandera: {e}")

            @bot.message_handler(content_types=["voice", "audio"])
            def handle_voice_message(msg):
                chat_id = msg.chat.id
                
                # Verificar Trial
                allowed, count = check_and_update_trial(cfg, chat_id)
                if not allowed:
                    bot.send_message(
                        chat_id,
                        "🔒 *Ha alcanzado el límite del período de prueba gratuita.*\n\n"
                        "Para activar la versión ilimitada PRO de TalkIA, contacte a su proveedor.",
                        parse_mode="Markdown"
                    )
                    return
                
                guest_code = user_targets.get(chat_id, "en")
                tmp_out = os.path.join(os.environ.get("TEMP", get_base_dir()), f"out_{uuid.uuid4().hex[:8]}.mp3")
                status_msg = None
                
                try:
                    status_msg = bot.send_message(chat_id, "⏳ *Escuchando y traduciendo...*", parse_mode="Markdown")
                    file_id = msg.voice.file_id if msg.voice else (msg.audio.file_id if msg.audio else None)
                    if not file_id:
                        bot.edit_message_text("⚠️ Tipo de archivo no soportado. Por favor enviá una nota de voz.", chat_id, status_msg.message_id)
                        return

                    file_info = bot.get_file(file_id)
                    audio_bytes = bot.download_file(file_info.file_path)
                    
                    original_text = transcribe_audio(client, audio_bytes)
                    
                    if not original_text:
                        bot.edit_message_text("⚠️ No se pudo entender el audio. Por favor intentá hablar de nuevo.", chat_id, status_msg.message_id)
                        return

                    direction, translation, eff_code = process_bidirectional_translation(client, original_text, guest_code)
                    
                    # Si habló el huésped en su idioma, fijamos su idioma detectado para las siguientes respuestas
                    if direction == "guest_to_es":
                        user_targets[chat_id] = eff_code
                        save_user_targets(user_targets)

                    flag_icon = LANG_FLAGS.get(eff_code, "🌍")
                    
                    if direction == "es_to_guest":
                        voice_key = VOICES.get(eff_code, VOICES["en"])
                        header = f"🚀 *Vos (Español) ➔ {flag_icon} {eff_code.upper()}*"
                        header_plain = f"🚀 Vos (Español) ➔ {flag_icon} {eff_code.upper()}"
                    else:
                        voice_key = VOICES["es"]
                        header = f"🌍 *Huésped ({flag_icon} {eff_code.upper()}) ➔ 🇦🇷 ESPAÑOL*"
                        header_plain = f"🌍 Huésped ({flag_icon} {eff_code.upper()}) ➔ 🇦🇷 ESPAÑOL"

                    response_markdown = f"{header}\n\n_{original_text}_\n\n🗣️ *{translation}*"
                    response_plain = f"{header_plain}\n\n{original_text}\n\n🗣️ {translation}"

                    try: bot.delete_message(chat_id, status_msg.message_id)
                    except: pass
                        
                    try:
                        bot.send_message(chat_id, response_markdown, parse_mode="Markdown")
                    except:
                        bot.send_message(chat_id, response_plain)

                    def send_voice_async():
                        try:
                            tts(translation, voice_key, tmp_out)
                            if os.path.exists(tmp_out):
                                with open(tmp_out, "rb") as f_voice:
                                    bot.send_voice(chat_id, f_voice)
                        except Exception as tts_err:
                            log.error(f"Error generando audio TTS: {tts_err}")
                        finally:
                            if os.path.exists(tmp_out):
                                try: os.remove(tmp_out)
                                except: pass

                    threading.Thread(target=send_voice_async, daemon=True).start()

                except Exception as err:
                    log.error(f"Error procesando nota de voz: {err}")
                    if status_msg:
                        try: bot.edit_message_text(f"❌ Error al traducir: {err}", chat_id, status_msg.message_id)
                        except: bot.send_message(chat_id, f"❌ Error al traducir: {err}")

            @bot.message_handler(func=lambda m: m.text and not m.text.startswith("/"))
            def handle_text_message(msg):
                chat_id = msg.chat.id
                
                # Verificar Trial
                allowed, count = check_and_update_trial(cfg, chat_id)
                if not allowed:
                    bot.send_message(
                        chat_id,
                        "🔒 *Ha alcanzado el límite del período de prueba gratuita.*\n\n"
                        "Para activar la versión ilimitada PRO de TalkIA, contacte a su proveedor.",
                        parse_mode="Markdown"
                    )
                    return

                guest_code = user_targets.get(chat_id, "en")
                tmp_out = os.path.join(os.environ.get("TEMP", get_base_dir()), f"out_{uuid.uuid4().hex[:8]}.mp3")
                
                try:
                    direction, translation, eff_code = process_bidirectional_translation(client, msg.text, guest_code)
                    
                    if direction == "guest_to_es":
                        user_targets[chat_id] = eff_code
                        save_user_targets(user_targets)

                    flag_icon = LANG_FLAGS.get(eff_code, "🌍")
                    
                    if direction == "es_to_guest":
                        voice_key = VOICES.get(eff_code, VOICES["en"])
                        header = f"💬 *Vos (Español) ➔ {flag_icon} {eff_code.upper()}*"
                    else:
                        voice_key = VOICES["es"]
                        header = f"💬 *Huésped ({flag_icon} {eff_code.upper()}) ➔ 🇦🇷 ESPAÑOL*"

                    bot.send_message(
                        chat_id,
                        f"{header}\n\n*{translation}*",
                        parse_mode="Markdown"
                    )
                    
                    def send_voice_async():
                        try:
                            tts(translation, voice_key, tmp_out)
                            if os.path.exists(tmp_out):
                                with open(tmp_out, "rb") as f_voice:
                                    bot.send_voice(chat_id, f_voice)
                        except Exception as tts_err:
                            log.error(f"Error en TTS de texto: {tts_err}")
                        finally:
                            if os.path.exists(tmp_out):
                                try: os.remove(tmp_out)
                                except: pass

                    threading.Thread(target=send_voice_async, daemon=True).start()

                except Exception as e:
                    log.error(f"Error procesando mensaje de texto: {e}")

            log.info("Bot Traductor en línea y listo para recibir audios/textos.")
            bot.polling(none_stop=True, interval=0, timeout=20)

        except Exception as global_err:
            log.error(f"[RECONEXIÓN AUTOMÁTICA] Error en polling: {global_err}")
            time.sleep(5)

if __name__ == "__main__":
    start_bot()
