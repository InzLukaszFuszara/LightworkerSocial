from django.conf import settings
from django.core.validators import MaxLengthValidator
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from . import text
from .images import convert_to_webp, make_thumbnail, validate_image_upload


class Category(models.Model):
    """A category defined by administrators; shown as a forum topic."""

    name = models.CharField(_("name"), max_length=100, unique=True)
    slug = models.SlugField(_("slug"), max_length=100, unique=True)
    description = models.TextField(_("description"), blank=True)
    position = models.PositiveIntegerField(_("position"), default=0)

    class Meta:
        verbose_name = _("category")
        verbose_name_plural = _("categories")
        ordering = ["position", "name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("posts:forum_topic", kwargs={"slug": self.slug})


class Hashtag(models.Model):
    name = models.CharField(_("name"), max_length=50, unique=True)

    class Meta:
        verbose_name = _("hashtag")
        verbose_name_plural = _("hashtags")
        ordering = ["name"]

    def __str__(self):
        return f"#{self.name}"

    def get_absolute_url(self):
        return reverse("posts:hashtag", kwargs={"name": self.name})


def _liked_by(model, user, field):
    """``Exists`` expression: has ``user`` liked the outer object?"""
    if user is None or not user.is_authenticated:
        return models.Value(False, output_field=models.BooleanField())
    return models.Exists(model.objects.filter(user=user, **{field: models.OuterRef("pk")}))


class PostQuerySet(models.QuerySet):
    def with_stats(self, user=None):
        """Annotate like/comment counts and whether ``user`` likes each post."""
        return self.annotate(
            like_count=models.Count("likes", distinct=True),
            comment_count=models.Count("comments", distinct=True),
            liked=_liked_by(PostLike, user, "post"),
        )

    def for_tiles(self, user=None):
        return (
            self.with_stats(user)
            .select_related("author", "category")
            .prefetch_related("images")
            .order_by("-created_at", "-pk")
        )

    def for_discussion(self, user=None):
        """Posts with their comments (oldest first), as shown on the forum."""
        comments = Comment.objects.with_stats(user).select_related("author").order_by("created_at", "pk")
        return self.for_tiles(user).prefetch_related(models.Prefetch("comments", queryset=comments))


class Post(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
        verbose_name=_("author"),
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="posts",
        verbose_name=_("category"),
    )
    content = models.TextField(
        _("content"),
        validators=[MaxLengthValidator(settings.POST_MAX_LENGTH)],
        help_text=_("Markdown is supported. Use #hashtags to tag your post."),
    )
    hashtags = models.ManyToManyField(
        Hashtag, related_name="posts", blank=True, verbose_name=_("hashtags")
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    objects = PostQuerySet.as_manager()

    class Meta:
        verbose_name = _("post")
        verbose_name_plural = _("posts")
        ordering = ["-created_at", "-pk"]

    def __str__(self):
        return text.excerpt(self.content, 60)

    def get_absolute_url(self):
        return reverse("posts:detail", kwargs={"pk": self.pk})

    def sync_hashtags(self):
        names = text.extract_hashtags(self.content)
        tags = [Hashtag.objects.get_or_create(name=name)[0] for name in names]
        self.hashtags.set(tags)

    @property
    def excerpt(self):
        return text.excerpt(self.content, settings.POST_EXCERPT_LENGTH)

    @property
    def rendered_content(self):
        return text.render_markdown(self.content)

    @cached_property
    def first_image(self):
        images = list(self.images.all())
        return images[0] if images else None


def post_image_path(instance, filename):
    return f"posts/{instance.post.created_at:%Y/%m}/{filename}"


def post_thumbnail_path(instance, filename):
    return f"posts/{instance.post.created_at:%Y/%m}/thumbs/{filename}"


class PostImage(models.Model):
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="images", verbose_name=_("post")
    )
    image = models.ImageField(
        _("image"), upload_to=post_image_path, validators=[validate_image_upload]
    )
    thumbnail = models.ImageField(_("thumbnail"), upload_to=post_thumbnail_path, blank=True)
    position = models.PositiveIntegerField(_("position"), default=0)

    class Meta:
        verbose_name = _("image")
        verbose_name_plural = _("images")
        ordering = ["position", "pk"]

    def __str__(self):
        return self.image.name

    @property
    def thumbnail_url(self):
        return (self.thumbnail or self.image).url

    def save(self, *args, **kwargs):
        # Freshly uploaded files (from the post form or the admin) are
        # re-encoded to WebP and get a thumbnail before being stored.
        if self.image and not self.image._committed:
            webp = convert_to_webp(self.image.file)
            self.image.save(webp.name, webp, save=False)
            thumb = make_thumbnail(self.image.file)
            self.thumbnail.save(thumb.name, thumb, save=False)
        super().save(*args, **kwargs)


@receiver(post_delete, sender=PostImage)
def delete_image_files(sender, instance, **kwargs):
    for field in (instance.image, instance.thumbnail):
        if field:
            field.storage.delete(field.name)


class PostLike(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes", verbose_name=_("post"))
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="post_likes", verbose_name=_("user")
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("post like")
        verbose_name_plural = _("post likes")
        constraints = [models.UniqueConstraint(fields=["post", "user"], name="unique_post_like")]

    def __str__(self):
        return f"{self.user} ♥ {self.post_id}"


class CommentQuerySet(models.QuerySet):
    def with_stats(self, user=None):
        return self.annotate(
            like_count=models.Count("likes", distinct=True),
            liked=_liked_by(CommentLike, user, "comment"),
        )


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments", verbose_name=_("post"))
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments", verbose_name=_("author")
    )
    text = models.TextField(
        _("comment"), validators=[MaxLengthValidator(settings.COMMENT_MAX_LENGTH)]
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)

    objects = CommentQuerySet.as_manager()

    class Meta:
        verbose_name = _("comment")
        verbose_name_plural = _("comments")
        ordering = ["created_at", "pk"]

    def __str__(self):
        return self.text[:60]

    def get_absolute_url(self):
        return f"{self.post.get_absolute_url()}#comment-{self.pk}"

    def can_delete(self, user):
        return user.is_authenticated and user.pk in (self.author_id, self.post.author_id)


class CommentLike(models.Model):
    comment = models.ForeignKey(
        Comment, on_delete=models.CASCADE, related_name="likes", verbose_name=_("comment")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comment_likes", verbose_name=_("user")
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("comment like")
        verbose_name_plural = _("comment likes")
        constraints = [models.UniqueConstraint(fields=["comment", "user"], name="unique_comment_like")]

    def __str__(self):
        return f"{self.user} ♥ comment {self.comment_id}"


def toggle_like(model, user, **target):
    """Like or unlike; returns ``(liked, like_count)``."""
    deleted, _rows = model.objects.filter(user=user, **target).delete()
    liked = not deleted
    if liked:
        model.objects.get_or_create(user=user, **target)
    return liked, model.objects.filter(**target).count()
