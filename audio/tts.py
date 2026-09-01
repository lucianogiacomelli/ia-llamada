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
    Servicio de TTS ultra rápido con Streaming Concurrente por Oraciones (Pipelining).
    Comienza a reproducir la primera oración en ~450ms mientras pre-descarga la siguiente
    en segundo plano en memoria, logrando cero pausas y mínima latencia percibida.
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
        
        if self.api_key:
            self.elevenlabs_client = ElevenLabs(api_key=self.api_key)
        else:
            self.elevenlabs_client = None

    def reproducir_stream_oraciones(self, generador_oraciones: Generator[str, None, None]):
        """
        Reproduce oraciones en streaming concurrente.
        La primera oración suena en ~450ms; las siguientes se pre-cargan en un thread worker
        para que no haya ningún corte ni silencio intermedio.
        """
        if self.provider == "elevenlabs" and self.api_key:
            try:
                self._reproducir_elevenlabs_pipelined(generador_oraciones)
                return
            except Exception as e:
                print(f"⚠️ Streaming concurrente falló ({e}). Usando fallback...")
                
        # Fallback si no hay ElevenLabs
        for oracion in generador_oraciones:
            self.reproducir(oracion)

    def _reproducir_elevenlabs_pipelined(self, generador_oraciones: Generator[str, None, None]):
        settings = VoiceSettings(
            stability=0.5,
            similarity_boost=0.75,
            speed=self.speed
        )
        
        audio_queue = queue.Queue(maxsize=10)
        
        def productor():
            try:
                for oracion in generador_oraciones:
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
                    if audio_bytes:
                        audio_queue.put(audio_bytes)
            except Exception as e:
                print(f"Error en productor de audio: {e}")
            finally:
                audio_queue.put(None)
                
        t_prod = threading.Thread(target=productor, daemon=True)
        t_prod.start()
        
        # Consumidor secuencial: reproduce cada oración completa sin solapamiento
        while True:
            audio_bytes = audio_queue.get()
            if audio_bytes is None:
                break
            proc = subprocess.Popen(["pw-play", "-"], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
            proc.stdin.write(audio_bytes)
            proc.stdin.close()
            proc.wait()

    def reproducir(self, texto: str):
        """Reproduce texto directo con pipe streaming."""
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
                for chunk in stream:
                    if chunk:
                        proc.stdin.write(chunk)
                proc.stdin.close()
                proc.wait()
                return
            except Exception as e:
                print(f"⚠️ ElevenLabs streaming falló ({e}). Usando fallback...")

        # Fallback Edge-TTS
        asyncio.run(self.sintetizar_edge_tts(texto, TEMP_AUDIO_SALIDA))
        if shutil.which("pw-play"):
            subprocess.run(["pw-play", TEMP_AUDIO_SALIDA], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    async def sintetizar_edge_tts(self, texto: str, output_path: str = TEMP_AUDIO_SALIDA) -> str:
        comunicador = edge_tts.Communicate(texto, EDGE_TTS_VOICE, rate="+15%")
        await comunicador.save(output_path)
        return output_path

# Instancia global reutilizable
tts_service = TextToSpeechService()
