from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from .images import ACCEPT_ATTR, validate_image_upload
from .models import Category, Comment, Post, PostImage


class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.FileField):
    widget = MultipleImageInput

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("required", False)
        super().__init__(*args, **kwargs)
        self.widget.attrs.update({"accept": ACCEPT_ATTR, "multiple": True})

    def clean(self, data, initial=None):
        files = data if isinstance(data, (list, tuple)) else ([data] if data else [])
        cleaned, errors = [], []
        for f in files:
            try:
                f = super().clean(f, initial)
                validate_image_upload(f)
                cleaned.append(f)
            except ValidationError as exc:
                errors.extend(exc.error_list)
        if errors:
            raise ValidationError(errors)
        return cleaned


class PostForm(forms.ModelForm):
    content = forms.CharField(
        label=_("Content"),
        max_length=settings.POST_MAX_LENGTH,
        widget=forms.Textarea(
            attrs={"rows": 10, "maxlength": settings.POST_MAX_LENGTH, "data-counter": "true"}
        ),
        help_text=_("Markdown is supported. Use #hashtags to tag your post."),
    )
    category = forms.ModelChoiceField(
        label=_("Category"),
        queryset=Category.objects.all(),
        empty_label=_("— choose a category —"),
    )
    images = MultipleImageField(
        label=_("Images"),
        help_text=_("JPG, PNG, GIF or WebP, max. 5 MiB each. Images are converted to WebP."),
    )

    class Meta:
        model = Post
        fields = ("category", "content")

    def clean_images(self):
        images = self.cleaned_data.get("images") or []
        limit = settings.POST_MAX_IMAGES
        if len(images) > limit:
            raise ValidationError(
                ngettext(
                    "You can attach at most %(limit)d image.",
                    "You can attach at most %(limit)d images.",
                    limit,
                )
                % {"limit": limit}
            )
        return images

    @transaction.atomic
    def save_for(self, author):
        post = self.save(commit=False)
        post.author = author
        post.save()
        post.sync_hashtags()
        for position, uploaded in enumerate(self.cleaned_data.get("images") or []):
            PostImage.objects.create(post=post, image=uploaded, position=position)
        return post


class CommentForm(forms.ModelForm):
    text = forms.CharField(
        label=_("Comment"),
        max_length=settings.COMMENT_MAX_LENGTH,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "maxlength": settings.COMMENT_MAX_LENGTH,
                "placeholder": _("Write a comment…"),
            }
        ),
    )

    class Meta:
        model = Comment
        fields = ("text",)
