# your_app_name/routing.py

from django.urls import re_path
from agent_app import consumers

websocket_urlpatterns = [
    re_path(r'ws/agent/$', consumers.AgentConsumer.as_asgi()),
]