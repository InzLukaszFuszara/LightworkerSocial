from django.contrib.auth.signals import user_logged_out
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Message, Presence


@receiver(user_logged_out)
def go_offline(sender, request, user, **kwargs):
    if user is not None:
        Presence.objects.filter(user=user).delete()


@receiver(post_delete, sender=Message)
def delete_message_image(sender, instance, **kwargs):
    if instance.image:
        instance.image.storage.delete(instance.image.name)
