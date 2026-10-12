from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    path("g/<uuid:token>/", views.group_link, name="group_link"),
    path("api/heartbeat/", views.heartbeat, name="heartbeat"),
    path("api/users/", views.search_users, name="search_users"),
    path("api/direct/<str:username>/", views.start_direct, name="start_direct"),
    path("api/groups/", views.create_group, name="create_group"),
    path("api/conversations/<int:conversation_id>/", views.conversation, name="conversation"),
    path("api/conversations/<int:conversation_id>/leave/", views.leave, name="leave"),
    path("api/conversations/<int:conversation_id>/rooms/", views.create_room, name="create_room"),
    path("api/conversations/<int:conversation_id>/members/", views.add_member, name="add_member"),
    path(
        "api/conversations/<int:conversation_id>/members/<int:user_id>/remove/",
        views.remove_member,
        name="remove_member",
    ),
    path(
        "api/conversations/<int:conversation_id>/members/<int:user_id>/mute/",
        views.mute_member,
        name="mute_member",
    ),
    path(
        "api/conversations/<int:conversation_id>/requests/<int:request_id>/<str:decision>/",
        views.decide_request,
        name="decide_request",
    ),
    path("api/rooms/<int:room_id>/messages/", views.room_messages, name="room_messages"),
    path("api/messages/<int:message_id>/image/", views.message_image, name="message_image"),
]
