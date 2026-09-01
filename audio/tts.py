import os
import shutil
import subprocess
import asyncio
import queue
import threading
from typing import Generator
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
import edge_tts
from config import (
    TTS_PROVIDER,
    ELEVENLABS_API_KEY,
    ELEVENLABS_VOICE_ID,
    ELEVENLABS_MODEL_ID,
    EDGE_TTS_VOICE,
    TEMP_AUDIO_SALIDA
)

class TextToSpeechService:
    """
    Servicio de TTS ultra rápido con soporte para INTERRUPCIONES (Barge-in).
    Si el cliente habla mientras Sofía está reproduciendo audio, corta inmediatamente
    la voz de la IA y cancela la cola de síntesis.
    """
    
    def __init__(
        self,
        provider: str = TTS_PROVIDER,
        api_key: str = ELEVENLABS_API_KEY,
        voice_id: str = ELEVENLABS_VOICE_ID,
        model_id: str = ELEVENLABS_MODEL_ID,
        speed: float = 1.08
    ):
        self.provider = provider
        self.voice_id = voice_id
        self.model_id = model_id
        self.api_key = api_key
        self.speed = speed
        
        self._active_proc: subprocess.Popen | None = None
        self._interrumpido = threading.Event()
        self._lock = threading.Lock()
        
        if self.api_key:
            self.elevenlabs_client = ElevenLabs(api_key=self.api_key)
        else:
            self.elevenlabs_client = None

    def interrumpir(self):
        """Cancela y corta la voz de Sofía de inmediato cuando el cliente habla."""
        self._interrumpido.set()
        with self._lock:
            if self._active_proc and self._active_proc.poll() is None:
                try:
                    self._active_proc.kill()
                except Exception:
                    pass
                self._active_proc = None

    @property
    def esta_hablando(self) -> bool:
        """Indica si Sofía está reproduciendo audio en este momento."""
        with self._lock:
            return self._active_proc is not None and self._active_proc.poll() is None

    def reproducir_stream_oraciones(self, generador_oraciones: Generator[str, None, None]) -> bool:
        """
        Reproduce oraciones en streaming con soporte para cancelación por interrupción.
        Retorna True si completó la respuesta, o False si fue interrumpida por el cliente.
        """
        self._interrumpido.clear()
        
        if self.provider == "elevenlabs" and self.api_key:
            try:
                return self._reproducir_elevenlabs_pipelined(generador_oraciones)
            except Exception as e:
                print(f"⚠️ Streaming ElevenLabs falló ({e}). Usando fallback...")
                
        # Fallback si no hay ElevenLabs
        for oracion in generador_oraciones:
            if self._interrumpido.is_set():
                return False
            self.reproducir(oracion)
        return True

    def _reproducir_elevenlabs_pipelined(self, generador_oraciones: Generator[str, None, None]) -> bool:
        settings = VoiceSettings(
            stability=0.5,
            similarity_boost=0.75,
            speed=self.speed
        )
        
        audio_queue = queue.Queue(maxsize=10)
        
        def productor():
            try:
                for oracion in generador_oraciones:
                    if self._interrumpido.is_set():
                        break
                    oracion = oracion.strip()
                    if not oracion or len(oracion) < 2:
                        continue
                    stream = self.elevenlabs_client.text_to_speech.convert(
                        voice_id=self.voice_id,
                        model_id=self.model_id,
                        text=oracion,
                        voice_settings=settings
                    )
                    audio_bytes = b"".join(stream)
                    if audio_bytes and not self._interrumpido.is_set():
                        audio_queue.put(audio_bytes)
            except Exception as e:
                if not self._interrumpido.is_set():
                    print(f"Error en productor de audio: {e}")
            finally:
                audio_queue.put(None)
                
        t_prod = threading.Thread(target=productor, daemon=True)
        t_prod.start()
        
        # Consumidor de reproducción
        while True:
            if self._interrumpido.is_set():
                return False
                
            try:
                audio_bytes = audio_queue.get(timeout=0.1)
            except queue.Empty:
                if not t_prod.is_alive():
                    break
                continue
                
            if audio_bytes is None:
                break
                
            if self._interrumpido.is_set():
                return False
                
            proc = subprocess.Popen(["pw-play", "-"], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
            with self._lock:
                self._active_proc = proc
                
            try:
                proc.stdin.write(audio_bytes)
                proc.stdin.close()
                proc.wait()
            except Exception:
                pass
            finally:
                with self._lock:
                    self._active_proc = None
                    
            if self._interrumpido.is_set():
                return False
                
        return True

    def reproducir(self, texto: str):
        """Reproduce texto directo con pipe streaming."""
        self._interrumpido.clear()
        print(f"\n🤖 Sofía: {texto}")
        if self.provider == "elevenlabs" and self.api_key:
            try:
                settings = VoiceSettings(
                    stability=0.5,
                    similarity_boost=0.75,
                    speed=self.speed
                )
                stream = self.elevenlabs_client.text_to_speech.convert(
                    voice_id=self.voice_id,
                    model_id=self.model_id,
                    text=texto,
                    voice_settings=settings
                )
                proc = subprocess.Popen(["pw-play", "-"], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
                with self._lock:
                    self._active_proc = proc
                    
                for chunk in stream:
                    if self._interrumpido.is_set():
                        proc.kill()
                        return
                    if chunk:
                        proc.stdin.write(chunk)
                        
                proc.stdin.close()
                proc.wait()
                return
            except Exception as e:
                print(f"⚠️ ElevenLabs streaming falló ({e}). Usando fallback...")
            finally:
                with self._lock:
                    self._active_proc = None

        # Fallback Edge-TTS
        asyncio.run(self.sintetizar_edge_tts(texto, TEMP_AUDIO_SALIDA))
        if shutil.which("pw-play"):
            proc = subprocess.Popen(["pw-play", TEMP_AUDIO_SALIDA], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            with self._lock:
                self._active_proc = proc
            proc.wait()
            with self._lock:
                self._active_proc = None

    async def sintetizar_edge_tts(self, texto: str, output_path: str = TEMP_AUDIO_SALIDA) -> str:
        comunicador = edge_tts.Communicate(texto, EDGE_TTS_VOICE, rate="+15%")
        await comunicador.save(output_path)
        return output_path

# Instancia global reutilizable
tts_service = TextToSpeechService()
