# 📞 Agente Telefónico de Voz con IA - Ventas Outbound (Argentina)

Sistema autónomo de llamadas de ventas y portabilidad telefónica con Inteligencia Artificial, diseñado para operar en **tiempo real (baja latencia sub-segundo)** y de forma **100% manos libres**.

Impulsado por **LangGraph**, **Ollama (`qwen2.5:7b`)**, **Faster-Whisper (GPU CUDA)** y **ElevenLabs / Edge-TTS**.

---

## 🚀 Características Principales

* **🎙️ Reconocimiento de Voz Instantáneo (STT):**
  * Faster-Whisper corriendo directamente sobre **CUDA (GPU NVIDIA)** con precisión `float16`.
  * Detección de silencios por energía (VAD) para detección automática de fin de turno (~550ms) sin presionar ninguna tecla.
* **🧠 Inteligencia Conversacional (Venta Consultiva):**
  * Orquestado con **LangGraph**.
  * Metodología de venta consultiva con diagnóstico de necesidades, empatía ante objeciones y anclaje de precios en **pesos argentinos**.
  * Memoria contextual persistente para recordar planes ofertados a lo largo de toda la llamada.
* **⚡ Cero Latencia por Downclock de GPU:**
  * Incluye un **GPU Warm Keeper** que evita que la tarjeta gráfica entre en estado de bajo consumo (`P8` a 405MHz) durante los silencios, manteniendo la VRAM a **7.300 MHz (`P2`)** para respuestas inmediatas.
* **🗣️ Voz Ultra Realista (TTS):**
  * Integración con **ElevenLabs (`eleven_flash_v2_5`)** a velocidad optimizada (1.15x) para ritmo de telemarketing.
  * Fallback automático a **Edge-TTS** si no hay conexión o se agotan los créditos.

---

## 📁 Arquitectura del Proyecto

```text
IA-LLAMADA/
├── agent/                  # Lógica del Agente y LangGraph
│   ├── graph.py            # Grafo de estados y flujo conversacional
│   ├── prompts.py          # Prompts del sistema, catálogo y técnicas de venta
│   └── state.py            # Definición del estado de la llamada
├── audio/                  # Motores de Audio (VAD, STT, TTS)
│   ├── stt.py              # Servicio Faster-Whisper en GPU CUDA
│   ├── tts.py              # Servicio ElevenLabs con fallback a Edge-TTS
│   └── vad.py              # Captura de audio y detección de silencio continua
├── core/                   # Control del Ciclo de Vida y Rendimiento
│   ├── call_session.py     # Manejo de la sesión, historial y métricas
│   └── gpu_keepalive.py    # Warm-keeper para fijar relojes de la GPU en P2
├── config.py               # Configuración global, precarga CUDA y variables
├── llamada_voz.py          # Simulador de llamada interactiva por micrófono
├── server_telefonia.py     # Servidor WebSocket para integración con telefonía (Twilio/Asterisk)
├── promociones_del_dia.json# Catálogo oficial de planes y promociones
└── .env.local.example      # Plantilla de variables de entorno
```

---

## 🛠️ Instalación y Requisitos

### 1. Requisitos Previos
* Linux (Ubuntu / Debian / Arch / WSL2)
* Python 3.10+
* GPU NVIDIA con drivers CUDA instalados (Recomendado: RTX 3060 12GB o superior)
* Ollama instalado con el modelo `qwen2.5:7b`:
  ```bash
  ollama pull qwen2.5:7b
  ```

### 2. Clonar y Configurar Entorno Virtual

```bash
# Clonar el repositorio
git clone <URL_DEL_REPOSITORIO>
cd IA-LLAMADA

# Crear y activar entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install langchain langchain-core langchain-ollama langgraph faster-whisper elevenlabs edge-tts python-dotenv numpy requests nvidia-cublas-cu12 nvidia-cudnn-cu12
```

### 3. Configurar Credenciales

Copia el archivo de ejemplo a `.env.local`:

```bash
cp .env.local.example .env.local
```

Edita `.env.local` y coloca tu API Key de ElevenLabs:

```ini
TTS_PROVIDER=elevenlabs
ELEVENLABS_API_KEY=tu_api_key_aqui
ELEVENLABS_VOICE_ID=EXAVITQu4vr4xnSDxMaL
ELEVENLABS_MODEL_ID=eleven_flash_v2_5
OLLAMA_MODEL=qwen2.5:7b
```

---

## 🎙️ Ejecución

Para iniciar la llamada telefónica interactiva por voz:

```bash
source venv/bin/activate
python llamada_voz.py
```

Habla de forma natural a través de tu micrófono; el sistema detectará automáticamente cuando termines de hablar y Sofía te responderá en tiempo real.
