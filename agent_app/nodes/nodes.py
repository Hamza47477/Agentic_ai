# nodes/nodes.py

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import spacy
from agent_app.utils import send_message_to_frontend
from pathlib import Path

# --- IMPORTANT: Load spaCy model once ---
try:
    model_dir = Path(__file__).parent.parent # Points to agent_app folder
    model_path = model_dir / "intent_model_spacy"
    nlp_model = spacy.load(str(model_path))
    send_message_to_frontend(f"SpaCy intent model loaded successfully from: {model_path}", message_type="debug_info")
except Exception as e:
    nlp_model = None
    send_message_to_frontend(f"Error loading spaCy model: {e}. Intent classification may not work.", message_type="error")



# --- IMPORTANT: Load spaCy model once ---
try:
    model_dir = Path(__file__).parent.parent
    model_path = model_dir / "intent_model_spacy"
    nlp_model = spacy.load(str(model_path))
    send_message_to_frontend(f"SpaCy intent model loaded successfully from: {model_path}", message_type="debug_info")
except Exception as e:
    nlp_model = None
    send_message_to_frontend(f"Error loading spaCy model: {e}. Intent classification may not work.", message_type="error")


def start_node(state):
    # Check if a primary intent has already been classified in this conversation thread.
    # This relies on the checkpointer loading the persisted 'state'.
    if state.get("is_book") or \
       state.get("is_cancel") or \
       state.get("is_reschedule") or \
       state.get("is_faq"):
        send_message_to_frontend("DEBUG: start_node: Intent already classified for this conversation. Bypassing re-classification.", message_type="debug_info")
        # If an intent is already set, this means we're in a multi-turn flow.
        # Simply return the state. The graph's conditional edges will then evaluate
        # and route to the appropriate node (e.g., BookAppointment if awaiting_info is True).
        return state

    # --- This block runs ONLY if no primary intent has been classified yet (first time in this conversation) ---

    messages = state.get("messages", [])
    user_input = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_input = msg.content
            break
    
    if not user_input:
        send_message_to_frontend("No user input found in latest message for start_node analysis.", message_type="error")
        state["is_faq"] = True # Default to FAQ if no valid input for some reason
        return state

    send_message_to_frontend(f"Start Node processing: '{user_input}' for initial classification.", message_type="debug_info")

    # Initialize flags for intent classification (reset them for this classification pass)
    state["is_book"] = False
    state["is_cancel"] = False
    state["is_reschedule"] = False
    state["is_faq"] = False
    state["User_intention"] = "unknown"

    if nlp_model:
        doc = nlp_model(user_input)
        send_message_to_frontend(f"SpaCy categories raw: {doc.cats}", message_type="debug_info")

        if doc.cats:
            predicted_intent = max(doc.cats, key=doc.cats.get)
            state["User_intention"] = predicted_intent
            send_message_to_frontend(f"Predicted intention by spaCy: '{predicted_intent}'", message_type="status_update")

            if predicted_intent == "book_appointment":
                state["is_book"] = True
            elif predicted_intent == "cancel_appointment":
                state["is_cancel"] = True
            elif predicted_intent == "reschedule_appointment":
                state["is_reschedule"] = True
            elif predicted_intent == "faq":
                state["is_faq"] = True
            else:
                send_message_to_frontend(f"Predicted intent '{predicted_intent}' not explicitly mapped. Defaulting to general questions.", message_type="status_update")
                state["is_faq"] = True
        else:
            send_message_to_frontend("No clear intent detected by spaCy model. Defaulting to general questions.", message_type="status_update")
            state["is_faq"] = True
    else:
        send_message_to_frontend("SpaCy model not loaded. Defaulting to general questions.", message_type="warning")
        state["is_faq"] = True

    send_message_to_frontend(f"Start Node returning with is_book: {state['is_book']}, is_faq: {state['is_faq']}", message_type="debug_info")
    
    return state


def new_appointment_node(state) :
    print("Riley: What type of appointment do you need today? Do you have a provider preference or want the first available?")
    return state

def urgent_triage_node(state) :
    print("Riley: Can you briefly describe your symptoms?")
    return state


def schedule_time_node(state):
    print("Riley: For your appointment, I have August 9 at 10:00 AM or August 10 at 2:00 PM. Which works better?")
    return state

def confirm_appointment_node(state) :
    print("Riley: You're scheduled for your appointment on {} at {}. Please arrive 15 minutes early and bring your insurance card and ID.".format(
        state.get("selected_date"), state.get("selected_time")
    ))
    return state

def general_info_node(state) :
    print("Riley: Clinic hours are Mon–Fri 8am–5pm, Sat 9am–12pm. We accept most insurance plans. Do you want to schedule an appointment?")
    return state

def reschedule_cancel_node(state) :
    print("Riley: Can you provide your name and date of birth so I can locate your appointment? Would you like to reschedule or cancel?")
    return state

def reschedule_node(state) :
    print("Riley: Your current appointment is on Aug 15 at 3 PM. New available times: Aug 20 at 11 AM or Aug 21 at 1 PM. Which would you prefer?")
    return state

def cancel_node(state) :
    print("Riley: I found your appointment on Aug 15. I can cancel this for you. 24-hour notice required to avoid a $50 fee. Would you like to reschedule instead?")
    return state

def emergency_redirect_node(state) :
    print("Riley: This sounds like an emergency. Please call 911 or visit the nearest ER immediately.")
    return state

def end_node(state) :
    print("Riley: Thank you for chatting with Wellness Partners. Have a great day!")
    return state

