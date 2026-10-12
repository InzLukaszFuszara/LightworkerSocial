"""Create demo users, categories and posts: python manage.py seed_demo"""

import io
import random

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw

from chat.models import Conversation, Membership, Message, Presence, Room
from posts.models import Category, Comment, CommentLike, Post, PostImage, PostLike

CATEGORIES = [
    ("Medytacja", "medytacja"),
    ("Uzdrawianie", "uzdrawianie"),
    ("Natura", "natura"),
]

TEXTS = [
    "Poranna **medytacja** nad jeziorem. Cisza, światło i oddech. #medytacja #spokój",
    "Kilka myśli o *wdzięczności*:\n\n- za ludzi\n- za naturę\n- za ten dzień\n\n#wdzięczność",
    "Spacer po lesie przywraca równowagę. Polecam każdemu! #natura #spokój",
    "Morning **light** and a cup of tea. #light #gratitude",
    "> Bądź światłem, którego szukasz.\n\nCytat dnia. #inspiracja #light",
]


def _picture(seed):
    rnd = random.Random(seed)
    img = Image.new("RGB", (800, 600), (225, 242, 253))
    draw = ImageDraw.Draw(img)
    for _ in range(12):
        x, y, r = rnd.randint(0, 800), rnd.randint(0, 600), rnd.randint(30, 160)
        colour = rnd.choice([(184, 225, 250), (182, 232, 192), (127, 209, 143), (110, 193, 239)])
        draw.ellipse((x - r, y - r, x + r, y + r), fill=colour)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return SimpleUploadedFile(f"demo{seed}.jpg", buf.getvalue(), content_type="image/jpeg")


class Command(BaseCommand):
    help = "Creates demo data (users with password 'demo-pass-123')."

    def handle(self, *args, **options):
        User = get_user_model()
        cats = []
        for name, slug in CATEGORIES:
            cat, _ = Category.objects.get_or_create(
                slug=slug, defaults={"name": name}
            )
            cats.append(cat)
        users = []
        for username in ("anna", "bartek", "celina"):
            user, created = User.objects.get_or_create(
                email=f"{username}@example.com", defaults={"username": username}
            )
            if created:
                user.set_password("demo-pass-123")
                user.email_verified = True
                user.bio = f"Cześć, jestem {username.capitalize()}!"
                user.save()
            users.append(user)
        for i in range(9):
            post = Post.objects.create(
                author=users[i % 3], category=cats[(i // 3 + i) % 3], content=TEXTS[i % len(TEXTS)]
            )
            post.sync_hashtags()
            if i % 2 == 0:
                PostImage.objects.create(post=post, image=_picture(i), position=0)
        self._seed_engagement(users)
        self._seed_chat(users)
        self.stdout.write(self.style.SUCCESS("Demo data created."))

    def _seed_engagement(self, users):
        replies = ["Piękne słowa 🙏", "Dziękuję, potrzebowałam tego dziś.", "Też tak mam!"]
        for i, post in enumerate(Post.objects.order_by("pk")):
            for j, user in enumerate(users):
                if (i + j) % 2 == 0 and user != post.author:
                    PostLike.objects.get_or_create(post=post, user=user)
            if i % 3 != 2:
                commenter = users[(i + 1) % 3]
                comment = Comment.objects.create(post=post, author=commenter, text=replies[i % 3])
                CommentLike.objects.get_or_create(comment=comment, user=post.author)

    def _seed_chat(self, users):
        anna, bartek, celina = users
        direct = Conversation.start_direct(anna, bartek)
        Message.objects.create(room=direct.default_room, author=bartek, text="Cześć Anna! Jak medytacja?")
        Message.objects.create(room=direct.default_room, author=anna, text="Świetnie, dziękuję 🙂")
        group = Conversation.create_group(anna, "Krąg światła")
        Membership.objects.get_or_create(conversation=group, user=bartek)
        Membership.objects.get_or_create(conversation=group, user=celina)
        Room.objects.create(conversation=group, name="Medytacje", created_by=anna)
        Room.objects.create(conversation=group, name="Wydarzenia", created_by=anna)
        Message.objects.create(room=group.default_room, author=celina, text="Witajcie w kręgu!")
        Presence.touch(bartek, Presence.AVAILABLE)
        Presence.touch(celina, Presence.AWAY)
