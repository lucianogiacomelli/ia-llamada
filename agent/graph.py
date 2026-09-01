import re
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START, END

from config import OLLAMA_MODEL, OLLAMA_TEMPERATURE
from agent.state import SalesState
from agent.prompts import PROMPT_SISTEMA_SOFIA

# ========================================================
# 1. MODELO OLLAMA CON MEMORIA Y SIN TRUNCAMIENTO
# ========================================================
llm = ChatOllama(
    model=OLLAMA_MODEL,
    temperature=OLLAMA_TEMPERATURE,
    keep_alive="24h",
    num_predict=120     # Espacio amplio para oraciones completas sin cortes bruscos
)

# ========================================================
# 2. NODO CONVERSACIONAL
# ========================================================
def nodo_conversacion(state: SalesState) -> dict:
    mensajes = state.get("messages", [])
    nombre = state.get("client_name", "el titular")
    
    # 1. Turno 0: Saludo inicial saliente
    if not mensajes:
        saludo_directo = f"¡Hola {nombre}! Buenas tardes, te habla Sofía de Movistar. Te llamo para acercarte una bonificación exclusiva del 50% para líneas de Claro, ¿hablo con vos?"
        return {
            "messages": [AIMessage(content=saludo_directo)],
            "stage": "esperando_sondeo"
        }
        
    # 2. Turnos subsiguientes: Mantiene hasta 16 mensajes para recordar toda la llamada
    mensajes_recientes = mensajes[-16:] if len(mensajes) > 16 else mensajes
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", PROMPT_SISTEMA_SOFIA.format(client_name=nombre)),
        MessagesPlaceholder(variable_name="messages")
    ])
    chain = prompt | llm
    respuesta_ai = chain.invoke({"messages": mensajes_recientes})
    
    texto_raw = respuesta_ai.content
    sale_closed = False
    stage = "evaluando_respuesta"
    
    if "[VENTA_CONFIRMADA]" in texto_raw:
        sale_closed = True
        stage = "finalizado"
    elif "[LLAMADA_TERMINADA]" in texto_raw:
        sale_closed = False
        stage = "finalizado"
        
    texto_limpio = limpiar_texto_modelo(texto_raw)
    
    return {
        "messages": [AIMessage(content=texto_limpio)],
        "sale_closed": sale_closed,
        "stage": stage
    }

def limpiar_texto_modelo(texto: str) -> str:
    """
    Limpia etiquetas internas, filtra caracteres chinos/extraños de Qwen
    y asegura que las oraciones no queden truncadas en símbolos como ¿ o comas.
    """
    # 1. Remover etiquetas de control
    texto = texto.replace("[VENTA_CONFIRMADA]", "").replace("[LLAMADA_TERMINADA]", "")
    texto = re.sub(r'\[.*?\]', '', texto)
    
    # 2. Filtro estricto de caracteres CJK (Chino / Japonés / Coreano)
    texto = re.sub(r'[\u4e00-\u9fff\u3400-\u4dbf]+', '', texto)
    
    # 3. Limpiar espacios repetidos
    texto = re.sub(r'\s+', ' ', texto).strip()
    
    # 4. Eliminar signos de apertura huérfanos al final (ej: "¿", "¡", ",")
    texto = re.sub(r'[\¿\¡\,\:\-]\s*$', '', texto).strip()
    
    return texto

# ========================================================
# 3. GRAFO LANGGRAPH
# ========================================================
workflow = StateGraph(SalesState)
workflow.add_node("conversacion", nodo_conversacion)
workflow.add_edge(START, "conversacion")
workflow.add_edge("conversacion", END)

app = workflow.compile()
