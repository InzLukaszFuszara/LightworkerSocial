from django.contrib import admin

from .models import Conversation, JoinRequest, Membership, Message, Presence, Room


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
    autocomplete_fields = ("user",)
    fields = ("user", "role", "muted_until", "joined_at")
    readonly_fields = ("joined_at",)


class RoomInline(admin.TabularInline):
    model = Room
    extra = 0
    fields = ("name", "is_default", "created_by")
    readonly_fields = ("created_by",)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("__str__", "kind", "owner", "created_at")
    list_filter = ("kind",)
    search_fields = ("name", "owner__username")
    readonly_fields = ("invite_token", "created_at")
    autocomplete_fields = ("owner",)
    inlines = [MembershipInline, RoomInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("__str__", "author", "room", "created_at")
    search_fields = ("text", "author__username")
    list_select_related = ("author", "room")
    raw_id_fields = ("room", "author")


@admin.register(JoinRequest)
class JoinRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "conversation", "status", "created_at")
    list_filter = ("status",)


@admin.register(Presence)
class PresenceAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "last_seen")
    list_filter = ("status",)
