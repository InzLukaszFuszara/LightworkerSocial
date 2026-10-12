import math
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.validators import MaxLengthValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from posts.images import convert_to_webp


class Presence(models.Model):
    """Online status of a logged in user, kept fresh by heartbeats."""

    AVAILABLE = "available"
    AWAY = "away"
    STATUS_CHOICES = [(AVAILABLE, _("Available")), (AWAY, _("Be right back"))]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="presence",
        verbose_name=_("user"),
    )
    status = models.CharField(_("status"), max_length=10, choices=STATUS_CHOICES, default=AVAILABLE)
    last_seen = models.DateTimeField(_("last seen"), default=timezone.now, db_index=True)

    class Meta:
        verbose_name = _("presence")
        verbose_name_plural = _("presence")

    def __str__(self):
        return f"{self.user} ({self.status})"

    @classmethod
    def online_cutoff(cls):
        return timezone.now() - timedelta(seconds=settings.CHAT_ONLINE_TIMEOUT)

    @classmethod
    def online(cls):
        return cls.objects.filter(last_seen__gte=cls.online_cutoff(), user__is_active=True)

    @classmethod
    def touch(cls, user, status=None):
        presence, _created = cls.objects.get_or_create(user=user)
        presence.last_seen = timezone.now()
        if status in dict(cls.STATUS_CHOICES):
            presence.status = status
        presence.save()
        return presence


class ConversationQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(memberships__user=user)

    def direct_between(self, a, b):
        return (
            self.filter(kind=Conversation.DIRECT, memberships__user=a)
            .filter(memberships__user=b)
            .first()
        )


class Conversation(models.Model):
    DIRECT = "direct"
    GROUP = "group"
    KIND_CHOICES = [(DIRECT, _("Direct conversation")), (GROUP, _("Group conversation"))]

    kind = models.CharField(_("type"), max_length=10, choices=KIND_CHOICES, default=DIRECT)
    name = models.CharField(_("name"), max_length=80, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="owned_conversations",
        verbose_name=_("owner"),
    )
    invite_token = models.UUIDField(_("invite token"), default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="Membership", related_name="conversations"
    )

    objects = ConversationQuerySet.as_manager()

    class Meta:
        verbose_name = _("conversation")
        verbose_name_plural = _("conversations")
        ordering = ["-created_at"]

    def __str__(self):
        if self.is_group:
            return self.name
        return " – ".join(str(u) for u in self.members.all())

    @property
    def is_group(self):
        return self.kind == self.GROUP

    def get_absolute_url(self):
        return reverse("chat:group_link", kwargs={"token": self.invite_token})

    def title_for(self, user):
        if self.is_group:
            return self.name
        other = self.members.exclude(pk=user.pk).first()
        return other.display_name if other else gettext("Conversation")

    def is_owner(self, user):
        return self.is_group and self.owner_id == user.pk

    @property
    def default_room(self):
        return self.rooms.filter(is_default=True).first() or self.rooms.first()

    @classmethod
    def start_direct(cls, a, b):
        conversation = cls.objects.direct_between(a, b)
        if conversation is None:
            conversation = cls.objects.create(kind=cls.DIRECT)
            Membership.objects.create(conversation=conversation, user=a)
            Membership.objects.create(conversation=conversation, user=b)
            Room.objects.create(conversation=conversation, is_default=True)
        return conversation

    @classmethod
    def create_group(cls, owner, name):
        conversation = cls.objects.create(kind=cls.GROUP, name=name, owner=owner)
        Membership.objects.create(conversation=conversation, user=owner, role=Membership.OWNER)
        Room.objects.create(conversation=conversation, is_default=True, created_by=owner)
        return conversation


class Membership(models.Model):
    OWNER = "owner"
    MEMBER = "member"
    ROLE_CHOICES = [(OWNER, _("Owner")), (MEMBER, _("Member"))]

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="memberships", verbose_name=_("conversation")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_memberships",
        verbose_name=_("user"),
    )
    role = models.CharField(_("role"), max_length=10, choices=ROLE_CHOICES, default=MEMBER)
    muted_until = models.DateTimeField(_("muted until"), null=True, blank=True)
    last_read_message_id = models.PositiveBigIntegerField(default=0)
    joined_at = models.DateTimeField(_("joined at"), auto_now_add=True)

    class Meta:
        verbose_name = _("member")
        verbose_name_plural = _("members")
        constraints = [
            models.UniqueConstraint(fields=["conversation", "user"], name="unique_chat_membership")
        ]
        ordering = ["joined_at", "pk"]

    def __str__(self):
        return f"{self.user} @ {self.conversation}"

    @property
    def is_owner(self):
        return self.role == self.OWNER

    @property
    def mute_seconds_left(self):
        if not self.muted_until:
            return 0
        return max(0, math.ceil((self.muted_until - timezone.now()).total_seconds()))

    @property
    def is_muted(self):
        return self.mute_seconds_left > 0

    def mute(self, minutes):
        self.muted_until = timezone.now() + timedelta(minutes=minutes) if minutes else None
        self.save(update_fields=["muted_until"])

    def unread_count(self):
        return (
            Message.objects.filter(room__conversation=self.conversation, pk__gt=self.last_read_message_id)
            .exclude(author=self.user)
            .count()
        )


class Room(models.Model):
    """A channel inside a conversation, shown as a tab of a group chat bubble."""

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="rooms", verbose_name=_("conversation")
    )
    name = models.CharField(_("name"), max_length=40, blank=True)
    is_default = models.BooleanField(_("default room"), default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("room")
        verbose_name_plural = _("rooms")
        ordering = ["-is_default", "created_at", "pk"]

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        return self.name or gettext("General")


def chat_image_path(instance, filename):
    return f"chat/{timezone.now():%Y/%m}/{filename}"


class Message(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="messages", verbose_name=_("room"))
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_messages",
        verbose_name=_("author"),
    )
    text = models.CharField(
        _("text"),
        max_length=settings.CHAT_MESSAGE_MAX_LENGTH,
        blank=True,
        validators=[MaxLengthValidator(settings.CHAT_MESSAGE_MAX_LENGTH)],
    )
    image = models.ImageField(_("image"), upload_to=chat_image_path, blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("message")
        verbose_name_plural = _("messages")
        ordering = ["pk"]

    def __str__(self):
        return self.text[:50] or self.image.name

    def save(self, *args, **kwargs):
        if self.image and not self.image._committed:
            webp = convert_to_webp(self.image.file)
            self.image.save(webp.name, webp, save=False)
        super().save(*args, **kwargs)


class JoinRequest(models.Model):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    STATUS_CHOICES = [(PENDING, _("Pending")), (APPROVED, _("Approved")), (REJECTED, _("Rejected"))]

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="join_requests", verbose_name=_("conversation")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+", verbose_name=_("user")
    )
    status = models.CharField(_("status"), max_length=10, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    decided_at = models.DateTimeField(_("decided at"), null=True, blank=True)

    class Meta:
        verbose_name = _("join request")
        verbose_name_plural = _("join requests")
        constraints = [
            models.UniqueConstraint(fields=["conversation", "user"], name="unique_join_request")
        ]
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user} → {self.conversation} ({self.status})"

    def decide(self, approve):
        self.status = self.APPROVED if approve else self.REJECTED
        self.decided_at = timezone.now()
        self.save(update_fields=["status", "decided_at"])
        if approve:
            Membership.objects.get_or_create(conversation=self.conversation, user=self.user)
