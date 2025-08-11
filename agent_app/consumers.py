# Agentic_ai/agent_app/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from langchain_core.messages import HumanMessage, AIMessage
from agent_app.agent_workflow import app as langgraph_app
from agent_app.agent_workflow import memory as checkpointer

class AgentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.thread_id = str(self.channel_name)

        self.agent_group_name = 'agent_messages_group'
        await self.channel_layer.group_add(
            self.agent_group_name,
            self.channel_name
        )
        await self.accept()
        print(f"WebSocket connected: {self.channel_name}, Thread ID: {self.thread_id}")

        loaded_state = None
        try:
            loaded_state_checkpoint = await sync_to_async(checkpointer.get_tuple)(
                {"configurable": {"thread_id": self.thread_id}}
            )
            
            if loaded_state_checkpoint and loaded_state_checkpoint.checkpoint and loaded_state_checkpoint.checkpoint['graph_state']:
                loaded_state = loaded_state_checkpoint.checkpoint['graph_state']
                print(f"Resuming conversation for thread ID: {self.thread_id}, Loaded Messages: {[m.content for m in loaded_state.get('messages', [])]}")
                # NEW: Print the full loaded state (graph_state) here
                print(f"DEBUG: Loaded graph_state on connect: {loaded_state}")
                await self.send(text_data=json.dumps({
                    'type': 'agent_response',
                    'message': 'Welcome back! How can I help you continue?'
                }))
            else:
                print(f"Starting new conversation for thread ID: {self.thread_id}")
                await self.send(text_data=json.dumps({
                    'type': 'agent_response',
                    'message': 'Thank you for contacting Wellness Partners. This is Riley. How may I help you today?'
                }))
        except Exception as e:
            print(f"Error loading state for thread {self.thread_id}: {e}. Starting fresh.")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Error starting conversation: {str(e)}'
            }))
        
        self.scope['session_state'] = loaded_state if loaded_state is not None else {"messages": []}


    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.agent_group_name,
            self.channel_name
        )
        print(f"WebSocket disconnected: {self.channel_name}")

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        user_message_content = text_data_json.get('message', '')
        message_type = text_data_json.get('type', 'user_message')

        if message_type == 'system_command' and user_message_content == 'RESET_CONVERSATION':
            await sync_to_async(checkpointer.at_checkpoint)(
                 {"configurable": {"thread_id": self.thread_id}},
                 {"messages": [], "customer_type_prompt_sent": False, "awaiting_info": False}
            )
            self.scope['session_state'] = {"messages": [], "customer_type_prompt_sent": False, "awaiting_info": False}
            await self.send(text_data=json.dumps({
                'type': 'reset_confirmed',
                'message': 'Conversation state reset successfully.'
            }))
            print(f"Conversation state reset for thread ID: {self.thread_id}")
            await self.send(text_data=json.dumps({
                'type': 'agent_response',
                'message': 'Thank you for contacting Wellness Partners. This is Riley. How may I help you today?'
            }))
            return

        if not user_message_content:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Empty message received.'
            }))
            return

        # NEW: Get the current state from the local session, which should reflect the last checkpoint.
        current_state_from_session = self.scope.get('session_state', {"messages": []})
        print(f"DEBUG: State before invoke (from session): {current_state_from_session}")

        langgraph_input = {"messages": [HumanMessage(content=user_message_content)]}
        config = {"configurable": {"thread_id": self.thread_id}}

        try:
            new_state = await sync_to_async(langgraph_app.invoke)(langgraph_input, config=config)
            
            self.scope['session_state'] = new_state 
            print(f"Langgraph finished. Updated state (latest messages): {[m.content for m in new_state.get('messages', [])]}")
            # NEW: Print the full new state after invoke (this is what's saved to checkpointer)
            print(f"DEBUG: Full graph_state after invoke: {new_state}")

        except Exception as e:
            print(f"Error invoking Langgraph: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'An error occurred while processing your request: {str(e)}'
            }))
            self.scope['session_state'] = {"messages": []}


    async def send_agent_message(self, event):
        message_type = event.get('message_type', 'agent_response')
        message_content = event['message']
        sender_info = event.get('sender', 'Agent')
        await self.send(text_data=json.dumps({
            'type': message_type,
            'message': message_content,
            'sender': sender_info
        }))
