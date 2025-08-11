# nodes/book_appointment.py (or wherever your customer_type_node_factory is)

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage # Ensure AIMessage is imported
import json
from agent_app.utils import send_message_to_frontend # Import your utility function


def customer_type_node_factory(model):
    def node(state):
        # Retrieve the latest user message from the state
        # The consumer is responsible for adding the new HumanMessage to the state
        messages = state.get("messages", [])
        last_human_message_content = ""
        for msg in reversed(messages): # Find the last HumanMessage
            if isinstance(msg, HumanMessage):
                last_human_message_content = msg.content
                break

        # If this node is entered without a specific prompt from the previous node,
        # or if it's the first time processing, ask the initial question.
        # You might want more sophisticated logic here based on graph flow.
        if "customer_type_prompt_sent" not in state: # Check if the initial prompt was sent
            send_message_to_frontend("Are you a new patient to Wellness Partners, or have you visited us before?", message_type="agent_response")
            state["customer_type_prompt_sent"] = True # Mark that the prompt has been sent
            # Since we just sent a prompt, we need to wait for the user's response.
            # The graph will be reinvoked by the consumer with the next user message.
            # We return the state to allow the graph to await the next input.
            return state

        # If we have a response from the user after the initial prompt
        user_input_for_classification = last_human_message_content

        # Store first message (This might need re-evaluation based on your graph's message accumulation)
        # state["messages"] = [HumanMessage(content=user_input_for_classification)] # This might overwrite history
        
        # Initialize flags in state if they don't exist
        state["is_new_user"] = state.get("is_new_user")
        state["patient_name"] = state.get("patient_name")
        state["patient_email"] = state.get("patient_email")
        state["patient_DOB"] = state.get("patient_DOB")
        state["emergency"] = state.get("emergency")
        state["awaiting_info"] = False # Flag to indicate if we're waiting for info

        # --- First turn: Classify new/existing patient ---
        if state.get("is_new_user") is None: # Only classify if not yet classified
            classification_prompt = [
                SystemMessage(content="You are an assistant that classifies whether the user is a new or existing patient. If user says 'yes i am' or 'yes' it means it a new patient because my question is :Are you a new patient to Wellness Partners, or have you visited us before? "),
                HumanMessage(content="""
                Classify the user's response into JSON with the field:
                customer_type: "new", "existing", or null if unsure.
                """),
                HumanMessage(content=user_input_for_classification)
            ]

            try:
                model_response = model.invoke(classification_prompt).content
                parsed = json.loads(model_response)
                customer_type = parsed.get("customer_type")
            except Exception as e:
                send_message_to_frontend(f"Error classifying customer type: {e}", message_type="error")
                customer_type = None

            state["is_new_user"] = (customer_type == "new")

            # Choose intro prompt based on classification
            if customer_type == "new":
                response_text = "Great! Let's get started with your new appointment. Please provide your full name, email, date of birth (YYYY-MM-DD), and whether the appointment is 'emergency' or 'regular'."
                #state["awaiting_info"] = True # We are now awaiting more info
            elif customer_type == "existing":
                response_text = "Great! Let's get started. Please provide your full name and email address."
                #state["awaiting_info"] = True # We are now awaiting more info
            else:
                response_text = "I'm sorry, I couldn't understand if you are a new or existing patient. Please clarify before continuing."
                #state["awaiting_info"] = True # Still awaiting clarification
            
            send_message_to_frontend(response_text, message_type="agent_response")
            return state # Return state to wait for next user input

        # --- Subsequent turns: Extract details ---
        # If we reach here, customer_type is already classified, now extract details
        extraction_prompt_messages = [HumanMessage(content=last_human_message_content)]
        if state["is_new_user"]:
            extraction_prompt_messages.insert(0, SystemMessage(content="""
                Extract the following from the user's message as JSON:
                full_name (string or null),
                email (string or null),
                date_of_birth (YYYY-MM-DD or null),
                is_emergency (boolean or null).
                If a field is missing, return null for it.
                """))
        else:
            extraction_prompt_messages.insert(0, SystemMessage(content="""
                Extract the following from the user's message as JSON:
                full_name (string or null),
                email (string or null),
                is_emergency (boolean or null).
                If a field is missing, return null for it.
                """))

        try:
            model_response = model.invoke(extraction_prompt_messages).content
            parsed = json.loads(model_response)
        except Exception as e:
            send_message_to_frontend(f"Error extracting details: {e}", message_type="error")
            parsed = {}

        # Update collected info with extracted values
        if not state["patient_name"] and parsed.get("full_name"):
            state["patient_name"] = parsed["full_name"]
        if not state["patient_email"] and parsed.get("email"):
            state["patient_email"] = parsed["email"]
        if state["emergency"] is None and parsed.get("is_emergency") is not None:
            state["emergency"] = parsed["is_emergency"]
        if state["is_new_user"] and not state["patient_DOB"] and parsed.get("date_of_birth"):
            state["patient_DOB"] = parsed["date_of_birth"]

        # Check if all required info is collected
        all_info_collected = False
        if state["is_new_user"]:    # for new patient
            if state["patient_name"] and state["patient_email"] and state["patient_DOB"]:
                all_info_collected = True
        else:
            if state["patient_name"] and state["patient_email"]:        # for returning patient
                all_info_collected = True

        if all_info_collected:
            send_message_to_frontend("Thank you! I have all the necessary information.")
            state["awaiting_info"] = False # All info collected, ready to proceed
        else:
            # Tell the user what’s missing
            missing_parts = []
            if not state["patient_name"]:
                missing_parts.append("your full name")
            if not state["patient_email"]:
                missing_parts.append("your email")
            if state["is_new_user"] and not state["patient_DOB"]:
                missing_parts.append("your date of birth (YYYY-MM-DD)")
            if missing_parts:
                send_message_to_frontend(f"We’re almost there! Just need {', and '.join(missing_parts)}.", message_type="agent_response")
        send_message_to_frontend(f"Current patient info collected: {state['patient_name']}, {state['patient_email']}, {state['patient_DOB']}, Emergency: {state['emergency']}", message_type="debug_info")

        return state

    return node


def cancel_appointment():
    
    
    print('cancelling the appointment')
    
    return

def rechedule_appointment():
    print("Recheduling appointment")
    return

def general_questions():
    
    pass