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
    Servicio de TTS ultra rápido y coherente con ElevenLabs (1.15x de velocidad).
    Fallback automático a Edge-TTS en caso de fallo.
    """
    
    def __init__(
        self,
        provider: str = TTS_PROVIDER,
        api_key: str = ELEVENLABS_API_KEY,
        voice_id: str = ELEVENLABS_VOICE_ID,
        model_id: str = ELEVENLABS_MODEL_ID,
        speed: float = 1.15
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

    def sintetizar_elevenlabs(self, texto: str, output_path: str = TEMP_AUDIO_SALIDA) -> str:
        """Sintetiza audio con ElevenLabs con velocidad 1.15x."""
        if not self.elevenlabs_client:
            raise ValueError("ELEVENLABS_API_KEY no configurada en .env.local")
            
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
        """Sintetiza audio con Edge-TTS con velocidad +15%."""
        comunicador = edge_tts.Communicate(texto, EDGE_TTS_VOICE, rate="+15%")
        await comunicador.save(output_path)
        return output_path

    async def sintetizar_audio(self, texto: str, output_path: str = TEMP_AUDIO_SALIDA) -> str:
        """Sintetiza audio usando el proveedor configurado."""
        if self.provider == "elevenlabs" and self.api_key:
            try:
                return await asyncio.to_thread(self.sintetizar_elevenlabs, texto, output_path)
            except Exception as e:
                print(f"⚠️ ElevenLabs falló ({e}). Usando fallback Edge-TTS...")
                return await self.sintetizar_edge_tts(texto, output_path)
        else:
            return await self.sintetizar_edge_tts(texto, output_path)

    def reproducir(self, texto: str, output_path: str = TEMP_AUDIO_SALIDA):
        """Sintetiza y reproduce el audio en los altavoces locales."""
        print(f"\n🤖 Sofía: {texto}")
        asyncio.run(self.sintetizar_audio(texto, output_path))
        
        if shutil.which("pw-play"):
            subprocess.run(["pw-play", output_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif shutil.which("ffplay"):
            subprocess.run(["ffplay", "-nodisp", "-autoexit", output_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif shutil.which("paplay"):
            subprocess.run(["paplay", output_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# Instancia global reutilizable
tts_service = TextToSpeechService()
