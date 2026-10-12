"""Messenger: JSON API used by the floating chat panel + the group invite page."""

from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST

from .forms import GroupForm, MessageForm, MuteForm, RoomForm, StatusForm, UsernameForm
from .models import Conversation, JoinRequest, Membership, Message, Presence, Room

User = get_user_model()
SEARCH_LIMIT = 10
MESSAGES_LIMIT = 50


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def api_login_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": _("You must be logged in.")}, status=401)
        return view(request, *args, **kwargs)

    return wrapper


def error(message, status=400, errors=None):
    payload = {"error": str(message)}
    if errors:
        payload["errors"] = errors
    return JsonResponse(payload, status=status)


def form_errors(form):
    flat = [str(e) for errs in form.errors.values() for e in errs]
    return error(flat[0] if flat else _("Invalid data."), errors=form.errors.get_json_data())


def membership_or_404(user, conversation_id):
    return get_object_or_404(
        Membership.objects.select_related("conversation"),
        conversation_id=conversation_id,
        user=user,
    )


def owner_membership_or_403(user, conversation_id):
    membership = membership_or_404(user, conversation_id)
    if not membership.conversation.is_owner(user):
        raise PermissionError
    return membership


def owner_only(view):
    @wraps(view)
    def wrapper(request, conversation_id, *args, **kwargs):
        try:
            membership = owner_membership_or_403(request.user, conversation_id)
        except PermissionError:
            return error(_("Only the group owner can do this."), status=403)
        return view(request, membership.conversation, *args, **kwargs)

    return wrapper


def user_json(user, presence=None):
    data = {"id": user.pk, "username": user.username, "display_name": user.display_name}
    if presence is not None:
        data["status"] = presence.status
    return data


def message_json(message, viewer):
    return {
        "id": message.pk,
        "room": message.room_id,
        "author": user_json(message.author),
        "mine": message.author_id == viewer.pk,
        "text": message.text,
        "image_url": (
            reverse("chat:message_image", kwargs={"message_id": message.pk})
            if message.image
            else None
        ),
        "created_at": message.created_at.isoformat(),
    }


def room_json(room):
    return {"id": room.pk, "name": room.display_name, "is_default": room.is_default}


def conversation_summary(membership, user):
    conversation = membership.conversation
    return {
        "id": conversation.pk,
        "kind": conversation.kind,
        "title": conversation.title_for(user),
        "is_owner": conversation.is_owner(user),
        "unread": membership.unread_count(),
        "last_message_id": conversation.last_message_id or 0,
    }


def conversation_detail(membership, request):
    user = request.user
    conversation = membership.conversation
    is_owner = conversation.is_owner(user)
    members = conversation.memberships.select_related("user").order_by("-role", "user__username")
    data = conversation_summary(membership, user)
    data.update(
        {
            "rooms": [room_json(r) for r in conversation.rooms.all()],
            "mute_seconds_left": membership.mute_seconds_left,
            "members": [
                {
                    **user_json(m.user),
                    "role": m.role,
                    "mute_seconds_left": m.mute_seconds_left,
                }
                for m in members
            ],
        }
    )
    if conversation.is_group:
        data["invite_url"] = request.build_absolute_uri(conversation.get_absolute_url())
    if is_owner:
        data["requests"] = [
            {"id": r.pk, "user": user_json(r.user), "created_at": r.created_at.isoformat()}
            for r in conversation.join_requests.filter(status=JoinRequest.PENDING).select_related("user")
        ]
    return data


def detail_response(membership, request, status=200):
    membership.refresh_from_db()
    membership.conversation = Conversation.objects.annotate(
        last_message_id=Max("rooms__messages__id")
    ).get(pk=membership.conversation_id)
    return JsonResponse({"conversation": conversation_detail(membership, request)}, status=status)


# ---------------------------------------------------------------------------
# Presence, user search, conversation list
# ---------------------------------------------------------------------------


