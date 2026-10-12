from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Category, Comment, Hashtag, Post, PostImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "position")
    list_editable = ("position",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


class PostImageInline(admin.TabularInline):
    model = PostImage
    extra = 0
    fields = ("preview", "image", "position")
    readonly_fields = ("preview",)

    @admin.display(description=_("preview"))
    def preview(self, obj):
        if obj.pk and obj.image:
            return format_html('<img src="{}" style="height:60px">', obj.thumbnail_url)
        return "—"


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("__str__", "author", "category", "created_at")
    list_filter = ("category", "created_at")
    search_fields = ("content", "author__email", "author__username")
    autocomplete_fields = ("author",)
    readonly_fields = ("hashtags", "created_at", "updated_at")
    inlines = [PostImageInline]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.sync_hashtags()


@admin.register(Hashtag)
class HashtagAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("__str__", "author", "post", "created_at")
    search_fields = ("text", "author__username", "author__email")
    raw_id_fields = ("post", "author")
