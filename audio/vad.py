import subprocess
import collections
import time
import numpy as np
from config import (
    VAD_SAMPLE_RATE,
    VAD_CHUNK_SAMPLES,
    VAD_UMBRAL_ENERGIA,
    VAD_SILENCIO_CORTE,
    VAD_PRE_BUFFER_SEC,
    VAD_MAX_ESPERA_INICIO
)

class VADStreamProcessor:
    """
    Procesador de VAD desacoplado:
    Permite procesar chunks de audio PCM (16kHz S16_LE) tanto del micrófono local
    como de un flujo de telefonía (Twilio, Asterisk, WebSockets).
    """
    
    def __init__(
        self,
        sample_rate=VAD_SAMPLE_RATE,
        umbral_energia=VAD_UMBRAL_ENERGIA,
        silencio_corte=VAD_SILENCIO_CORTE,
        pre_buffer_sec=VAD_PRE_BUFFER_SEC
    ):
        self.sample_rate = sample_rate
        self.umbral_energia = umbral_energia
        self.silencio_corte = silencio_corte
        
        self.chunk_duration = VAD_CHUNK_SAMPLES / sample_rate
        self.pre_buffer_size = int(pre_buffer_sec / self.chunk_duration)
        self.pre_buffer = collections.deque(maxlen=self.pre_buffer_size)
        
        self.reset()
        
    def reset(self):
        self.hablando = False
        self.duracion_silencio = 0.0
        self.audio_grabado = []
        self.pre_buffer.clear()
        
    def process_chunk(self, chunk_pcm_s16: np.ndarray) -> tuple[bool, np.ndarray | None]:
        """
        Procesa un fragmento de audio.
        Retorna (is_turn_complete, audio_completo_float32_o_None).
        """
        rms = np.sqrt(np.mean(chunk_pcm_s16.astype(np.float32)**2))
        
        if not self.hablando:
            self.pre_buffer.append(chunk_pcm_s16)
            if rms > self.umbral_energia:
                self.hablando = True
                self.audio_grabado.extend(list(self.pre_buffer))
                self.duracion_silencio = 0.0
                return False, None
            return False, None
        else:
            self.audio_grabado.append(chunk_pcm_s16)
            if rms < self.umbral_energia:
                self.duracion_silencio += self.chunk_duration
            else:
                self.duracion_silencio = 0.0
                
            if self.duracion_silencio >= self.silencio_corte:
                # Turno completado por silencio
                audio_np = np.concatenate(self.audio_grabado).astype(np.float32) / 32768.0
                self.reset()
                return True, audio_np
                
            return False, None


def capturar_audio_microfono_vad(
    silencio_corte=VAD_SILENCIO_CORTE,
    umbral_energia=VAD_UMBRAL_ENERGIA,
    max_espera=VAD_MAX_ESPERA_INICIO
) -> np.ndarray | None:
    """Captura audio del micrófono local con detección automática de silencio."""
    bytes_per_chunk = VAD_CHUNK_SAMPLES * 2
    processor = VADStreamProcessor(
        umbral_energia=umbral_energia,
        silencio_corte=silencio_corte
    )
    
    proc = subprocess.Popen(
        ["arecord", "-q", "-r", str(VAD_SAMPLE_RATE), "-c", "1", "-f", "S16_LE", "-t", "raw"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )
    
    print("\n🎧 [Escuchando...] Puedes hablar ahora:", flush=True)
    t_inicio = time.time()
    
    try:
        while True:
            raw_bytes = proc.stdout.read(bytes_per_chunk)
            if not raw_bytes or len(raw_bytes) < bytes_per_chunk:
                break
                
            chunk = np.frombuffer(raw_bytes, dtype=np.int16)
            turn_finished, audio_np = processor.process_chunk(chunk)
            
            if turn_finished:
                print(f"⚡ [Silencio detectado] Procesando...")
                return audio_np
                
            if not processor.hablando and (time.time() - t_inicio > max_espera):
                return None
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=0.2)
        except Exception:
            proc.kill()
            
    return None
