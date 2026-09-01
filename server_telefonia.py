"""
====================================================================
TEMPLATE DE INTEGRACIÓN PARA TELEFONÍA REAL (Twilio, Asterisk, SIP)
====================================================================
Este archivo demuestra cómo conectar el agente a una llamada telefónica real
utilizando WebSockets / Audio Streaming (ejemplo compatible con Twilio Media Streams,
FreeSWITCH o gateways VoIP).
"""

import json
import asyncio
import base64
import numpy as np
from core.call_session import CallSession
from audio.stt import stt_service
from audio.tts import tts_service
from audio.vad import VADStreamProcessor

async def manejar_llamada_websocket(websocket):
    """
    Controlador de stream de audio para una llamada telefónica entrante o saliente.
    """
    print("\n📞 [Llamada telefónica conectada vía WebSocket]")
    
    # 1. Crear sesión de la llamada
    sesion = CallSession(client_name="Cliente Telefónico")
    vad_processor = VADStreamProcessor(sample_rate=16000, umbral_energia=250, silencio_corte=1.0)
    
    # 2. Sofía da el saludo inicial
    saludo_texto = sesion.iniciar_llamada()
    audio_path = await tts_service.sintetizar_audio(saludo_texto)
    print(f"🤖 Sofía (Teléfono): {saludo_texto}")
    
    # Enviar audio inicial al WebSocket (ej. codificado en base64 o raw PCM)
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
    await websocket.send(json.dumps({"event": "media", "media": {"payload": base64.b64encode(audio_bytes).decode()}}))
    
    # 3. Bucle de escucha y respuesta en tiempo real
    try:
        async for mensaje in websocket:
            data = json.loads(mensaje)
            event = data.get("event")
            
            if event == "media":
                # Recibir chunk de audio del teléfono (PCM 16-bit)
                payload = base64.b64decode(data["media"]["payload"])
                chunk_pcm = np.frombuffer(payload, dtype=np.int16)
                
                # Procesar con VAD
                turno_terminado, audio_completo = vad_processor.process_chunk(chunk_pcm)
                
                if turno_terminado and audio_completo is not None:
                    # 4. Transcribir voz del cliente
                    texto_cliente = stt_service.transcribir_audio(audio_completo)
                    print(f"👤 Cliente: \"{texto_cliente}\"")
                    
                    if not texto_cliente:
                        continue
                        
                    # 5. Procesar respuesta con el Grafo de LangGraph
                    respuesta_sofia, llamada_finalizada = sesion.procesar_respuesta_cliente(texto_cliente)
                    print(f"🤖 Sofía: {respuesta_sofia}")
                    
                    # 6. Sintetizar y enviar audio por la línea telefónica
                    ruta_audio_resp = await tts_service.sintetizar_audio(respuesta_sofia)
                    with open(ruta_audio_resp, "rb") as f:
                        resp_bytes = f.read()
                        
                    await websocket.send(json.dumps({
                        "event": "media",
                        "media": {"payload": base64.b64encode(resp_bytes).decode()}
                    }))
                    
                    if llamada_finalizada:
                        print("📞 [Fin de la llamada - Colgando]")
                        await websocket.send(json.dumps({"event": "hangup"}))
                        break
                        
            elif event == "stop" or event == "hangup":
                print("📞 [El cliente colgó la llamada]")
                break
                
    finally:
        resumen = sesion.obtener_resumen()
        print("\n📊 Resumen de la llamada:")
        print(json.dumps(resumen, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    print("💡 Este servidor está listo para integrarse con Twilio, Asterisk o FreeSWITCH.")
    print("   Para pruebas locales por micrófono ejecuta: python llamada_voz.py")
