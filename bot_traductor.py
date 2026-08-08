import os
import time
import logging
import threading
import asyncio
import uuid
import telebot
import edge_tts
from groq import Groq

# ── LOGGING ──────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("bot_traductor")

# ── CONFIGURACIÓN Y CLAVES ────────────────────────────────
TG_TOKEN = os.environ.get("TG_TOKEN", "8401365409:AAFLenDqSSR-SYfSfZFD6967zeTLgAzfMkw")
GROQ_KEY = os.environ.get("GROQ_API_KEY", "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")

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

LANG_FLAGS = {
    "es": "🇦🇷", "en": "🇺🇸", "ja": "🇯🇵", "ru": "🇷🇺", "zh": "🇨🇳",
    "de": "🇩🇪", "it": "🇮🇹", "fr": "🇫🇷", "pt": "🇧🇷", "ko": "🇰🇷",
    "he": "🇮🇱", "hi": "🇮🇳"
}

FLAG_MAP = {
    "🇺🇸": "en", "🇫🇷": "fr", "🇧🇷": "pt", "🇯🇵": "ja", "🇷🇺": "ru",
    "🇩🇪": "de", "🇮🇱": "he", "🇮🇳": "hi", "🇨🇳": "zh", "🇮🇹": "it", "🇰🇷": "ko"
}

# Almacena el idioma seleccionado por usuario de Telegram
user_target = {}

def get_groq_client():
    return Groq(api_key=GROQ_KEY)

def tts(text, voice, path):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(edge_tts.Communicate(text, voice).save(path))
    finally:
        loop.close()

def transcribe(client, audio_bytes):
    tmp_folder = os.path.join(os.environ.get("TEMP", os.getcwd()), "talkia_tmp")
    os.makedirs(tmp_folder, exist_ok=True)
    tmp_file = os.path.join(tmp_folder, f"tr_{uuid.uuid4().hex[:8]}.ogg")
    
    with open(tmp_file, "wb") as f:
        f.write(audio_bytes)
        
    try:
        with open(tmp_file, "rb") as f:
            r = client.audio.transcriptions.create(
                file=("audio.ogg", f, "audio/ogg"),
                model="whisper-large-v3-turbo",
                response_format="verbose_json"
            )
        detected_lang = r.language[:2] if hasattr(r, 'language') and r.language else "en"
        return r.text.strip(), detected_lang
    finally:
        if os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
            except:
                pass

def translate_text(client, text, from_lang, to_lang):
    try:
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "user",
                "content": f"Translate natural spoken dialogue from {from_lang} to {to_lang}. Return ONLY the direct translation without extra commentary or quotes.\n\nText: {text}"
            }],
            max_tokens=500,
            temperature=0.2
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        log.error(f"Error en traduccion Groq: {e}")
        return text

def build_keyboard():
    m = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row(telebot.types.KeyboardButton("🇺🇸 EN"), telebot.types.KeyboardButton("🇫🇷 FR"), telebot.types.KeyboardButton("🇧🇷 PT"))
    m.row(telebot.types.KeyboardButton("🇯🇵 JA"), telebot.types.KeyboardButton("🇷🇺 RU"), telebot.types.KeyboardButton("🇩🇪 DE"))
    m.row(telebot.types.KeyboardButton("🇮🇱 HE"), telebot.types.KeyboardButton("🇮🇳 HI"), telebot.types.KeyboardButton("🇨🇳 ZH"))
    m.row(telebot.types.KeyboardButton("🇮🇹 IT"), telebot.types.KeyboardButton("🇰🇷 KO"))
    return m

