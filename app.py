import os
import json
import uuid
import logging
import threading
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from ai_engine import ai_engine
from database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("app")

app = Flask(__name__)
CORS(app)

AUDIO_FOLDER = "audio_responses"
os.makedirs(AUDIO_FOLDER, exist_ok=True)

# ── PÁGINAS HTML ────────────────────────────────────────────
@app.route("/")
def home():
    return send_from_directory(".", "login.html")

@app.route("/guest/<room_id>")
def guest_page(room_id):
    return send_from_directory(".", "guest.html")

@app.route("/panel")
def staff_panel():
    return send_from_directory(".", "panel.html")

@app.route("/config")
def config_page():
    return send_from_directory(".", "config.html")

@app.route("/qr")
def qr_page():
    return send_from_directory(".", "qr_generator.html")

@app.route("/audio_responses/<path:filename>")
def serve_audio(filename):
    return send_from_directory(AUDIO_FOLDER, filename)

# ── API: CONFIGURACIÓN DEL HOTEL ────────────────────────────
@app.route("/api/config", methods=["GET"])
def api_get_config():
    return jsonify(db.load_config())

@app.route("/api/config", methods=["POST"])
def api_save_config():
    data = request.json
    db.save_config(data)
    return jsonify({"success": True})

# ── API: AGENTE DE IA (CHAT TEXTO) ──────────────────────────
@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.json
    room_id = data.get("room", "000")
    text = data.get("text", "")
    target_lang = data.get("lang", "es")

    if not text:
        return jsonify({"error": "Texto vacío"}), 400

    config = db.load_config()
    hotel_name = config.get("hotel_name", "Hotel")
    context = f"Hotel: {hotel_name}. Habitación: {room_id}."

    result = ai_engine.process_guest_message(
        text=text,
        source_lang="auto",
        target_lang=target_lang,
        context_info=context
    )

    response_text = result.get("response_translated", text)
    summary_es = result.get("summary_es", text)
    detected_lang = result.get("detected_lang", "en")
    request_type = result.get("request_type", "general")
    sentiment = result.get("sentiment", "neutral")

    db.record_request(room_id, detected_lang, request_type, summary_es, sentiment)

    audio_url = None
    try:
        audio_filename = f"resp_{uuid.uuid4().hex[:8]}.mp3"
        audio_path = os.path.join(AUDIO_FOLDER, audio_filename)
        success = ai_engine.generate_tts_voice(response_text, detected_lang, audio_path)
        if success:
            audio_url = f"/audio_responses/{audio_filename}"
    except Exception as e:
        log.error(f"Error generando audio: {e}")

    return jsonify({
        "response": response_text,
        "summary_es": summary_es,
        "detected_lang": detected_lang,
        "request_type": request_type,
        "sentiment": sentiment,
        "audio_url": audio_url
    })

# ── API: AGENTE DE IA (VOZ / AUDIO) ─────────────────────────
@app.route("/api/voice", methods=["POST"])
def api_voice():
    if "audio" not in request.files:
        return jsonify({"error": "No se recibió audio"}), 400

    room_id = request.form.get("room", "000")
    audio_file = request.files["audio"]
    audio_bytes = audio_file.read()

    if not audio_bytes:
        return jsonify({"error": "Audio vacío"}), 400

    original_text, detected_lang = ai_engine.transcribe_audio(audio_bytes)

    if not original_text:
        return jsonify({"error": "No se pudo entender el audio"}), 400

    config = db.load_config()
    hotel_name = config.get("hotel_name", "Hotel")
    context = f"Hotel: {hotel_name}. Habitación: {room_id}."

    result = ai_engine.process_guest_message(
        text=original_text,
        source_lang=detected_lang,
        target_lang="es" if detected_lang != "es" else "en",
        context_info=context
    )

    response_text = result.get("response_translated", original_text)
    summary_es = result.get("summary_es", original_text)
    request_type = result.get("request_type", "general")
    sentiment = result.get("sentiment", "neutral")

    db.record_request(room_id, detected_lang, request_type, summary_es, sentiment)

    audio_url = None
    try:
        audio_filename = f"voice_{uuid.uuid4().hex[:8]}.mp3"
        audio_path = os.path.join(AUDIO_FOLDER, audio_filename)
        resp_lang = detected_lang if detected_lang != "es" else "es"
        success = ai_engine.generate_tts_voice(response_text, resp_lang, audio_path)
        if success:
            audio_url = f"/audio_responses/{audio_filename}"
    except Exception as e:
        log.error(f"Error generando audio de voz: {e}")

    return jsonify({
        "original": original_text,
        "response": response_text,
        "summary_es": summary_es,
        "detected_lang": detected_lang,
        "request_type": request_type,
        "sentiment": sentiment,
        "audio_url": audio_url
    })

