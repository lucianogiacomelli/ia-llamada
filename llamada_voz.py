#!/usr/bin/env python3
"""
============================================================
SIMULADOR DE LLAMADA DE VENTAS MOVISTAR (ARGENTINA / VOZ REAL)
============================================================
- FULL DUPLEX CON INTERRUPCIONES (Barge-in):
  Si el cliente habla mientras Sofía está hablando, la voz de Sofía se
  corta inmediatamente (<50ms) y el sistema procesa lo que dijo el cliente.
- Streaming concurrente oración por oración.
- GPU Warm Keeper activo (P2 permanente a 7300MHz).
"""

import time
from core import CallSession, gpu_keeper
from audio import stt_service, tts_service, capturar_audio_con_barge_in

def main():
    print("\n" + "="*65)
    print("📞 LLAMADA DE MOVISTAR ARGENTINA - SOFÍA IA (FULL DUPLEX / BARGE-IN)")
    print("="*65)
    print("💡 Habla naturalmente. Podés interrumpir a Sofía en cualquier momento.")
    print("="*65)
    
    # 1. Iniciar GPU Keepalive para sostener relojes máximos (P2 / 7300MHz)
    gpu_keeper.start()
    
    # 2. Iniciar sesión de llamada
    sesion = CallSession(client_name="Juan Pérez")
    
    try:
        # 3. Turno 0: Saludo inicial con escucha activa simultánea
        saludo_inicial = sesion.iniciar_llamada()
        
        def hablar_saludo():
            tts_service.reproducir(saludo_inicial)
            
        interrumpido, audio_np = capturar_audio_con_barge_in(
            reproducir_fn=hablar_saludo,
            silencio_corte=0.35,
            umbral_energia=250
        )
        
        # 4. Bucle continuo de la llamada
        while True:
            # Si no capturó audio (silencio prolongado), escuchamos de nuevo
            if audio_np is None:
                interrumpido, audio_np = capturar_audio_con_barge_in(
                    reproducir_fn=None,
                    silencio_corte=0.35,
                    umbral_energia=250
                )
                continue
                
            # Transcripción directa en GPU con Whisper (~25ms)
            texto_cliente = stt_service.transcribir_audio(audio_np)
            
            if not texto_cliente:
                interrumpido, audio_np = capturar_audio_con_barge_in(
                    reproducir_fn=None,
                    silencio_corte=0.35,
                    umbral_energia=250
                )
                continue
                
            print(f"👤 Tú: \"{texto_cliente}\"")
            print("\n🤖 Sofía: ", end="", flush=True)
            
            # Preparar generador de respuesta de Sofía
            def responder_sofia_stream():
                def gen():
                    for oracion in sesion.procesar_respuesta_stream(texto_cliente):
                        print(f"{oracion} ", end="", flush=True)
                        yield oracion
                    print()
                tts_service.reproducir_stream_oraciones(gen())
                
            # Escucha full-duplex: reproduce a Sofía pero corta al instante si el cliente habla
            interrumpido, audio_np = capturar_audio_con_barge_in(
                reproducir_fn=responder_sofia_stream,
                silencio_corte=0.35,
                umbral_energia=250
            )
            
            # Verificar si la llamada concluyó legítimamente (cierre de venta o despedida)
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