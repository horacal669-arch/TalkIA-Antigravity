import os, re, uuid, json, logging, threading, asyncio, time
import telebot
import edge_tts
import requests as req_lib
from groq import Groq

# ── CONFIG ──────────────────────────────────────────────
TG_TOKEN_HOTEL = os.environ.get("TG_TOKEN_HOTEL","8377451943:AAFMqMO6GEXGeGbo6JTXXUWeLGYrXzrMyfc")
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY","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")
TG_CHAT_HOTEL  = os.environ.get("TG_CHAT","6618443331")
WEB_BASE       = os.environ.get("WEB_BASE","http://localhost:5000")

client = Groq(api_key=GROQ_API_KEY)
bot    = telebot.TeleBot(TG_TOKEN_HOTEL, threaded=True)
telebot.logger.setLevel(logging.CRITICAL)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("bot_hotel")

VOICES = {
    "es":"es-AR-TomasNeural","en":"en-US-ChristopherNeural",
    "ja":"ja-JP-KeitaNeural","ru":"ru-RU-DmitryNeural",
    "zh":"zh-CN-YunxiNeural","de":"de-DE-ConradNeural",
    "it":"it-IT-DiegoNeural","fr":"fr-FR-HenriNeural",
    "pt":"pt-BR-AntonioNeural","he":"he-IL-AvriNeural","hi":"hi-IN-MadhurNeural"
}

LANG_NAMES = {
    "es":"español","en":"inglés","ja":"japonés","ru":"ruso",
    "zh":"chino","de":"alemán","it":"italiano","fr":"francés",
    "pt":"portugués","he":"hebreo","hi":"hindi"
}

def tts(text, voice, path):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:    loop.run_until_complete(edge_tts.Communicate(text, voice).save(path))
    finally: loop.close()

# ── MAIN KEYBOARD ────────────────────────────────────────
def main_keyboard():
    m = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row(
        telebot.types.KeyboardButton("📊 Reporte del Turno"),
        telebot.types.KeyboardButton("🏨 Consultar Habitación")
    )
    m.row(
        telebot.types.KeyboardButton("🔄 Resetear Turno"),
        telebot.types.KeyboardButton("📋 Últimas Solicitudes")
    )
    return m

# ── START ────────────────────────────────────────────────
@bot.message_handler(commands=["start"])
def start(msg):
    bot.send_message(msg.chat.id,
        "🏨 *TalkIA Hotel Bot*\n\n"
        "Acá vas a recibir las notificaciones de los huéspedes "
        "y podés consultar el estado del turno.",
        parse_mode="Markdown",
        reply_markup=main_keyboard())

# ── REPORTE DEL TURNO ─────────────────────────────────────
@bot.message_handler(func=lambda m: "Reporte del Turno" in m.text)
def shift_report(msg):
    bot.send_message(msg.chat.id, "⏳ Generando reporte...")
    try:
        r = req_lib.get(f"{WEB_BASE}/api/report", timeout=10)
        report = r.json().get("report","Sin datos")
        bot.send_message(msg.chat.id, report, parse_mode="Markdown")
        # Audio del resumen de satisfacción
        r2 = req_lib.get(f"{WEB_BASE}/api/stats", timeout=5)
        stats = r2.json()
        sentiment = stats.get("sentiment",{"positive":0,"neutral":0,"negative":0})
        total = sum(sentiment.values()) or 1
        sat = round(sentiment.get("positive",0)/total*100)
        total_req = stats.get("total",0)
        audio_text = f"Reporte del turno. {total_req} solicitudes atendidas. Nivel de satisfacción: {sat} por ciento."
        tmp = f"/tmp/report_{uuid.uuid4().hex[:6]}.mp3"
        tts(audio_text, VOICES["es"], tmp)
        with open(tmp,"rb") as f:
            bot.send_voice(msg.chat.id, f)
        if os.path.exists(tmp): os.remove(tmp)
    except Exception as e:
        bot.send_message(msg.chat.id, f"❌ Error: {e}")

# ── CONSULTAR HABITACION ──────────────────────────────────
@bot.message_handler(func=lambda m: "Consultar Habitación" in m.text)
def ask_room(msg):
    bot.send_message(msg.chat.id,
        "¿Qué habitación querés consultar?\nEscribí el número:",
        reply_markup=telebot.types.ForceReply())