# ── API: SERVICIOS RÁPIDOS ───────────────────────────────────
@app.route("/api/service", methods=["POST"])
def api_service():
    data = request.json
    room_id = data.get("room", "000")
    service_type = data.get("type", "general")
    lang = data.get("lang", "en")
    note = data.get("note", "")

    ICONS = {
        "coffee": "☕", "cleaning": "🧹", "taxi": "🚕", "towels": "🛁",
        "dinner": "🍽️", "wakeup": "⏰", "wifi": "📶", "emergency": "🚨"
    }
    icon = ICONS.get(service_type, "💬")
    summary = f"{icon} Hab. {room_id}: Solicitud de {service_type}"
    if note:
        summary += f" — {note}"

    entry = db.record_request(room_id, lang, service_type, summary, "neutral")
    return jsonify({"success": True, "entry": entry})

# ── API: EXCURSIONES Y TOURS ─────────────────────────────────
@app.route("/api/tours", methods=["GET"])
def api_get_tours():
    return jsonify(db.load_tours())

@app.route("/api/tours", methods=["POST"])
def api_add_tour():
    data = request.json
    tour = db.add_tour(
        title=data.get("title", ""),
        price_usd=data.get("price_usd", 0),
        duration=data.get("duration", ""),
        description=data.get("description", ""),
        photo=data.get("photo", "")
    )
    return jsonify({"success": True, "tour": tour})

@app.route("/api/tours/<tour_id>", methods=["DELETE"])
def api_delete_tour(tour_id):
    db.delete_tour(tour_id)
    return jsonify({"success": True})

# ── API: AMENITIES (SPA, SAUNA, YOGA, PISCINA, COMBIS) ──────
@app.route("/api/amenities", methods=["GET"])
def api_get_amenities():
    amenities = db.load_amenities()
    reservations = db.load_reservations()
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")

    for amenity in amenities:
        for slot in amenity.get("slots", []):
            booked = sum(1 for r in reservations
                        if r.get("item_name") == amenity["name"]
                        and r.get("time_slot") == slot
                        and r.get("date") == today
                        and r.get("status") == "confirmed")
            # no modificamos el slot, dejamos que el frontend calcule disponibilidad

    return jsonify({
        "amenities": amenities,
        "reservations": [r for r in reservations if r.get("date") == today and r.get("status") == "confirmed"]
    })

# ── API: RESERVAS ────────────────────────────────────────────
@app.route("/api/reserve", methods=["POST"])
def api_reserve():
    data = request.json
    room_id = data.get("room", "000")
    item_name = data.get("item_name", "")
    time_slot = data.get("time_slot", "")

    result = db.make_reservation(room_id, item_name, time_slot)

    if result.get("success"):
        summary = f"🎫 Hab. {room_id}: Reserva {item_name} a las {time_slot}"
        db.record_request(room_id, "es", "reservation", summary, "positive")

    return jsonify(result)

@app.route("/api/cancel", methods=["POST"])
def api_cancel():
    data = request.json
    res_id = data.get("reservation_id", "")
    reason = data.get("reason", "Cancelación del huésped")
    result = db.cancel_reservation(res_id, reason)
    return jsonify(result)

# ── API: RESEÑAS Y ESTRELLITAS ───────────────────────────────
@app.route("/api/review", methods=["POST"])
def api_review():
    data = request.json
    room_id = data.get("room", "000")
    stars = data.get("stars", 5)
    comment = data.get("comment", "")
    category = data.get("category", "rating")

    avg = db.record_review(room_id, stars, comment, category)
    return jsonify({"success": True, "average_stars": avg})

# ── API: ESTADÍSTICAS PARA PANEL DE RECEPCIÓN ────────────────
@app.route("/api/stats", methods=["GET"])
def api_stats():
    return jsonify(db.load_stats())

@app.route("/api/reviews", methods=["GET"])
def api_reviews():
    return jsonify(db.load_reviews())

@app.route("/api/rooms", methods=["GET"])
def api_rooms():
    return jsonify(db.load_rooms())

# ── INICIAR SERVIDOR ─────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    log.info("=" * 50)
    log.info("  TalkIA Antigravity — Servidor Iniciado")
    log.info(f"  http://localhost:{port}")
    log.info("=" * 50)
    app.run(host="0.0.0.0", port=port, debug=False)
