#!/usr/bin/env python3
"""
============================================================
SIMULADOR DE LLAMADA DE VENTAS MOVISTAR (ARGENTINA / VOZ REAL)
============================================================
- Pipeline Concurrente: Streaming Oración a Oración (LLM -> TTS).
- El primer audio comienza a sonar en los altavoces en ~450ms.
- GPU Warm Keeper activo (P2 permanente a 7300MHz).
- Silencio de corte VAD en 350ms para respuesta inmediata.
"""

import time
from core import CallSession, gpu_keeper
from audio import stt_service, tts_service, capturar_audio_microfono_vad

def main():
    print("\n" + "="*65)
    print("📞 LLAMADA DE MOVISTAR ARGENTINA - SOFÍA IA (PIPELINE CONCURRENTE)")
    print("="*65)
    print("💡 Habla naturalmente; el sistema detectará tu voz y silencio.")
    print("="*65)
    
    # 1. Iniciar GPU Keepalive para sostener relojes máximos (P2 / 7300MHz)
    gpu_keeper.start()
    
    # 2. Iniciar sesión de llamada
    sesion = CallSession(client_name="Juan Pérez")
    
    try:
        # 3. Sofía saluda
        saludo_inicial = sesion.iniciar_llamada()
        tts_service.reproducir(saludo_inicial)
        
        # 4. Bucle continuo de la llamada
        while True:
            # Captura audio con corte de silencio en 350ms
            audio_np = capturar_audio_microfono_vad(silencio_corte=0.35, umbral_energia=250)
            
            if audio_np is None:
                print("⚠️ (Silencio prolongado, escuchando nuevamente...)")
                continue
                
            # Transcripción directa en GPU con Whisper (~25ms)
            texto_cliente = stt_service.transcribir_audio(audio_np)
            
            if not texto_cliente:
                continue
                
            print(f"👤 Tú: \"{texto_cliente}\"")
            print("\n🤖 Sofía: ", end="", flush=True)
            
            # Generador de oraciones en streaming directo desde Ollama
            def generador_oraciones_con_log():
                for oracion in sesion.procesar_respuesta_stream(texto_cliente):
                    print(f"{oracion} ", end="", flush=True)
                    yield oracion
                print() # Salto de línea al terminar
                
            # Reproducción concurrente oración por oración en pipe hacia pw-play
            tts_service.reproducir_stream_oraciones(generador_oraciones_con_log())
            
            # Verificar si la llamada concluyó legítimamente
            if sesion.esta_finalizada:
                resumen = sesion.obtener_resumen()
                print("\n" + "="*65)
                if resumen["venta_concretada"]:
                    print("🎉 ¡VENTA CONCRETADA EXITOSAMENTE!")
                else:
                    print("📞 LLAMADA FINALIZADA (Sin venta)")
                print(f"⏱️ Duración total: {resumen['duracion_segundos']}s | Total intercambios: {resumen['total_intercambios']}")
                print("="*65)
                break
    finally:
        # Detener keepalive al colgar
        gpu_keeper.stop()

if __name__ == "__main__":
    main()