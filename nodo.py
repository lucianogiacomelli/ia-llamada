#!/usr/bin/env python3
"""
Módulo de compatibilidad y prueba interactiva por consola.
Exporta el grafo `app` y el tipo `SalesState` desde el paquete `agent`.
"""

from agent.state import SalesState, DecisionLlamada
from agent.graph import app, llm, decisor_llm
from core.call_session import CallSession

# Compatibilidad con imports anteriores
__all__ = ["app", "SalesState", "DecisionLlamada", "llm", "decisor_llm"]

if __name__ == "__main__":
    print("\n" + "="*60)
    print("📞 SIMULADOR DE LLAMADA MOVISTAR (MODO TEXTO / CONSOLA)")
    print("="*60)
    
    sesion = CallSession(client_name="Juan Pérez")
    saludo = sesion.iniciar_llamada()
    print(f"\n🤖 Sofía: {saludo}")
    
    while True:
        cliente_input = input("\n👤 Tú: ").strip()
        if not cliente_input:
            continue
            
        if cliente_input.lower() in ["salir", "exit", "cortar"]:
            print("\n📞 [Llamada cortada]")
            break
            
        respuesta, fin = sesion.procesar_respuesta_cliente(cliente_input)
        print(f"\n🤖 Sofía: {respuesta}")
        
        if fin:
            resumen = sesion.obtener_resumen()
            print("\n" + "="*60)
            if resumen["venta_concretada"]:
                print("🎉 [Venta concretada exitosamente]")
            else:
                print("📞 [Fin de la llamada]")
            print(f"⏱️ Duración: {resumen['duracion_segundos']}s | Operador: {resumen['operador_actual']}")
            print("="*60)
            break