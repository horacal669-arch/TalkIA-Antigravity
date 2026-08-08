import os
import re
import json
import uuid
import logging
import asyncio
import requests
from groq import Groq
import edge_tts

log = logging.getLogger("ai_engine")

GROQ_KEY = os.environ.get("GROQ_API_KEY", "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")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

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

LANG_NAMES = {
    "es": "Español", "en": "English", "ja": "日本語", "ru": "Русский",
    "zh": "中文", "de": "Deutsch", "it": "Italiano", "fr": "Français",
    "pt": "Português", "he": "עברית", "hi": "हिन्दी", "ko": "한국어"
}

class AIEngine:
    def __init__(self):
        self.groq_client = Groq(api_key=GROQ_KEY)

    def transcribe_audio(self, audio_bytes):
        """Convierte voz a texto usando Groq Whisper (ultra-rápido)."""
        tmp_folder = os.path.join(os.environ.get("TEMP", os.getcwd()), "talkia_tmp")
        os.makedirs(tmp_folder, exist_ok=True)
        tmp_file = os.path.join(tmp_folder, f"stt_{uuid.uuid4().hex[:8]}.ogg")
        
        with open(tmp_file, "wb") as f:
            f.write(audio_bytes)

        try:
            with open(tmp_file, "rb") as f:
                res = self.groq_client.audio.transcriptions.create(
                    file=("audio.ogg", f, "audio/ogg"),
                    model="whisper-large-v3-turbo",
                    response_format="verbose_json"
                )
            detected_lang = res.language[:2] if hasattr(res, 'language') and res.language else "en"
            return res.text.strip(), detected_lang
        except Exception as e:
            log.error(f"Error en STT Whisper: {e}")
            return "", "en"
        finally:
            if os.path.exists(tmp_file):
                try: os.remove(tmp_file)
                except: pass

    def process_guest_message(self, text, source_lang="auto", target_lang="es", context_info="Hotel Concierge"):
        """
        Procesa el mensaje del huésped/turista con Groq y fallback inteligente.
        Retorna la respuesta traducida, el tipo de solicitud y análisis de sentimiento.
        """
        prompt = f"""You are TalkIA PRO, an elite AI Concierge and Tourism Assistant in Ushuaia, Patagonia Argentina.
Context: {context_info}
Rule 1: If the input is in Spanish, translate and reply warmly to the target language '{target_lang}'.
Rule 2: If the input is in a foreign language, translate it accurately to Spanish for the hotel staff/guide.
Rule 3: Identify request category: coffee, cleaning, taxi, towels, dinner, wakeup, wifi, emergency, tour_booking, complaint, suggestion, rating, general.
Rule 4: Assess sentiment: positive, neutral, negative.

Return ONLY a valid raw JSON without markdown codeblocks:
{{
  "response_translated": "translated text or reply in target language",
  "summary_es": "brief 1-sentence summary in Spanish for staff",
  "detected_lang": "iso 2-letter code",
  "request_type": "category",
  "sentiment": "positive|neutral|negative"
}}

Input text: {text}"""

        try:
            res = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.2
            )
            raw_content = res.choices[0].message.content.strip()
            return self._parse_json(raw_content, text)
        except Exception as e:
            log.error(f"Fallback en IA: {e}")
            return {
                "response_translated": text,
                "summary_es": f"Consulta: {text}",
                "detected_lang": source_lang if source_lang != "auto" else "en",
                "request_type": "general",
                "sentiment": "neutral"
            }

    def generate_tts_voice(self, text, lang_code, output_filepath):
        """Genera audio de voz humana usando Edge-TTS."""
        voice = VOICES.get(lang_code, VOICES["en"])
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(edge_tts.Communicate(text, voice).save(output_filepath))
            return True
        except Exception as e:
            log.error(f"Error generando TTS: {e}")
            return False
        finally:
            loop.close()

    def _parse_json(self, raw_text, fallback_text):
        clean = re.sub(r'```(?:json)?', '', raw_text).strip('`').strip()
        match = re.search(r'\{.*\}', clean, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
        return {
            "response_translated": raw_text,
            "summary_es": fallback_text,
            "detected_lang": "en",
            "request_type": "general",
            "sentiment": "neutral"
        }

ai_engine = AIEngine()
