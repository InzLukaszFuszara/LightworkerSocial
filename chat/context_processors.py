from django.conf import settings
from django.urls import reverse


def chat(request):
    """Configuration of the floating messenger for the JavaScript client."""
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {}
    config = {
        "maxLength": settings.CHAT_MESSAGE_MAX_LENGTH,
        "maxImageBytes": settings.CHAT_IMAGE_MAX_BYTES,
        "heartbeatSeconds": settings.CHAT_HEARTBEAT_SECONDS,
        "pollSeconds": settings.CHAT_POLL_SECONDS,
        "muteChoices": settings.CHAT_MUTE_CHOICES,
        "me": request.user.pk,
        "urls": {
            "heartbeat": reverse("chat:heartbeat"),
            "search": reverse("chat:search_users"),
            "createGroup": reverse("chat:create_group"),
            "direct": reverse("chat:start_direct", kwargs={"username": "__USERNAME__"}),
            "conversation": reverse("chat:conversation", kwargs={"conversation_id": 0}),
            "messages": reverse("chat:room_messages", kwargs={"room_id": 0}),
        },
    }
    return {"chat_config": config}
