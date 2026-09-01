import re
import time
from typing import Generator
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from agent.graph import llm, limpiar_texto_modelo
from agent.prompts import PROMPT_SISTEMA_SOFIA
from agent.state import SalesState

DELIMITERS = re.compile(r"([.!?\n]+)")

class CallSession:
    """
    Controlador del ciclo de vida de una llamada de venta real con streaming concurrente.
    Emite oraciones individuales en tiempo real apenas están disponibles.
    """
    
    def __init__(self, client_name: str = "Juan Pérez", client_phone: str | None = None):
        self.client_name = client_name
        self.client_phone = client_phone
        self.start_time = time.time()
        self.end_time = None
        
        self.state: SalesState = {
            "messages": [],
            "client_name": self.client_name,
            "client_phone": self.client_phone,
            "current_operator": None,
            "dni_cliente": None,
            "localidad_cliente": None,
            "objection_count": 0,
            "intent": "indefinido",
            "stage": "inicio",
            "sale_closed": False
        }
        
    def iniciar_llamada(self) -> str:
        """Sofía inicia la llamada con el saludo inicial."""
        saludo = f"¡Hola {self.client_name}! Buenas tardes, te habla Sofía de Movistar. Te llamo para acercarte una bonificación exclusiva del 50% para líneas de Claro, ¿hablo con vos?"
        self.state["messages"].append(AIMessage(content=saludo))
        self.state["stage"] = "esperando_sondeo"
        return saludo
        
    def procesar_respuesta_stream(self, texto_cliente: str) -> Generator[str, None, None]:
        """
        Generador que produce oraciones individuales en tiempo real apenas están listas.
        Permite que el TTS comience a hablar de inmediato sin esperar al final del párrafo.
        """
        if not texto_cliente:
            yield "Disculpame, no te escuché bien. ¿Me podrías repetir?"
            return
            
        # Detección temprana de corte
        if any(w in texto_cliente.lower() for w in ["cortar", "adiós", "chau", "no me interesa", "no me llames más"]):
            self.state["stage"] = "finalizado"
            self.state["intent"] = "rechazo"
            self.end_time = time.time()
            despedida = "Muchas gracias por tu tiempo, que tengas una excelente tarde. ¡Hasta luego!"
            self.state["messages"].append(HumanMessage(content=texto_cliente))
            self.state["messages"].append(AIMessage(content=despedida))
            yield despedida
            return

        self.state["messages"].append(HumanMessage(content=texto_cliente))
        mensajes_recientes = self.state["messages"][-16:]
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", PROMPT_SISTEMA_SOFIA.format(client_name=self.client_name)),
            MessagesPlaceholder(variable_name="messages")
        ])
        chain = prompt | llm
        
        buffer = ""
        texto_acumulado = ""
        
        for chunk in chain.stream({"messages": mensajes_recientes}):
            buffer += chunk.content
            texto_acumulado += chunk.content
            
            parts = DELIMITERS.split(buffer)
            if len(parts) > 1:
                for i in range(0, len(parts) - 1, 2):
                    oracion = (parts[i] + parts[i+1]).strip()
                    oracion_limpia = limpiar_texto_modelo(oracion)
                    if len(oracion_limpia) > 2:
                        yield oracion_limpia
                buffer = parts[-1]
                
        if buffer.strip():
            restante = limpiar_texto_modelo(buffer)
            if len(restante) > 2:
                yield restante
                
        # Actualizar estado según etiquetas de control
        if "[VENTA_CONFIRMADA]" in texto_acumulado:
            self.state["sale_closed"] = True
            self.state["stage"] = "finalizado"
            self.end_time = time.time()
        elif "[LLAMADA_TERMINADA]" in texto_acumulado:
            self.state["sale_closed"] = False
            self.state["stage"] = "finalizado"
            self.end_time = time.time()
            
        texto_limpio_final = limpiar_texto_modelo(texto_acumulado)
        self.state["messages"].append(AIMessage(content=texto_limpio_final))

    @property
    def esta_finalizada(self) -> bool:
        return self.state.get("stage") == "finalizado"

    def obtener_resumen(self) -> dict:
        duracion = round((self.end_time or time.time()) - self.start_time, 2)
        return {
            "cliente": self.client_name,
            "telefono": self.client_phone,
            "dni_registrado": self.state.get("dni_cliente"),
            "localidad_registrada": self.state.get("localidad_cliente"),
            "duracion_segundos": duracion,
            "venta_concretada": self.state.get("sale_closed", False),
            "operador_anterior": self.state.get("current_operator"),
            "intencion_final": self.state.get("intent"),
            "total_intercambios": len(self.state["messages"]),
            "transcripcion": [
                {"rol": "Sofía" if m.type == "ai" else "Cliente", "texto": m.content}
                for m in self.state["messages"]
            ]
        }
