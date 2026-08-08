# 🏔️ TalkIA Antigravity — Suite de Inteligencia Artificial para Hoteles y Turismo

**TalkIA Antigravity** es una solución tecnológica integral de Inteligencia Artificial diseñada para optimizar la atención al cliente, comunicación multilingüe en tiempo real y servicios de conserjería para hoteles, posadas y empresas de turismo en Ushuaia y el mundo.

---

## 🌟 Características Principales

### 🎙️ 1. Bot Traductor Personal en Vivo (Telegram)
- **Traducción bidireccional en tiempo real** (Español ↔ Inglés, Portugués, Francés, Alemán, Ruso, Chino, Japonés, Hebreo, etc.).
- **Teclado de banderas rápido** para selección de idioma al instante.
- **Voz humana neuronal (Edge-TTS)** y reconocimiento de audio ultrarrápido con **Groq Whisper Large v3**.
- **Resistencia total a caídas:** Proceso independiente blindado.

### 🏨 2. Plataforma Web para Hoteles (Dashboards Interactivos)
- **Dashboard del Huésped (Acceso por Códigos QR):**
  - Escaneo directo por habitación (ej. Hab. 101, 104).
  - Pedidos rápidos de servicios: 🧹 Limpieza, ☕ Café, 🚕 Taxi, 🛁 Toallas, 📶 WiFi, 🚨 Emergencias.
  - **Sistema de Calificación con Estrellitas (⭐ 1 a ⭐ 5)**, felicitaciones y reclamos.
- **Dashboard del Staff / Recepción:**
  - Panel de control en tiempo real con alertas auditivas y visuales.
  - Gestión de reclamos y monitoreo de satisfacción del cliente.
- **Dashboard de Configuración de Marca:**
  - Personalización de colores principales, logo, fotos, wifi y horarios del hotel.

### 🏔️ 3. Módulo de Turismo y Excursiones
- Integración para agencias de viaje y guías turísticos.
- Muestra de catálogo de excursiones en el idioma nativo del cliente (Tren del Fin del Mundo, Navegación Canal Beagle, Parque Nacional Tierra del Fuego, etc.).

---

## 🚀 Estructura del Proyecto

```
Proyecto TalkIA PRO/
├── bot_traductor.py         # Bot de Telegram autónomo
├── ai_engine.py             # Motor Multi-IA (Groq + Edge-TTS + Fallback)
├── database.py              # Base de datos persistente (Hoteles, Estrellitas, Tours)
├── servidor_talia.py        # Servidor Web principal con Flask
├── index.html               # Dashboard del Huésped
├── panel.html               # Dashboard de Recepción
├── config.html              # Dashboard de Configuración
├── qr_generator.html        # Generador de Códigos QR
├── INICIAR_BOT_TRADUCTOR.bat# Lanzador ejecutable 1-clic (Bot)
├── INICIAR_SISTEMA_HOTEL.bat# Lanzador ejecutable 1-clic (Web)
├── INICIAR_TODO.bat         # Lanzador ejecutable 1-clic (Completo)
└── RESPALDAR_EN_GITHUB.bat  # Sincronización automática con GitHub
```

---

## 👨‍💻 Autor
**Horazio** — Ushuaia, Tierra del Fuego, Argentina.
