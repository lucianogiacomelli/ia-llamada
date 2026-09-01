import os
import sys
import ctypes
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Cargar variables de entorno de forma absoluta con override
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env.local"), override=True)
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"), override=True)

# ========================================================
# 1. PRE-CARGA DE LIBRERÍAS CUDA (Para Whisper en Linux GPU)
# ========================================================
def pre_cargar_cuda():
    """Registra y enlaza libcublas y dependencias en memoria."""
    rutas_cuda = [
        os.path.join(sys.prefix, f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages/nvidia/cublas/lib"),
        os.path.join(sys.prefix, f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages/nvidia/cudnn/lib"),
        os.path.join(sys.prefix, f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages/nvidia/cuda_nvrtc/lib"),
        "/usr/local/lib/ollama/cuda_v12",
        "/usr/local/cuda/lib64",
        "/usr/local/cuda-12/lib64"
    ]
    for ruta in rutas_cuda:
        if os.path.exists(ruta):
            if "LD_LIBRARY_PATH" in os.environ:
                os.environ["LD_LIBRARY_PATH"] = f"{ruta}:{os.environ['LD_LIBRARY_PATH']}"
            else:
                os.environ["LD_LIBRARY_PATH"] = ruta
                
            for archivo in sorted(os.listdir(ruta)):
                if (archivo.startswith("libcublas") or archivo.startswith("libcudnn") or archivo.startswith("libcudart")) and ".so" in archivo:
                    try:
                        ctypes.CDLL(os.path.join(ruta, archivo))
                    except Exception:
                        pass

pre_cargar_cuda()

# ========================================================
# 2. CONFIGURACIÓN DEL AGENTE Y MODELOS
# ========================================================
# LLM (Ollama)
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_TEMPERATURE = 0.2

# ========================================================
# 3. CONFIGURACIÓN DE TTS (ElevenLabs / Edge-TTS)
# ========================================================
TTS_PROVIDER = os.environ.get("TTS_PROVIDER", "elevenlabs")

# Configuración de ElevenLabs
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip()
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL").strip()
ELEVENLABS_MODEL_ID = os.environ.get("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5").strip()

# Configuración de Edge-TTS (Fallback local)
EDGE_TTS_VOICE = os.environ.get("EDGE_TTS_VOICE", "es-AR-ElenaNeural").strip()

# ========================================================
# 4. RECONOCIMIENTO DE VOZ (Whisper) Y VAD ULTRA RÁPIDO
# ========================================================
WHISPER_MODEL_SIZE = "small"
WHISPER_DEVICE = "cuda"
WHISPER_COMPUTE_TYPE = "float16"

# Detección de Silencio (VAD) - Optimizado a 350ms para respuesta inmediata
VAD_SAMPLE_RATE = 16000
VAD_CHUNK_SAMPLES = 512
VAD_UMBRAL_ENERGIA = 250
VAD_SILENCIO_CORTE = 0.35
VAD_PRE_BUFFER_SEC = 0.35
VAD_MAX_ESPERA_INICIO = 15.0

# Archivos
CATALOGO_PATH = os.path.join(BASE_DIR, "promociones_del_dia.json")
TEMP_AUDIO_SALIDA = os.path.join(BASE_DIR, "respuesta_ia.mp3")
TEMP_AUDIO_ENTRADA = os.path.join(BASE_DIR, "entrada_usuario.wav")
