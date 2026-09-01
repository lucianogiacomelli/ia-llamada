import os
import shutil
import subprocess
import asyncio
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
    Servicio de TTS ultra rápido con streaming directo por pipe (pw-play -).
    Inicia la reproducción en los altavoces en ~450ms sin esperar la descarga completa.
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

    def reproducir_stream_elevenlabs(self, texto: str):
        """
        Envía los chunks de audio directamente a los altavoces a través de un pipe stdin (pw-play -).
        Comienza a sonar apenas llega el primer paquete de audio (TTFB ~450ms).
        """
        if not self.elevenlabs_client:
            raise ValueError("ELEVENLABS_API_KEY no configurada")
            
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
        
        # Reproductor en streaming directo vía pipe
        proc = subprocess.Popen(["pw-play", "-"], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            for chunk in stream:
                if chunk:
                    proc.stdin.write(chunk)
        finally:
            if proc.stdin:
                proc.stdin.close()
            proc.wait()

    def sintetizar_elevenlabs(self, texto: str, output_path: str = TEMP_AUDIO_SALIDA) -> str:
        """Sintetiza y guarda a disco (método tradicional)."""
        if not self.elevenlabs_client:
            raise ValueError("ELEVENLABS_API_KEY no configurada")
            
        settings = VoiceSettings(
            stability=0.5,
            similarity_boost=0.75,
            speed=self.speed
        )
        
        audio_stream = self.elevenlabs_client.text_to_speech.convert(
            voice_id=self.voice_id,
            model_id=self.model_id,
            text=texto,
            voice_settings=settings
        )
        
        with open(output_path, "wb") as f:
            for chunk in audio_stream:
                if chunk:
                    f.write(chunk)
                    
        return output_path

    async def sintetizar_edge_tts(self, texto: str, output_path: str = TEMP_AUDIO_SALIDA) -> str:
        """Fallback Edge-TTS."""
        comunicador = edge_tts.Communicate(texto, EDGE_TTS_VOICE, rate="+15%")
        await comunicador.save(output_path)
        return output_path

    async def sintetizar_audio(self, texto: str, output_path: str = TEMP_AUDIO_SALIDA) -> str:
        if self.provider == "elevenlabs" and self.api_key:
            try:
                return await asyncio.to_thread(self.sintetizar_elevenlabs, texto, output_path)
            except Exception as e:
                print(f"⚠️ ElevenLabs falló ({e}). Usando fallback Edge-TTS...")
                return await self.sintetizar_edge_tts(texto, output_path)
        else:
            return await self.sintetizar_edge_tts(texto, output_path)

    def reproducir(self, texto: str):
        """Reproduce la respuesta usando pipe streaming de baja latencia."""
        print(f"\n🤖 Sofía: {texto}")
        if self.provider == "elevenlabs" and self.api_key:
            try:
                self.reproducir_stream_elevenlabs(texto)
                return
            except Exception as e:
                print(f"⚠️ Streaming ElevenLabs falló ({e}). Usando fallback...")
                
        # Fallback si falla el streaming
        asyncio.run(self.sintetizar_edge_tts(texto, TEMP_AUDIO_SALIDA))
        if shutil.which("pw-play"):
            subprocess.run(["pw-play", TEMP_AUDIO_SALIDA], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# Instancia global reutilizable
tts_service = TextToSpeechService()