def start_bot():
    log.info("Iniciando Bot Traductor Personal de Telegram...")
    
    while True:
        try:
            bot = telebot.TeleBot(TG_TOKEN, threaded=True)
            client = get_groq_client()

            @bot.message_handler(commands=["start", "help"])
            def handle_start(msg):
                try:
                    user_target[msg.chat.id] = "en"
                    bot.send_message(
                        msg.chat.id,
                        "🎙️ *TalkIA PRO — Traductor Personal en Vivo*\n\n"
                        "• Hablás en *español* ➔ Traduzco al idioma del huésped con voz.\n"
                        "• El huésped habla su idioma ➔ Traduzco al *español* con voz.\n\n"
                        "👇 *Seleccioná el idioma del huésped:*",
                        parse_mode="Markdown",
                        reply_markup=build_keyboard()
                    )
                except Exception as e:
                    log.error(f"Error en /start: {e}")

            @bot.message_handler(func=lambda m: m.text and any(flag in m.text for flag in FLAG_MAP))
            def handle_flag_selection(msg):
                try:
                    for flag, code in FLAG_MAP.items():
                        if flag in msg.text:
                            user_target[msg.chat.id] = code
                            flag_icon = LANG_FLAGS.get(code, "🌍")
                            bot.send_message(
                                msg.chat.id,
                                f"✅ *Idioma del Huésped activado:* {flag_icon} *{code.upper()}*\n\nMandá tu audio o texto.",
                                parse_mode="Markdown"
                            )
                            return
                except Exception as e:
                    log.error(f"Error cambiando idioma: {e}")

            @bot.message_handler(content_types=["voice", "audio"])
            def handle_voice_message(msg):
                chat_id = msg.chat.id
                target_lang = user_target.get(chat_id, "en")
                tmp_out = os.path.join(os.environ.get("TEMP", os.getcwd()), f"out_{uuid.uuid4().hex[:8]}.mp3")
                status_msg = None
                
                try:
                    status_msg = bot.send_message(chat_id, "⏳ *Escuchando y traduciendo...*", parse_mode="Markdown")
                    file_info = bot.get_file(msg.voice.file_id)
                    audio_bytes = bot.download_file(file_info.file_path)
                    
                    original_text, detected_lang = transcribe(client, audio_bytes)
                    
                    if not original_text:
                        bot.edit_message_text("⚠️ No se pudo entender el audio, intenta de nuevo.", chat_id, status_msg.message_id)
                        return

                    # Si hablas español -> traducir al idioma del huésped
                    if detected_lang == "es":
                        translation = translate_text(client, original_text, "Spanish", target_lang)
                        voice_key = VOICES.get(target_lang, VOICES["en"])
                        flag_icon = LANG_FLAGS.get(target_lang, "🌍")
                        response_markdown = f"🚀 *Vos (Español) ➔ {flag_icon} {target_lang.upper()}*\n\n_{original_text}_\n\n🗣️ *{translation}*"
                    else:
                        # Si habla el huésped -> traducir al español
                        user_target[chat_id] = detected_lang
                        translation = translate_text(client, original_text, detected_lang, "Spanish")
                        voice_key = VOICES["es"]
                        flag_icon = LANG_FLAGS.get(detected_lang, "🌍")
                        response_markdown = f"🌍 *Huésped {flag_icon} {detected_lang.upper()} ➔ Español*\n\n_{original_text}_\n\n🗣️ *{translation}*"

                    try:
                        bot.delete_message(chat_id, status_msg.message_id)
                    except:
                        pass
                        
                    bot.send_message(chat_id, response_markdown, parse_mode="Markdown")

                    def send_voice_async():
                        try:
                            tts(translation, voice_key, tmp_out)
                            if os.path.exists(tmp_out):
                                with open(tmp_out, "rb") as f_voice:
                                    bot.send_voice(chat_id, f_voice)
                        except Exception as tts_err:
                            log.error(f"Error generando TTS: {tts_err}")
                        finally:
                            if os.path.exists(tmp_out):
                                try: os.remove(tmp_out)
                                except: pass

                    threading.Thread(target=send_voice_async, daemon=True).start()

                except Exception as err:
                    log.error(f"Error procesando voz: {err}")
                    if status_msg:
                        try: bot.edit_message_text(f"❌ Error al traducir: {err}", chat_id, status_msg.message_id)
                        except: bot.send_message(chat_id, f"❌ Error al traducir: {err}")

            @bot.message_handler(func=lambda m: m.text and not m.text.startswith("/"))
            def handle_text_message(msg):
                chat_id = msg.chat.id
                target_lang = user_target.get(chat_id, "en")
                try:
                    translation = translate_text(client, msg.text, "Spanish / Any", target_lang)
                    flag_icon = LANG_FLAGS.get(target_lang, "🌍")
                    bot.send_message(
                        chat_id,
                        f"💬 *Traducción ➔ {flag_icon} {target_lang.upper()}*\n\n*{translation}*",
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    log.error(f"Error en texto: {e}")

            log.info("Bot Traductor Personal en línea y listo para recibir audios.")
            bot.polling(none_stop=True, interval=0, timeout=20)

        except Exception as global_err:
            log.error(f"[RECONEXIÓN AUTOMÁTICA] Ocurrió un error en el polling: {global_err}")
            time.sleep(5)

if __name__ == "__main__":
    start_bot()