@api_login_required
@require_POST
def heartbeat(request):
    """Mark the current user online (optionally changing their status).

    Returns the online users grouped by status and my conversations.
    """
    form = StatusForm(request.POST)
    status = form.cleaned_data.get("status") if form.is_valid() else None
    me = Presence.touch(request.user, status)
    online = (
        Presence.online().exclude(user=request.user).select_related("user").order_by("user__username")
    )
    memberships = (
        Membership.objects.filter(user=request.user)
        .select_related("conversation")
        .order_by("-conversation__created_at")
    )
    conversation_ids = [m.conversation_id for m in memberships]
    last_ids = dict(
        Conversation.objects.filter(pk__in=conversation_ids)
        .annotate(last_message_id=Max("rooms__messages__id"))
        .values_list("pk", "last_message_id")
    )
    conversations = []
    for m in memberships:
        m.conversation.last_message_id = last_ids.get(m.conversation_id)
        conversations.append(conversation_summary(m, request.user))
    conversations.sort(key=lambda c: c["last_message_id"], reverse=True)
    return JsonResponse(
        {
            "me": {**user_json(request.user, me)},
            "users": [user_json(p.user, p) for p in online],
            "conversations": conversations,
        }
    )


@api_login_required
@require_GET
def search_users(request):
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"users": []})
    users = (
        User.objects.filter(is_active=True, username__icontains=query)
        .exclude(pk=request.user.pk)
        .order_by("username")[:SEARCH_LIMIT]
    )
    online = dict(
        Presence.online().filter(user__in=users).values_list("user_id", "status")
    )
    return JsonResponse(
        {"users": [{**user_json(u), "status": online.get(u.pk, "offline")} for u in users]}
    )


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


@api_login_required
@require_POST
def start_direct(request, username):
    other = get_object_or_404(User, username=username, is_active=True)
    if other == request.user:
        return error(_("You cannot start a conversation with yourself."))
    conversation = Conversation.start_direct(request.user, other)
    return detail_response(membership_or_404(request.user, conversation.pk), request)


@api_login_required
@require_POST
def create_group(request):
    form = GroupForm(request.POST)
    if not form.is_valid():
        return form_errors(form)
    with transaction.atomic():
        conversation = Conversation.create_group(request.user, form.cleaned_data["name"])
    return detail_response(membership_or_404(request.user, conversation.pk), request, status=201)


@api_login_required
@require_GET
def conversation(request, conversation_id):
    return detail_response(membership_or_404(request.user, conversation_id), request)


@api_login_required
@require_POST
def leave(request, conversation_id):
    membership = membership_or_404(request.user, conversation_id)
    if not membership.conversation.is_group:
        return error(_("You cannot leave a direct conversation."))
    if membership.is_owner:
        return error(_("The owner cannot leave the group."))
    membership.delete()
    return JsonResponse({"ok": True})


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


def _room_for_member(user, room_id):
    room = get_object_or_404(Room.objects.select_related("conversation"), pk=room_id)
    membership = membership_or_404(user, room.conversation_id)
    return room, membership


@api_login_required
def room_messages(request, room_id):
    room, membership = _room_for_member(request.user, room_id)
    if request.method == "POST":
        return _send_message(request, room, membership)
    if request.method != "GET":
        return error(_("Method not allowed."), status=405)
    queryset = room.messages.select_related("author")
    try:
        after = int(request.GET.get("after", 0))
    except ValueError:
        after = 0
    if after:
        items = list(queryset.filter(pk__gt=after)[:MESSAGES_LIMIT])
    else:
        items = list(queryset.order_by("-pk")[:MESSAGES_LIMIT])[::-1]
    if items and items[-1].pk > membership.last_read_message_id:
        Membership.objects.filter(pk=membership.pk).update(last_read_message_id=items[-1].pk)
    return JsonResponse(
        {
            "messages": [message_json(m, request.user) for m in items],
            "mute_seconds_left": membership.mute_seconds_left,
        }
    )


def _send_message(request, room, membership):
    if membership.is_muted:
        seconds = membership.mute_seconds_left
        return JsonResponse(
            {
                "error": _("You are muted in this conversation."),
                "mute_seconds_left": seconds,
            },
            status=403,
        )
    form = MessageForm(request.POST, request.FILES)
    if not form.is_valid():
        return form_errors(form)
    message = Message.objects.create(
        room=room,
        author=request.user,
        text=form.cleaned_data["text"],
        image=form.cleaned_data.get("image") or "",
    )
    Membership.objects.filter(pk=membership.pk).update(last_read_message_id=message.pk)
    return JsonResponse({"message": message_json(message, request.user)}, status=201)


