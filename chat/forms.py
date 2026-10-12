from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from posts.images import validate_image_upload

from .models import Presence


class MessageForm(forms.Form):
    text = forms.CharField(
        label=_("Message"), max_length=settings.CHAT_MESSAGE_MAX_LENGTH, required=False
    )
    image = forms.FileField(label=_("Image"), required=False)

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image:
            validate_image_upload(image, settings.CHAT_IMAGE_MAX_BYTES)
        return image

    def clean(self):
        data = super().clean()
        if not data.get("text") and not data.get("image") and not self.errors:
            raise ValidationError(_("Write a message or attach an image."))
        return data


class GroupForm(forms.Form):
    name = forms.CharField(label=_("Group name"), max_length=80)


class RoomForm(forms.Form):
    name = forms.CharField(label=_("Room name"), max_length=40)


class MuteForm(forms.Form):
    minutes = forms.IntegerField(
        label=_("Minutes"), min_value=0, max_value=settings.CHAT_MAX_MUTE_MINUTES
    )


class StatusForm(forms.Form):
    status = forms.ChoiceField(choices=Presence.STATUS_CHOICES, required=False)


class UsernameForm(forms.Form):
    username = forms.CharField(max_length=40)
