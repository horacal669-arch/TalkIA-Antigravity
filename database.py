import os
import json
import logging
from datetime import datetime

log = logging.getLogger("database")

CONFIG_FILE = "hotel_config.json"
ROOMS_FILE = "rooms.json"
STATS_FILE = "stats.json"
REVIEWS_FILE = "reviews.json"
TOURS_FILE = "tours.json"

class Database:
    def __init__(self):
        self._init_defaults()

    def _init_defaults(self):
        if not os.path.exists(CONFIG_FILE):
            self.save_config({
                "hotel_name": "Hotel Ushuaia Patagonia",
                "primary_color": "#d4a843",
                "accent_color": "#1e293b",
                "wifi_name": "Ushuaia_Guest_WiFi",
                "wifi_password": "Patagonia2026",
                "checkin_time": "14:00",
                "checkout_time": "11:00",
                "breakfast_time": "07:00 - 10:30",
                "notify_telegram": True,
                "mode": "hotel" # "hotel" or "tourism"
            })

        if not os.path.exists(ROOMS_FILE):
            self.save_rooms({
                "101": {"status": "occupied", "guest_lang": "en"},
                "102": {"status": "available", "guest_lang": "es"},
                "103": {"status": "occupied", "guest_lang": "pt"},
                "104": {"status": "occupied", "guest_lang": "fr"}
            })

        if not os.path.exists(STATS_FILE):
            self.save_stats({
                "total_requests": 0,
                "by_lang": {},
                "by_category": {},
                "requests": []
            })

        if not os.path.exists(REVIEWS_FILE):
            self.save_reviews({
                "ratings": [],
                "average_stars": 5.0,
                "complaints": [],
                "compliments": [],
                "suggestions": []
            })

        if not os.path.exists(TOURS_FILE):
            self.save_tours([
                {"id": "t1", "name": "Tren del Fin del Mundo", "price_usd": 45, "duration": "4 hs"},
                {"id": "t2", "name": "Navegación Canal Beagle (Isla de Lobos)", "price_usd": 60, "duration": "3 hs"},
                {"id": "t3", "name": "Excursión Parque Nacional Tierra del Fuego", "price_usd": 50, "duration": "5 hs"},
                {"id": "t4", "name": "Aventura 4x4 Lagos Fagnano y Escondido", "price_usd": 90, "duration": "Full Day"}
            ])

    def _read_json(self, filepath, default):
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                log.error(f"Error leyendo {filepath}: {e}")
        return default

    def _write_json(self, filepath, data):
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"Error escribiendo {filepath}: {e}")

    # Configuración
    def load_config(self):
        return self._read_json(CONFIG_FILE, {})

    def save_config(self, data):
        self._write_json(CONFIG_FILE, data)

    # Habitaciones / QRs
    def load_rooms(self):
        return self._read_json(ROOMS_FILE, {"rooms": {}})

    def save_rooms(self, data):
        self._write_json(ROOMS_FILE, data)

    # Estadísticas y Solicitudes
    def load_stats(self):
        return self._read_json(STATS_FILE, {})

    def save_stats(self, data):
        self._write_json(STATS_FILE, data)

    def record_request(self, room_id, lang_code, request_type, summary_es, sentiment="neutral"):
        stats = self.load_stats()
        stats["total_requests"] = stats.get("total_requests", 0) + 1
        
        stats.setdefault("by_lang", {})
        stats["by_lang"][lang_code] = stats["by_lang"].get(lang_code, 0) + 1

        stats.setdefault("by_category", {})
        stats["by_category"][request_type] = stats["by_category"].get(request_type, 0) + 1

        new_entry = {
            "id": f"req_{int(datetime.now().timestamp())}",
            "time": datetime.now().strftime("%H:%M"),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "room": room_id,
            "lang": lang_code,
            "type": request_type,
            "summary": summary_es,
            "sentiment": sentiment,
            "status": "pending"
        }

        stats.setdefault("requests", []).insert(0, new_entry)
        stats["requests"] = stats["requests"][:100]
        self.save_stats(stats)
        return new_entry

    # Reseñas, Estrellitas y Reclamos
    def load_reviews(self):
        return self._read_json(REVIEWS_FILE, {})

    def save_reviews(self, data):
        self._write_json(REVIEWS_FILE, data)

    def record_review(self, room_id, stars, comment="", category="rating"):
        reviews = self.load_reviews()
        entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "room": room_id,
            "stars": int(stars),
            "comment": comment
        }
        
        reviews.setdefault("ratings", []).insert(0, entry)
        
        # Calcular promedio de estrellitas
        all_stars = [r["stars"] for r in reviews["ratings"] if "stars" in r]
        if all_stars:
            reviews["average_stars"] = round(sum(all_stars) / len(all_stars), 1)

        if stars <= 2 or category == "complaint":
            reviews.setdefault("complaints", []).insert(0, entry)
        elif stars == 5 or category == "compliment":
            reviews.setdefault("compliments", []).insert(0, entry)
        elif category == "suggestion":
            reviews.setdefault("suggestions", []).insert(0, entry)

        self.save_reviews(reviews)
        return reviews["average_stars"]

    # Tours y Excursiones (Para expansión a empresas de turismo)
    def load_tours(self):
        return self._read_json(TOURS_FILE, [])

    def save_tours(self, data):
        self._write_json(TOURS_FILE, data)

db = Database()
