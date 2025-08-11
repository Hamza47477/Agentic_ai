import json
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def send_message_to_frontend(message_content: str, message_type: str = 'agent_response', user_id: str = None):
    """
    Sends a message to all connected WebSocket clients in the 'agent_messages_group'.
    If a user_id is provided, it attempts to send to a group specific to that user.

    Args:
        message_content (str): The text message to send to the frontend.
        message_type (str): A string indicating the type of message (e.g., 'status_update', 'final_answer').
                            This helps the frontend differentiate and display messages.
        user_id (str, optional): An optional user ID to send a message to a specific user's group.
                                 If None, sends to the general 'agent_messages_group'.
    Returns:
        dict: A dictionary indicating the status of the message sending operation.
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        print("Error: Channel layer not configured. Cannot send message to frontend.")
        return {"status": "error", "message": "Channel layer not configured"}

    # Define the group name. You might want to make this more dynamic
    # if you have per-user or per-conversation groups.
    if user_id:
        group_name = f'user_{user_id}_group' # Example: send to a specific user's group
    else:
        group_name = 'agent_messages_group' # General group for all connected clients

    event = {
        'type': 'send_agent_message', # This calls the 'send_agent_message' method on the consumer
        'message': message_content,
        'message_type': message_type, # Custom type for frontend interpretation
        'sender': 'backend_agent' # Optional: Add sender info
    }

    try:
        # async_to_sync is crucial for calling async channel layer methods from sync code
        async_to_sync(channel_layer.group_send)(group_name, event)
        print(f"Message sent to frontend group '{group_name}' (type: {message_type}): {message_content}")
        return {"status": "success", "message": "Message sent to frontend"}
    except Exception as e:
        print(f"Error sending message to frontend via channel layer: {e}")
        return {"status": "error", "message": f"Failed to send message: {e}"}
