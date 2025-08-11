# your_app_name/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('agent/', views.agent_interface, name='agent_interface'),
]