@login_required
@require_GET
def message_image(request, message_id):
    """Serve chat images only to members of the conversation."""
    message = get_object_or_404(Message.objects.select_related("room"), pk=message_id)
    membership_or_404(request.user, message.room.conversation_id)
    if not message.image:
        raise Http404
    return FileResponse(message.image.open("rb"), content_type="image/webp")


# ---------------------------------------------------------------------------
# Group owner tools
# ---------------------------------------------------------------------------


@api_login_required
@require_POST
@owner_only
def create_room(request, conversation):
    form = RoomForm(request.POST)
    if not form.is_valid():
        return form_errors(form)
    room = Room.objects.create(
        conversation=conversation, name=form.cleaned_data["name"], created_by=request.user
    )
    return JsonResponse({"room": room_json(room)}, status=201)


@api_login_required
@require_POST
@owner_only
def add_member(request, conversation):
    form = UsernameForm(request.POST)
    if not form.is_valid():
        return form_errors(form)
    user = User.objects.filter(username=form.cleaned_data["username"], is_active=True).first()
    if user is None:
        return error(_("User not found."), status=404)
    _m, created = Membership.objects.get_or_create(conversation=conversation, user=user)
    if not created:
        return error(_("This user is already a member."))
    JoinRequest.objects.filter(conversation=conversation, user=user, status=JoinRequest.PENDING).update(
        status=JoinRequest.APPROVED, decided_at=timezone.now()
    )
    return detail_response(membership_or_404(request.user, conversation.pk), request, status=201)


def _target_membership(conversation, user_id):
    target = get_object_or_404(Membership, conversation=conversation, user_id=user_id)
    if target.is_owner:
        raise PermissionError
    return target


@api_login_required
@require_POST
@owner_only
def remove_member(request, conversation, user_id):
    try:
        target = _target_membership(conversation, user_id)
    except PermissionError:
        return error(_("The owner cannot be removed."), status=403)
    target.delete()
    return detail_response(membership_or_404(request.user, conversation.pk), request)


@api_login_required
@require_POST
@owner_only
def mute_member(request, conversation, user_id):
    try:
        target = _target_membership(conversation, user_id)
    except PermissionError:
        return error(_("The owner cannot be muted."), status=403)
    form = MuteForm(request.POST)
    if not form.is_valid():
        return form_errors(form)
    target.mute(form.cleaned_data["minutes"])
    return detail_response(membership_or_404(request.user, conversation.pk), request)


@api_login_required
@require_POST
@owner_only
def decide_request(request, conversation, request_id, decision):
    if decision not in ("approve", "reject"):
        raise Http404
    join_request = get_object_or_404(
        JoinRequest, pk=request_id, conversation=conversation, status=JoinRequest.PENDING
    )
    join_request.decide(approve=decision == "approve")
    return detail_response(membership_or_404(request.user, conversation.pk), request)


# ---------------------------------------------------------------------------
# Group invite link page
# ---------------------------------------------------------------------------


@login_required
def group_link(request, token):
    conversation = get_object_or_404(Conversation, invite_token=token, kind=Conversation.GROUP)
    membership = Membership.objects.filter(conversation=conversation, user=request.user).first()
    join_request = JoinRequest.objects.filter(conversation=conversation, user=request.user).first()
    if request.method == "POST":
        if membership is None:
            if join_request is None:
                JoinRequest.objects.create(conversation=conversation, user=request.user)
            elif join_request.status != JoinRequest.PENDING:
                join_request.status = JoinRequest.PENDING
                join_request.decided_at = None
                join_request.save(update_fields=["status", "decided_at"])
            messages.success(
                request, _("Your request has been sent. The group owner has to approve it.")
            )
        return redirect(conversation.get_absolute_url())
    return render(
        request,
        "chat/group_link.html",
        {
            "conversation": conversation,
            "membership": membership,
            "join_request": join_request,
            "member_count": conversation.memberships.count(),
        },
    )

