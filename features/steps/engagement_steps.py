"""Steps for likes and comments."""

import json

from behave import given, then, when
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from helpers import soup, tile

from posts.models import Category, Comment, Post, PostLike

User = get_user_model()


def _client(context):
    return context.test.client


def _latest_post():
    return Post.objects.order_by("-pk").first()


def _post(content):
    return Post.objects.get(content=content)


def _comment(text):
    return Comment.objects.get(text=text)


def _as(context, username):
    client = _client(context)
    client.force_login(User.objects.get(username=username))
    return client


# --------------------------------------------------------------------------
# Likes
# --------------------------------------------------------------------------


@given('"{username:Q}" likes the latest post')
def step_user_likes(context, username):
    PostLike.objects.create(post=_latest_post(), user=User.objects.get(username=username))


@when("I like the latest post")
def step_like(context):
    context.response = _client(context).post(
        reverse("posts:like", kwargs={"pk": _latest_post().pk}), {"next": "/"}
    )


@when('"{username:Q}" likes the latest post through the API')
def step_like_api(context, username):
    context.response = _as(context, username).post(
        reverse("posts:like", kwargs={"pk": _latest_post().pk}),
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert context.response.status_code == 200, context.response.status_code


@then("the API should answer that the post is liked with {count:d} like")
def step_api_answer(context, count):
    data = json.loads(context.response.content)
    assert data == {"liked": True, "count": count}, data


@when("an anonymous visitor likes the latest post")
def step_anonymous_like(context):
    context.response = Client().post(reverse("posts:like", kwargs={"pk": _latest_post().pk}))
    assert context.response.status_code == 302


@then("the latest post should have {count:d} like")
@then("the latest post should have {count:d} likes")
def step_post_likes(context, count):
    actual = _latest_post().likes.count()
    assert actual == count, actual


@then("tile {number:d} should show {count:d} like")
@then("tile {number:d} should show {count:d} likes")
def step_tile_likes(context, number, count):
    button = tile(context.response, number).select_one(".post-stats .like-button")
    assert button is not None, "No like button under the tile"
    shown = button.select_one(".like-count").get_text(strip=True)
    assert shown == str(count), shown


@then("tile {number:d} should show {count:d} comment")
@then("tile {number:d} should show {count:d} comments")
def step_tile_comments(context, number, count):
    counter = tile(context.response, number).select_one(".post-stats .comment-count")
    assert counter is not None, "No comment counter under the tile"
    assert str(count) in counter.get_text(), counter.get_text()


@then("the like button of tile {number:d} should be pressed")
def step_tile_pressed(context, number):
    button = tile(context.response, number).select_one(".post-stats .like-button")
    assert "liked" in button["class"] and button["aria-pressed"] == "true", button


@then("the like button of tile {number:d} should link to the login page")
def step_tile_login(context, number):
    button = tile(context.response, number).select_one(".post-stats .like-button")
    assert button.name == "a", button.name
    assert button["href"].startswith(reverse("accounts:login")), button["href"]


@when('I like the comment "{text:Q}"')
def step_like_comment(context, text):
    context.response = _client(context).post(
        reverse("posts:like_comment", kwargs={"pk": _comment(text).pk}), {"next": "/"}
    )


@then('the comment "{text:Q}" should have {count:d} like')
@then('the comment "{text:Q}" should have {count:d} likes')
def step_comment_likes(context, text, count):
    actual = _comment(text).likes.count()
    assert actual == count, actual


@then('the comment "{text:Q}" should show {count:d} like')
@then('the comment "{text:Q}" should show {count:d} likes')
def step_comment_shows_likes(context, text, count):
    item = soup(context.response).select_one(f'[data-comment="{_comment(text).pk}"]')
    assert item is not None, "Comment not shown"
    shown = item.select_one(".like-count").get_text(strip=True)
    assert shown == str(count), shown


# --------------------------------------------------------------------------
# Comments
# --------------------------------------------------------------------------


@given('"{username:Q}" has commented "{text:Q}" on the latest post')
def step_has_commented(context, username, text):
    Comment.objects.create(
        post=_latest_post(), author=User.objects.get(username=username), text=text
    )


@given('"{username:Q}" has commented "{text:Q}" on the post "{content:Q}"')
def step_has_commented_on(context, username, text, content):
    Comment.objects.create(
        post=_post(content), author=User.objects.get(username=username), text=text
    )


def _comment_on_latest(context, text, client=None, next_url=None):
    data = {"text": text}
    if next_url:
        data["next"] = next_url
    client = client or _client(context)
    context.response = client.post(
        reverse("posts:add_comment", kwargs={"pk": _latest_post().pk}), data
    )


@when('I comment "{text:Q}" on the latest post')
def step_comment(context, text):
    _comment_on_latest(context, text)


@when("I comment with {length:d} characters on the latest post")
def step_comment_length(context, length):
    _comment_on_latest(context, "x" * length)


@when('I comment "{text:Q}" on the latest post from the forum topic "{name:Q}"')
def step_comment_from_forum(context, text, name):
    context.forum_url = Category.objects.get(name=name).get_absolute_url()
    _comment_on_latest(context, text, next_url=context.forum_url)


@when('an anonymous visitor comments "{text:Q}" on the latest post')
def step_anonymous_comment(context, text):
    _comment_on_latest(context, text, client=Client())


@when('I delete the comment "{text:Q}"')
def step_delete_comment(context, text):
    context.response = _client(context).post(
        reverse("posts:delete_comment", kwargs={"pk": _comment(text).pk}), {"next": "/"}
    )


@then("the latest post should have {count:d} comment")
@then("the latest post should have {count:d} comments")
def step_comment_count(context, count):
    actual = _latest_post().comments.count()
    assert actual == count, actual


@then('the latest post should have the comments "{texts:Q}"')
def step_comment_texts(context, texts):
    expected = [t.strip() for t in texts.split(",")]
    actual = list(_latest_post().comments.values_list("text", flat=True))
    assert actual == expected, actual


@then('I should be redirected to the comment "{text:Q}"')
def step_redirect_comment(context, text):
    assert context.response.status_code == 302, context.response.status_code
    location = context.response["Location"]
    assert location.endswith(f"#comment-{_comment(text).pk}"), location


@then('I should be redirected to the forum topic "{name:Q}"')
def step_redirect_forum(context, name):
    assert context.response.status_code == 302, context.response.status_code
    location = context.response["Location"]
    assert location.startswith(Category.objects.get(name=name).get_absolute_url()), location


# --------------------------------------------------------------------------
# Forum layout
# --------------------------------------------------------------------------


def _forum_posts(context):
    return soup(context.response).select(".forum-posts > .forum-post")


@then("I should see {count:d} forum post")
@then("I should see {count:d} forum posts")
def step_forum_post_count(context, count):
    actual = len(_forum_posts(context))
    assert actual == count, actual


def _forum_post(context, number):
    posts = _forum_posts(context)
    assert len(posts) >= number, len(posts)
    return posts[number - 1]


@then('forum post {number:d} should contain "{text:Q}"')
def step_forum_post_contains(context, number, text):
    content = _forum_post(context, number).select_one(".post-content").get_text()
    assert text in content, content


@then('forum post {number:d} should list the comments "{texts:Q}"')
def step_forum_post_comments(context, number, texts):
    expected = [t.strip() for t in texts.split(",")]
    actual = [
        c.get_text(strip=True)
        for c in _forum_post(context, number).select(".comment-list .comment-text")
    ]
    assert actual == expected, actual


@then("every forum post should take a whole row")
def step_forum_rows(context):
    assert soup(context.response).select_one("div.forum-posts"), "No forum post list"
    assert not soup(context.response).select(".tiles"), "The forum still shows tiles"
    css = (settings.BASE_DIR / "static" / "css" / "app.css").read_text()
    assert ".forum-posts { display: flex; flex-direction: column;" in css


@then("every forum post should have a comment form")
def step_forum_forms(context):
    for post in _forum_posts(context):
        assert post.select_one("form.comment-form textarea[name=text]"), post


# --------------------------------------------------------------------------
# Browser
# --------------------------------------------------------------------------


@when('"{username:Q}" opens the wall of "{owner:Q}" in the browser')
def step_browser_wall_as(context, username, owner):
    client = Client()
    client.force_login(User.objects.get(username=username))
    session = client.cookies[settings.SESSION_COOKIE_NAME].value
    context.page.context.add_cookies(
        [{"name": settings.SESSION_COOKIE_NAME, "value": session, "url": context.base_url}]
    )
    context.page.goto(context.base_url + reverse("posts:wall", kwargs={"username": owner}))
    context.page.evaluate("window.__notReloaded = true")


def _browser_like_button(context, number):
    return context.page.locator(".tiles > .tile").nth(number - 1).locator(".post-stats .like-button")


@when("I click the like button of tile {number:d} in the browser")
def step_browser_like(context, number):
    _browser_like_button(context, number).click()


@then("the like button of tile {number:d} in the browser should show {count:d} and be pressed")
def step_browser_like_state(context, number, count):
    button = _browser_like_button(context, number)
    context.page.wait_for_function(
        "el => el.classList.contains('liked')", arg=button.element_handle(), timeout=3000
    )
    assert button.locator(".like-count").inner_text() == str(count)
    assert button.get_attribute("aria-pressed") == "true"


@then("the page should not have been reloaded")
def step_not_reloaded(context):
    assert context.page.evaluate("window.__notReloaded === true"), "The page was reloaded"
