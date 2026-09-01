from typing import TypedDict, Annotated, Literal
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

# ========================================================
# 1. ESTADO DE LA LLAMADA (LangGraph State)
# ========================================================
class SalesState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    client_name: str
    client_phone: str | None
    current_operator: str | None
    dni_cliente: str | None
    localidad_cliente: str | None
    objection_count: int
    intent: Literal["interesado", "objecion_precio", "objecion_otra", "rechazo", "datos_dni", "duda_o_aclaracion", "indefinido"]
    stage: Literal["inicio", "esperando_sondeo", "esperando_oferta", "evaluando_respuesta", "pidiendo_datos", "finalizado"]
    sale_closed: bool

# ========================================================
# 2. ESQUEMA DE DECISIÓN Y RESPUESTA (1 sola pasada)
# ========================================================
class DecisionLlamada(BaseModel):
    intencion: Literal["interesado", "objecion_precio", "objecion_otra", "rechazo", "datos_dni", "duda_o_aclaracion"] = Field(
        description="Clasificación exacta de lo que dijo el cliente."
    )
    operador: str | None = Field(
        default=None,
        description="Compañía telefónica mencionada si la dijo (Claro, Personal, Tuenti, etc.), sino null."
    )
    dni_detectado: str | None = Field(
        default=None,
        description="Número de DNI o documento si el cliente lo mencionó, sino null."
    )
    localidad_detectada: str | None = Field(
        default=None,
        description="Ciudad, localidad o dirección si el cliente la mencionó, sino null."
    )
    respuesta_sofia: str = Field(
        description="La respuesta hablada de Sofía. En español argentino natural, con precios siempre en 'pesos' (nunca $, nunca dólares). Máximo 2 oraciones breves y cálidas."
    )
    accion: Literal["pedir_datos", "confirmar_cierre", "negociar", "aclarar", "despedida"] = Field(
        description="'pedir_datos' si el cliente acepta y pedimos DNI; 'confirmar_cierre' si ya dio su DNI/datos para finalizar venta; 'negociar' si pone objeción; 'aclarar' si tiene dudas o audio confuso; 'despedida' si rechaza."
    )