@bot.message_handler(func=lambda m: m.reply_to_message and "qué habitación" in m.reply_to_message.text.lower())
def show_room(msg):
    room = msg.text.strip()
    try:
        r = req_lib.get(f"{WEB_BASE}/api/rooms", timeout=5)
        rooms = r.json().get("rooms",{})
        if room not in rooms:
            bot.send_message(msg.chat.id, f"❌ Habitación *{room}* sin actividad.", parse_mode="Markdown")
            return
        info = rooms[room]
        lang = info.get("lang","en")
        lang_name = LANG_NAMES.get(lang, lang)
        reqs = info.get("requests",[])
        pending = [r for r in reqs if r.get("status")=="pending"]
        rating = info.get("rating")
        stars = "⭐"*rating if rating else "Sin calificación"

        lines = [
            f"🏨 *Habitación {room}*",
            f"🌍 Idioma: {lang_name}",
            f"⭐ Calificación: {stars}",
            f"📋 Total solicitudes: {len(reqs)}",
            f"⏳ Pendientes: {len(pending)}",
        ]
        if info.get("notes"):
            lines.append(f"📝 Nota: _{info['notes']}_")
        if reqs:
            lines.append("")
            lines.append("*Últimas solicitudes:*")
            for req in reqs[:5]:
                status = "✅" if req.get("status")=="done" else "⏳"
                lines.append(f"{status} {req.get('icon','')} {req.get('summary_es','')} ({req.get('time','')})")

        bot.send_message(msg.chat.id, "\n".join(lines), parse_mode="Markdown", reply_markup=main_keyboard())
    except Exception as e:
        bot.send_message(msg.chat.id, f"❌ Error: {e}")

# ── ULTIMAS SOLICITUDES ───────────────────────────────────
@bot.message_handler(func=lambda m: "Últimas Solicitudes" in m.text)
def last_requests(msg):
    try:
        r = req_lib.get(f"{WEB_BASE}/api/stats", timeout=5)
        stats = r.json()
        reqs = stats.get("requests",[])[:10]
        if not reqs:
            bot.send_message(msg.chat.id, "Sin solicitudes registradas.", reply_markup=main_keyboard())
            return
        lines = ["📋 *Últimas 10 solicitudes:*",""]
        for req in reqs:
            lang = req.get("lang","?").upper()
            lines.append(f"• Hab. {req.get('room','?')} [{lang}] {req.get('time','')} — {req.get('text','')[:50]}")
        bot.send_message(msg.chat.id, "\n".join(lines), parse_mode="Markdown", reply_markup=main_keyboard())
    except Exception as e:
        bot.send_message(msg.chat.id, f"❌ Error: {e}")

# ── RESETEAR TURNO ────────────────────────────────────────
@bot.message_handler(func=lambda m: "Resetear Turno" in m.text)
def reset_shift(msg):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("✅ Sí, resetear", callback_data="confirm_reset"),
        telebot.types.InlineKeyboardButton("❌ Cancelar", callback_data="cancel_reset")
    )
    bot.send_message(msg.chat.id,
        "⚠️ ¿Seguro que querés resetear el turno?\n"
        "Se borrarán las estadísticas del día y el historial de habitaciones.",
        reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data in ["confirm_reset","cancel_reset"])
def handle_reset(call):
    if call.data == "confirm_reset":
        try:
            req_lib.post(f"{WEB_BASE}/api/reset-shift", timeout=5)
            bot.answer_callback_query(call.id, "✅ Turno reseteado")
            bot.send_message(call.message.chat.id,
                "🔄 *Turno reseteado.* Estadísticas en cero. Listo para el nuevo turno.",
                parse_mode="Markdown", reply_markup=main_keyboard())
        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ Error: {e}")
    else:
        bot.answer_callback_query(call.id, "Cancelado")
        bot.send_message(call.message.chat.id, "Operación cancelada.", reply_markup=main_keyboard())

log.info("Bot Hotel TalkIA — ONLINE")
while True:
    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        log.error(f"Conexion: {e}")
        time.sleep(5)
