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
RESERVATIONS_FILE = "reservations.json"
AMENITIES_FILE = "amenities.json"

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
                "shuttle_schedules": "09:00, 12:00, 15:00, 18:00, 21:00 (Combi al Centro)",
                "notify_telegram": True,
                "mode": "hotel"
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
                {
                    "id": "t1",
                    "title": "Navegación Canal Beagle e Isla de Lobos",
                    "price_usd": 60,
                    "duration": "3 hs",
                    "description": "Navegación por el Canal Beagle contemplando el Faro del Fin del Mundo e Isla de Lobos.",
                    "photo": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=500"
                },
                {
                    "id": "t2",
                    "title": "Trekking Laguna Esmeralda",
                    "price_usd": 55,
                    "duration": "5 hs",
                    "description": "Caminata entre bosques de lengas y turbales hasta la deslumbrante Laguna Esmeralda.",
                    "photo": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=500"
                },
                {
                    "id": "t3",
                    "title": "Excursión 4x4 Lagos Fagnano y Escondido",
                    "price_usd": 90,
                    "duration": "Full Day",
                    "description": "Aventura off-road cruzando la Cordillera de los Andes hasta los grandes lagos.",
                    "photo": "https://images.unsplash.com/photo-1519681393784-d120267933ba?w=500"
                }
            ])

        if not os.path.exists(AMENITIES_FILE):
            self.save_amenities([
                {"id": "a1", "name": "Spa & Sauna Seco", "max_capacity": 4, "slots": ["14:00", "15:30", "17:00", "18:30", "20:00"]},
                {"id": "a2", "name": "Piscina Climatizada", "max_capacity": 8, "slots": ["10:00", "12:00", "14:00", "16:00", "18:00", "20:00"]},
                {"id": "a3", "name": "Clase de Yoga & Relajación", "max_capacity": 6, "slots": ["08:30", "17:30"]},
                {"id": "a4", "name": "Mesa Restaurante / Cena", "max_capacity": 10, "slots": ["20:00", "21:30", "23:00"]},
                {"id": "a5", "name": "Combi Transfer al Centro / Aeropuerto", "max_capacity": 12, "slots": ["09:00", "12:00", "15:00", "18:00", "21:00"]}
            ])

        if not os.path.exists(RESERVATIONS_FILE):
            self.save_reservations([])

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

    # Configuración del Hotel
    def load_config(self):
        return self._read_json(CONFIG_FILE, {})

    def save_config(self, data):
        self._write_json(CONFIG_FILE, data)

    # Habitaciones y QRs
    def load_rooms(self):
        return self._read_json(ROOMS_FILE, {"rooms": {}})

    def save_rooms(self, data):
        self._write_json(ROOMS_FILE, data)

    # Excursiones y Tours Personalizados por Hotel / Hostal
    def load_tours(self):
        return self._read_json(TOURS_FILE, [])

    def save_tours(self, data):
        self._write_json(TOURS_FILE, data)

    def add_tour(self, title, price_usd, duration, description, photo=""):
        tours = self.load_tours()
        new_tour = {
            "id": f"t_{int(datetime.now().timestamp())}",
            "title": title,
            "price_usd": float(price_usd),
            "duration": duration,
            "description": description,
            "photo": photo or "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=500"
        }
        tours.append(new_tour)
        self.save_tours(tours)
        return new_tour

    def delete_tour(self, tour_id):
        tours = [t for t in self.load_tours() if t.get("id") != tour_id]
        self.save_tours(tours)

    # Instalaciones / Amenities (Spa, Sauna, Yoga, Piscina, Combis)
    def load_amenities(self):
        return self._read_json(AMENITIES_FILE, [])

    def save_amenities(self, data):
        self._write_json(AMENITIES_FILE, data)

    # Sistema de Reservas y Gestión de Cupos / Cancelaciones
    def load_reservations(self):
        return self._read_json(RESERVATIONS_FILE, [])

    def save_reservations(self, data):
        self._write_json(RESERVATIONS_FILE, data)

    def make_reservation(self, room_id, item_name, time_slot, date_str=None):
        date_str = date_str or datetime.now().strftime("%Y-%m-%d")
        reservations = self.load_reservations()

        # Verificar cupo disponible para esa hora
        existing_count = sum(1 for r in reservations if r.get("item_name") == item_name and r.get("time_slot") == time_slot and r.get("date") == date_str and r.get("status") == "confirmed")
        
        # Buscar capacidad máxima
        amenities = self.load_amenities()
        max_cap = 6
        for a in amenities:
            if a.get("name") == item_name:
                max_cap = a.get("max_capacity", 6)
                break

        if existing_count >= max_cap:
            return {"success": False, "message": f"Horario {time_slot} completo para {item_name}. Por favor elige otro horario."}

        new_res = {
            "id": f"res_{int(datetime.now().timestamp())}",
            "room": room_id,
            "item_name": item_name,
            "time_slot": time_slot,
            "date": date_str,
            "status": "confirmed",
            "created_at": datetime.now().strftime("%H:%M")
        }
        reservations.insert(0, new_res)
        self.save_reservations(reservations)
        return {"success": True, "reservation": new_res}

    def cancel_reservation(self, reservation_id, reason="Emergencia / Cancelación"):
        reservations = self.load_reservations()
        for r in reservations:
            if r.get("id") == reservation_id:
                r["status"] = "cancelled"
                r["cancel_reason"] = reason
                r["cancelled_at"] = datetime.now().strftime("%H:%M")
                self.save_reservations(reservations)
                return {"success": True, "freed_reservation": r}
        return {"success": False, "message": "Reserva no encontrada."}

    # Estadísticas, Estrellitas y Reclamos
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

db = Database()
