from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/chat/room_<str:room_name>/', consumers.ChatConsumer.as_asgi()),
    path('ws/global/', consumers.GlobalConsumer.as_asgi()),
    
]
