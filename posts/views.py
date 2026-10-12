from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Max
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .forms import CommentForm, PostForm
from .models import Category, Comment, CommentLike, Post, PostLike, toggle_like
from .text import normalise_tag


def _paginate(request, queryset):
    paginator = Paginator(queryset, settings.POSTS_PER_PAGE)
    return paginator.get_page(request.GET.get("page"))


def home(request):
    page = _paginate(request, Post.objects.for_tiles(request.user))
    return render(request, "posts/home.html", {"page_obj": page})


def wall(request, username):
    profile = get_object_or_404(get_user_model(), username=username, is_active=True)
    page = _paginate(request, Post.objects.filter(author=profile).for_tiles(request.user))
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
        Post.objects.for_discussion(request.user).prefetch_related("hashtags"), pk=pk
    )
    return render(request, "posts/post_detail.html", {"post": post, "comment_form": CommentForm()})


def _back(request, fallback):
    """Where to return after a form on a list page (?next=… or the Referer)."""
    target = request.POST.get("next") or request.META.get("HTTP_REFERER", "")
    if url_has_allowed_host_and_scheme(target, {request.get_host()}, request.is_secure()):
        return redirect(target)
    return redirect(fallback)


def _wants_json(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


@login_required
@require_POST
def like_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    liked, count = toggle_like(PostLike, request.user, post=post)
    if _wants_json(request):
        return JsonResponse({"liked": liked, "count": count})
    return _back(request, post.get_absolute_url())


@login_required
@require_POST
def like_comment(request, pk):
    comment = get_object_or_404(Comment.objects.select_related("post"), pk=pk)
    liked, count = toggle_like(CommentLike, request.user, comment=comment)
    if _wants_json(request):
        return JsonResponse({"liked": liked, "count": count})
    return _back(request, comment.get_absolute_url())


@login_required
@require_POST
def add_comment(request, pk):
    post = get_object_or_404(Post, pk=pk)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
        messages.success(request, _("Your comment has been added."))
        target = _back(request, post.get_absolute_url())
        target["Location"] = f"{target['Location'].split('#')[0]}#comment-{comment.pk}"
        return target
    for error in form.errors.get("text", []):
        messages.error(request, error)
    return _back(request, post.get_absolute_url())


@login_required
@require_POST
def delete_comment(request, pk):
    comment = get_object_or_404(Comment.objects.select_related("post"), pk=pk)
    if not comment.can_delete(request.user):
        return HttpResponseForbidden()
    comment.delete()
    messages.success(request, _("The comment has been deleted."))
    return _back(request, comment.post.get_absolute_url())


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
    page = _paginate(
        request, Post.objects.filter(category=category).for_discussion(request.user)
    )
    return render(request, "posts/forum_topic.html", {"category": category, "page_obj": page})


def hashtag(request, name):
    tag = normalise_tag(name)
    page = _paginate(request, Post.objects.filter(hashtags__name=tag).for_tiles(request.user))
    return render(request, "posts/hashtag.html", {"tag": tag, "page_obj": page})
