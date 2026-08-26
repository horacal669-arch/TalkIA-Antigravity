# generate_promo_video.py

"""
Script to generate a 60-second promotional video for TalkIA PRO.
- Uses moviepy for video composition.
- Uses gTTS for Spanish narration.
- Adds background music (assumed to be 'background.mp3' in the project root).
- Adds subtitles (hard‑coded for simplicity).
- Outputs MP4 compatible with WhatsApp (H.264 Baseline, 720p).

Prerequisites (install via pip):
    pip install moviepy gtts

Place the following assets in the project root before running:
    - talkia_presenter_female_1786916222733.jpg (presenter image)
    - background.mp3 (royalty‑free music)

The script creates temporary clips, concatenates them, adds audio and subtitles,
and writes the final video to 'TalkIA_PRO_Video_Promo.mp4'.
"""

import os
from moviepy.video.VideoClip import ImageClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.video.compositing.CompositeVideoClip import concatenate_videoclips
from moviepy.video.compositing.TextClip import TextClip
from moviepy.audio.AudioClip import AudioFileClip, CompositeAudioClip
from gtts import gTTS

# Configuration
VIDEO_OUTPUT = "TalkIA_PRO_Video_Promo.mp4"
DURATION = 60  # seconds total
RESOLUTION = (1280, 720)
FPS = 24

# Assets (ensure they exist)
PRESENTER_IMG = "talkia_presenter_female_1786916222733.jpg"
BACKGROUND_MUSIC = "background.mp3"

# Spanish script (approx. 60 seconds)
SCRIPT_TEXT = (
    "¡Bienvenido a TalkIA, la solución de concierge virtual para hoteles pequeños! "
    "Con TalkIA, sus huéspedes reciben asistencia instantánea en varios idiomas, "
    "desde reservas hasta recomendaciones locales, todo desde su móvil. "
    "Nuestro sistema funciona sin complicaciones, fácil de instalar y compatible con cualquier red, "
    "incluso usando 4G o datos móviles. "
    "Descargue la aplicación, conecte su teléfono, y pulse 'Empezar' para ver la magia. "
    "TalkIA – su asistente de voz, siempre listo. "
)

# Generate narration audio
tts = gTTS(text=SCRIPT_TEXT, lang="es")
tts_path = "narration.mp3"
tts.save(tts_path)

# Load assets
if not os.path.isfile(PRESENTER_IMG):
    raise FileNotFoundError(f"Presenter image not found: {PRESENTER_IMG}")
if not os.path.isfile(BACKGROUND_MUSIC):
    # If background music is missing, we will use silent audio later
    print(f"Warning: Background music not found: {BACKGROUND_MUSIC}. Using silent audio.")

# Create visual slides – for simplicity we repeat the presenter image with different captions
slides = []
slide_duration = DURATION / 4  # 4 slides approx. 15s each
captions = [
    "TalkIA – Concierge virtual 24/7",
    "Soporte multilingüe: Español, Inglés, Portugués y más",
    "Fácil instalación, funciona en 4G y Wi‑Fi",
    "Descargue ahora y mejore la experiencia del huésped",
]

for caption in captions:
    img_clip = ImageClip(PRESENTER_IMG).with_duration(slide_duration)
    txt_clip = (
        TextClip(caption, fontsize=48, font="Arial", color="white", stroke_color="black", stroke_width=2)
        .set_position("center")
        .set_duration(slide_duration)
    )
    # Use CompositeVideoClip with explicit size to enforce resolution
    slide = CompositeVideoClip([img_clip, txt_clip], size=RESOLUTION)
    slides.append(slide)

video = concatenate_videoclips(slides)

# Add background music and narration
if os.path.isfile(BACKGROUND_MUSIC):
    audio_bg = AudioFileClip(BACKGROUND_MUSIC).volumex(0.3)
else:
    # Generate silent audio of appropriate duration
    from moviepy.audio.AudioClip import AudioArrayClip
    import numpy as np
    sr = 44100
    silence = np.zeros((int(video.duration * sr), 2), dtype=np.float32)
    audio_bg = AudioArrayClip(silence, fps=sr).volumex(0.0)

# Combine background and narration (narration on top)
combined_audio = audio_bg.set_duration(video.duration)
audio_narr = AudioFileClip(tts_path).set_duration(video.duration)
final_audio = CompositeAudioClip([combined_audio, audio_narr])
video = video.set_audio(final_audio)

# Write output – ensure compatibility with WhatsApp (baseline profile)
video.write_videofile(
    VIDEO_OUTPUT,
    codec="libx264",
    preset="medium",
    bitrate="2000k",
    audio_codec="aac",
    fps=FPS,
    ffmpeg_params=["-profile:v", "baseline", "-level", "3.0"],
)

# Cleanup temporary narration file
os.remove(tts_path)

print(f"Video generated: {VIDEO_OUTPUT}")
