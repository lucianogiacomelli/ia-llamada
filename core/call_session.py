import time
from langchain_core.messages import HumanMessage
from agent.graph import app
from agent.state import SalesState

class CallSession:
    """
    Controlador del ciclo de vida de una llamada de venta real.
    Garantiza que la llamada continúe hasta que el cliente realmente cierre la venta (DNI) o corte.
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
        self.state = app.invoke(self.state)
        return self.state["messages"][-1].content
        
    def procesar_respuesta_cliente(self, texto_cliente: str) -> tuple[str, bool]:
        """
        Procesa la respuesta del cliente a través del grafo de LangGraph.
        Retorna: (respuesta_sofia, llamada_finalizada)
        """
        if not texto_cliente:
            return "Disculpame, no te escuché bien. ¿Me podrías repetir?", False
            
        # Comprobar si el cliente pide cortar explícitamente
        if any(w in texto_cliente.lower() for w in ["cortar", "adiós", "chau", "no me interesa", "no me llames más"]):
            self.state["stage"] = "finalizado"
            self.state["intent"] = "rechazo"
            self.end_time = time.time()
            return "Muchas gracias por tu tiempo, que tengas una excelente tarde. ¡Hasta luego!", True
            
        # Añadir al historial
        self.state["messages"].append(HumanMessage(content=texto_cliente))
        
        # Invocación de 1 sola pasada al grafo
        self.state = app.invoke(self.state)
        
        respuesta_sofia = self.state["messages"][-1].content
        
        # La llamada SOLO finaliza si el estado es 'finalizado'
        llamada_terminada = (self.state.get("stage") == "finalizado")
        if llamada_terminada:
            self.end_time = time.time()
            
        return respuesta_sofia, llamada_terminada
        
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
