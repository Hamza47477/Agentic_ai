# nodes/general_questions.py

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from agent_app.utils import send_message_to_frontend # Ensure this import is correct
import json # Import json for parsing LLM response

def general_question_node_factory(model):
    def node(state):
        # 1. Add System Message (if not already present)
        # This ensures the LLM has context about its role and available information.
        # It uses 'send_message_to_frontend' for debugging, but the SystemMessage itself
        # is for the LLM's context, not directly for the user.
        if not any(isinstance(msg, SystemMessage) and "Wellness Partners" in msg.content for msg in state.get("messages", [])):
            state.setdefault("messages", []).insert(0, SystemMessage(content="""
You are Riley, the friendly appointment scheduling assistant for Wellness Partners health clinic. 
Your job is to answer user questions clearly, accurately, and politely. 
You know the following information about the clinic:

 **General Information**
- Name: Wellness Partners Health Clinic
- Location: 123 Main Street, Springfield
- Contact: (555) 123-4567, email: info@wellnesspartners.com

**Here's what you can do**

Answer questions about the clinic's services, hours, and location.
Book a new appointment for you.
Update an existing appointment, like changing the time or service.
Cancel an appointment if you need to.

 **Opening Hours**
- Monday to Friday: 8:00 AM – 6:00 PM
- Saturday: 9:00 AM – 2:00 PM
- Sunday: Closed

 **Closed Days**
- Sundays
- Public Holidays

 **Services Provided**
- Primary Care
- Specialist Consultations (Cardiology, Dermatology, Pediatrics, etc.)
- Diagnostic Services (Blood Tests, X-rays, Ultrasound)
- Wellness & Preventive Care (Vaccinations, Annual Checkups)
- Urgent Care (non-life-threatening emergencies)

 **Other Notes**
- Same-day appointments available for urgent cases
- Telehealth appointments available for select services
- Walk-ins are accepted, but booking is recommended

When answering:
- Be concise but friendly
- If unsure, politely say you don't know and suggest calling the clinic
- Only provide information relevant to the question
"""))
            send_message_to_frontend("DEBUG: System message added to state for General Questions.", message_type="debug_info")

        # 2. Retrieve the latest user message from the state
        # The consumer appends the new HumanMessage to the state before invoking the graph.
        last_human_message_content = ""
        messages = state.get("messages", [])
        # Find the latest HumanMessage that wasn't just a system message or AI response.
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_human_message_content = msg.content
                break
        
        if not last_human_message_content:
            send_message_to_frontend("DEBUG: General Question Node: No user input to process.", message_type="debug_info")
            # If no actual user input is found, perhaps it was just a transition.
            # We return state, and the graph's overall conditional edges will decide next.
            return state

        send_message_to_frontend(f"DEBUG: General Question Node processing: '{last_human_message_content}'", message_type="debug_info")

        # 3. Dynamic Intent Detection using Chat Model
        # This allows users to switch context from general questions to specific actions.
        # It will try to classify the user's intent to route to "BookAppointment", etc.
        intent_classification_prompt = [
            SystemMessage(content="""
            You are an expert intent classifier. Analyze the user's message and determine if they want to:
            - 'book_appointment'
            - 'reschedule_appointment'
            - 'cancel_appointment'
            - 'general_question' (if none of the above actions are clearly intended)

            Return your classification as a JSON object with a single key 'intent' and the corresponding value.
            Example: {"intent": "book_appointment"}
            Example: {"intent": "general_question"}
            """),
            HumanMessage(content=last_human_message_content)
        ]

        try:
            intent_model_response = model.invoke(intent_classification_prompt).content
            parsed_intent = json.loads(intent_model_response)
            detected_intent = parsed_intent.get("intent")
            send_message_to_frontend(f"DEBUG: Detected intent in General Q: '{detected_intent}'", message_type="debug_info")

            # Reset all routing flags first to prevent stale state
            state["is_book"] = False
            state["is_cancel"] = False
            state["is_reschedule"] = False
            state["is_faq"] = False # This will be set below if it's a general question

            if detected_intent == "book_appointment":
                state["is_book"] = True
                send_message_to_frontend("DEBUG: Routing to book appointment from general questions.", message_type="debug_info")
                return state # IMMEDIATELY return to allow graph to re-evaluate and transition
            elif detected_intent == "reschedule_appointment":
                state["is_reschedule"] = True
                send_message_to_frontend("DEBUG: Routing to reschedule from general questions.", message_type="debug_info")
                return state # IMMEDIATELY return
            elif detected_intent == "cancel_appointment":
                state["is_cancel"] = True
                send_message_to_frontend("DEBUG: Routing to cancel from general questions.", message_type="debug_info")
                return state # IMMEDIATELY return
            # If it's a general_question or an unrecognized intent, proceed to answer it.
            # No 'return state' here, as we fall through to the next block.

        except Exception as e:
            send_message_to_frontend(f"Error classifying intent in general questions: {e}. Defaulting to general.", message_type="error")
            detected_intent = "general_question" # Fallback to general question if LLM classification fails

        # 4. Process General Question with LLM (Only if not routed to an action intent)
        # This part runs if detected_intent was 'general_question' or if intent classification failed.
        if detected_intent == "general_question":
            try:
                # Invoke the LLM with the current conversation history (including the system message)
                response = model.invoke(state["messages"])
                answer = response.content
                send_message_to_frontend(f"Riley: {answer}", message_type="agent_response") # Send to frontend!
            except Exception as e:
                answer = f"Sorry, I couldn't process your question due to an internal error. Please try again. (Error: {e})"
                send_message_to_frontend(answer, message_type="error") # Send error to frontend

            # 5. Store Bot's Answer and Update State
            state["messages"].append(AIMessage(content=answer))
            state["is_faq"] = True  # Keep the graph in the 'general_questions' state unless intent explicitly changes.
            send_message_to_frontend("DEBUG: General question answered. Remaining in FAQ state.", message_type="debug_info")

            return state # IMPORTANT: Return state to pause and wait for the next user input!

        # Fallback if somehow intent wasn't 'general_question' and also didn't route
        # (This should ideally not be reached if intent classification is robust)
        send_message_to_frontend("DEBUG: General question node completed or unexpectedly reached end without clear action.", message_type="debug_info")
        return state

    return node
