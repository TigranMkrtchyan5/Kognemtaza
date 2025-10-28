import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from .models import Room, ChatMessage

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Load room and users
        self.room = await sync_to_async(Room.objects.get)(name=self.room_name)
        users_in_room = await sync_to_async(list)(self.room.users.exclude(id=self.scope["user"].id))
        self.other_user = users_in_room[0]

        # Send chat history
        messages = await sync_to_async(list)(self.room.messages.order_by("created_at"))
        messages_data = [
            {
                "sender_id": msg.sender.id,
                "sender_full_name": msg.sender.profile.full_name,
                "sender_username": msg.sender.username,
                "text": msg.content,
                "created_at": msg.created_at.isoformat()
            } for msg in messages
        ]
        await self.send(text_data=json.dumps({"type": "message_history", "messages": messages_data}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data)
        text = data.get("text", "").strip()
        if not text:
            return

        message = await self.save_message(text)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": {
                    "sender_id": message.sender.id,
                    "sender_full_name": message.sender.profile.full_name,
                    "sender_username": message.sender.username,
                    "text": message.content,
                    "created_at": message.created_at.isoformat()
                }
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({"type": "new_message", "message": event["message"]}))

    @sync_to_async
    def save_message(self, text):
        return ChatMessage.objects.create(
            room=self.room,
            sender=self.scope["user"],
            recipient=self.other_user,
            content=text
        )
