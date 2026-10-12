from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Max
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .forms import PostForm
from .models import Category, Post
from .text import normalise_tag


def _paginate(request, queryset):
    paginator = Paginator(queryset, settings.POSTS_PER_PAGE)
    return paginator.get_page(request.GET.get("page"))


def home(request):
    page = _paginate(request, Post.objects.for_tiles())
    return render(request, "posts/home.html", {"page_obj": page})


def wall(request, username):
    profile = get_object_or_404(get_user_model(), username=username, is_active=True)
    page = _paginate(request, Post.objects.filter(author=profile).for_tiles())
    return render(
        request,
        "posts/wall.html",
        {"profile": profile, "page_obj": page, "is_owner": request.user == profile},
    )


@login_required
def create_post(request):
    form = PostForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save_for(request.user)
        messages.success(request, _("Your post has been added to your wall."))
        return redirect(request.user.get_absolute_url())
    return render(
        request,
        "posts/post_form.html",
        {"form": form, "has_categories": Category.objects.exists()},
    )


def post_detail(request, pk):
    post = get_object_or_404(
        Post.objects.select_related("author", "category").prefetch_related("images", "hashtags"),
        pk=pk,
    )
    return render(request, "posts/post_detail.html", {"post": post})


@login_required
@require_POST
def delete_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author_id != request.user.pk:
        return HttpResponseForbidden()
    post.delete()
    messages.success(request, _("The post has been deleted."))
    return redirect(request.user.get_absolute_url())


def forum(request):
    categories = Category.objects.annotate(
        post_count=Count("posts"), last_post_at=Max("posts__created_at")
    )
    return render(request, "posts/forum.html", {"categories": categories})


def forum_topic(request, slug):
    category = get_object_or_404(Category, slug=slug)
    page = _paginate(request, Post.objects.filter(category=category).for_tiles())
    return render(request, "posts/forum_topic.html", {"category": category, "page_obj": page})


def hashtag(request, name):
    tag = normalise_tag(name)
    page = _paginate(request, Post.objects.filter(hashtags__name=tag).for_tiles())
    return render(request, "posts/hashtag.html", {"tag": tag, "page_obj": page})
