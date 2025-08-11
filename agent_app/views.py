# your_app_name/views.py
from django.shortcuts import render

def agent_interface(request):
    return render(request, 'agent_app/index.html')