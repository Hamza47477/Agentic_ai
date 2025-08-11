# Agentic_ai/agent_app/agent_workflow.py

from typing import Annotated, TypedDict, Literal, Optional, List
from .nodes.nodes import start_node
from .nodes.book_appointment import customer_type_node_factory
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages, BaseMessage
from langchain_openai import ChatOpenAI
from .nodes.general_questions import general_question_node_factory
from langchain_core.messages import HumanMessage
from agent_app.utils import send_message_to_frontend

# NEW: Import MemorySaver
from langgraph.checkpoint.memory import MemorySaver # <--- CHANGE THIS IMPORT

model = ChatOpenAI(
    api_key= "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"
)


class AppointmentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    is_book: bool
    is_cancel: bool
    is_new_user: bool
    is_reschedule: bool
    is_faq: bool
    patient_name: str
    patient_email: str
    patient_DOB : str
    emergency: bool
    initial_greeting_sent: bool
    customer_type_prompt_sent: bool
    awaiting_info: bool

# NEW: Initialize MemorySaver
memory = MemorySaver() # <--- CHANGE THIS INITIALIZATION


# compile the state graph
graph = StateGraph(AppointmentState)


# defining nodes
graph.add_node("start_node", start_node)
graph.add_node("BookAppointment", customer_type_node_factory(model))
graph.add_node('general_questions' , general_question_node_factory(model))


# defining edges
graph.set_entry_point("start_node")

graph.add_conditional_edges(
    "start_node",
    lambda state: (
        "BookAppointment" if state.get("is_book") else
        "CancelAppointment" if state.get("is_cancel") else
        "RecheduleAppointment" if state.get("is_reschedule") else
        "general_questions" if state.get("is_faq") else
        END
    ),
)

graph.add_conditional_edges(
    "BookAppointment",
    lambda state: (
        "BookAppointment" if state.get("awaiting_info") else
        "ConfirmAppointment"
    ),
)

graph.add_conditional_edges(
    "general_questions",
    lambda state: (
        "BookAppointment" if state.get("is_book") else
        "CancelAppointment" if state.get("is_cancel") else
        "RecheduleAppointment" if state.get("is_reschedule") else
        END
    ),
)



# Compile the graph with the checkpointer
app = graph.compile(checkpointer=memory)