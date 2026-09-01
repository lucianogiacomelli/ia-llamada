import subprocess
import collections
import time
import threading
from typing import Callable
import numpy as np
from config import (
    VAD_SAMPLE_RATE,
    VAD_CHUNK_SAMPLES,
    VAD_UMBRAL_ENERGIA,
    VAD_SILENCIO_CORTE,
    VAD_PRE_BUFFER_SEC,
    VAD_MAX_ESPERA_INICIO
)
from audio.tts import tts_service

class VADStreamProcessor:
    """
    Procesador de VAD con soporte de detección de inicio de habla para interrupciones (Barge-In).
    """
    
    def __init__(
        self,
        sample_rate=VAD_SAMPLE_RATE,
        umbral_energia=VAD_UMBRAL_ENERGIA,
        silencio_corte=VAD_SILENCIO_CORTE,
        pre_buffer_sec=VAD_PRE_BUFFER_SEC,
        on_speech_started: Callable[[], None] | None = None
    ):
        self.sample_rate = sample_rate
        self.umbral_energia = umbral_energia
        self.silencio_corte = silencio_corte
        self.on_speech_started = on_speech_started
        
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
                if self.on_speech_started:
                    try:
                        self.on_speech_started()
                    except Exception:
                        pass
                return False, None
            return False, None
        else:
            self.audio_grabado.append(chunk_pcm_s16)
            if rms < self.umbral_energia:
                self.duracion_silencio += self.chunk_duration
            else:
                self.duracion_silencio = 0.0
                
            if self.duracion_silencio >= self.silencio_corte:
                audio_np = np.concatenate(self.audio_grabado).astype(np.float32) / 32768.0
                self.reset()
                return True, audio_np
                
            return False, None


def capturar_audio_con_barge_in(
    reproducir_fn: Callable[[], None] | None = None,
    silencio_corte=VAD_SILENCIO_CORTE,
    umbral_energia=VAD_UMBRAL_ENERGIA,
    max_espera=VAD_MAX_ESPERA_INICIO
) -> tuple[bool, np.ndarray | None]:
    """
    Sistema Full-Duplex de audio con Interrupción (Barge-In):
    1. Activa el micrófono de inmediato.
    2. Lanza reproducir_fn() en segundo plano (Sofía habla).
    3. Si el cliente empieza a hablar mientras Sofía está hablando, corta a Sofía al instante.
    4. Continúa grabando hasta que el cliente termine de hablar (silencio_corte).
    Retorna: (fue_interrumpido, audio_cliente_np)
    """
    interrumpido = False
    
    def on_user_spoke():
        nonlocal interrumpido
        if tts_service.esta_hablando:
            interrumpido = True
            print("\n🛑 [Interrupción detectada] El cliente tomó la palabra...")
            tts_service.interrumpir()
            
    bytes_per_chunk = VAD_CHUNK_SAMPLES * 2
    processor = VADStreamProcessor(
        umbral_energia=umbral_energia,
        silencio_corte=silencio_corte,
        on_speech_started=on_user_spoke
    )
    
    proc_mic = subprocess.Popen(
        ["arecord", "-q", "-r", str(VAD_SAMPLE_RATE), "-c", "1", "-f", "S16_LE", "-t", "raw"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )
    
    # Iniciar reproducción en segundo plano si hay función
    t_reprod = None
    if reproducir_fn:
        t_reprod = threading.Thread(target=reproducir_fn, daemon=True)
        t_reprod.start()
        
    t_inicio = time.time()
    
    try:
        while True:
            raw_bytes = proc_mic.stdout.read(bytes_per_chunk)
            if not raw_bytes or len(raw_bytes) < bytes_per_chunk:
                break
                
            chunk = np.frombuffer(raw_bytes, dtype=np.int16)
            turn_finished, audio_np = processor.process_chunk(chunk)
            
            if turn_finished:
                print(f"⚡ [Silencio detectado] Procesando...")
                return interrumpido, audio_np
                
            # Timeout solo si nadie está hablando y Sofía terminó
            if not processor.hablando and (t_reprod is None or not t_reprod.is_alive()):
                if time.time() - t_inicio > max_espera:
                    return interrumpido, None
    finally:
        proc_mic.terminate()
        try:
            proc_mic.wait(timeout=0.2)
        except Exception:
            pass


def capturar_audio_microfono_vad(
    silencio_corte=VAD_SILENCIO_CORTE,
    umbral_energia=VAD_UMBRAL_ENERGIA,
    max_espera=VAD_MAX_ESPERA_INICIO
) -> np.ndarray | None:
    """Función de compatibilidad para capturar solo voz."""
    _, audio_np = capturar_audio_con_barge_in(
        reproducir_fn=None,
        silencio_corte=silencio_corte,
        umbral_energia=umbral_energia,
        max_espera=max_espera
    )
    return audio_np
