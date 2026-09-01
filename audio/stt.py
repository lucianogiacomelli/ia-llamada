import numpy as np
from faster_whisper import WhisperModel
from config import WHISPER_MODEL_SIZE, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE

class SpeechToTextService:
    """Servicio de reconocimiento de voz acelerado con Faster-Whisper."""
    
    def __init__(self, model_size=WHISPER_MODEL_SIZE, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE):
        print(f"⏳ Inicializando Whisper ({model_size}) en {device.upper()}...")
        try:
            self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
            print(f"⚡ Whisper cargado exitosamente en {device.upper()}")
        except Exception as e:
            print(f"⚠️ Falló en {device} ({e}). Cargando en CPU...")
            self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
            
    def transcribir_audio(self, audio_data: np.ndarray | str, language="es") -> str:
        """
        Transcribe audio desde un array numpy float32 normalizado o desde un archivo WAV.
        Utiliza beam_size=1 y VAD filter para mínima latencia.
        """
        segments, _ = self.model.transcribe(
            audio_data,
            language=language,
            vad_filter=True,
            beam_size=1,
            temperature=0.0
        )
        texto = " ".join([seg.text for seg in segments]).strip()
        return texto

# Instancia global reutilizable
stt_service = SpeechToTextService()
