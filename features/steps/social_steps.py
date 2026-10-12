import datetime

from behave import given, then, when
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from helpers import make_animated_gif, make_huge_png, make_image, soup, tile, tiles
from PIL import Image

from posts.models import Category, Post, PostImage

User = get_user_model()


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def client(context):
    return context.test.client


def get(context, url, **kwargs):
    context.response = client(context).get(url, follow=True, **kwargs)
    return context.response


def post(context, url, data=None, **kwargs):
    context.response = client(context).post(url, data or {}, **kwargs)
    return context.response


def user_by_ref(ref):
    if "@" in ref:
        return User.objects.get(email=ref)
    return User.objects.get(username=ref)


def category(name):
    return Category.objects.get(name=name)


def latest_post():
    return Post.objects.order_by("-pk").first()


def body(context):
    return context.response.content.decode()


def make_post(author, content, cat, images=0, created_at=None):
    p = Post.objects.create(author=user_by_ref(author), category=category(cat), content=content)
    p.sync_hashtags()
    for i in range(images):
        colour = (110, 193, 239) if i == 0 else (127, 209, 143)
        PostImage.objects.create(
            post=p, image=make_image(f"img{i}.png", "PNG", color=colour), position=i
        )
    if created_at:
        Post.objects.filter(pk=p.pk).update(created_at=created_at)
    return p


# --------------------------------------------------------------------------
# Users & authentication
# --------------------------------------------------------------------------


@given('a user "{username:Q}" with e-mail "{email:Q}" and password "{password:Q}"')
def step_user(context, username, email, password):
    context.users[username] = User.objects.create_user(
        email=email, username=username, password=password
    )


@given('an administrator "{email:Q}" with password "{password:Q}"')
def step_admin(context, email, password):
    User.objects.create_superuser(email=email, username=email.split("@")[0], password=password)


@given('I am logged in as "{ref:Q}"')
def step_logged_in(context, ref):
    client(context).force_login(user_by_ref(ref))


@given('I use the language "{lang:Q}"')
@when('I switch the language to "{lang:Q}"')
def step_language(context, lang):
    post(context, reverse("set_language"), {"language": lang, "next": "/"})
    assert context.response.status_code == 302


@when('I sign up with e-mail "{email:Q}", username "{username:Q}" and password "{password:Q}"')
def step_signup(context, email, username, password):
    post(
        context,
        reverse("accounts:signup"),
        {"email": email, "username": username, "password1": password, "password2": password},
    )


@when('I log in with e-mail "{email:Q}" and password "{password:Q}"')
def step_login(context, email, password):
    post(context, reverse("accounts:login"), {"username": email, "password": password})


@when("I log out")
def step_logout(context):
    post(context, reverse("accounts:logout"))


@then('I should be logged in as "{email:Q}"')
def step_check_logged_in(context, email):
    response = client(context).get(reverse("posts:home"))
    user = response.wsgi_request.user
    assert user.is_authenticated, "User is not logged in"
    assert user.email == email, f"Logged in as {user.email}"


@then("I should not be logged in")
def step_check_not_logged_in(context):
    response = client(context).get(reverse("posts:home"))
    assert not response.wsgi_request.user.is_authenticated


@then('I should be redirected to the wall of "{username:Q}"')
def step_redirect_wall(context, username):
    assert context.response.status_code == 302, context.response.status_code
    expected = reverse("posts:wall", kwargs={"username": username})
    assert context.response["Location"] == expected, context.response["Location"]


@then("I should be redirected to the login page")
def step_redirect_login(context):
    login_url = reverse("accounts:login")
    if context.response.status_code == 302:
        assert context.response["Location"].startswith(login_url), context.response["Location"]
        context.response = client(context).get(context.response["Location"])
        return
    assert context.response.redirect_chain, "No redirect happened"
    assert context.response.redirect_chain[-1][0].startswith(login_url)


# --------------------------------------------------------------------------
# Categories & posts
# --------------------------------------------------------------------------


@given('a category "{name:Q}" exists')
def step_category(context, name):
    context.categories[name] = Category.objects.create(
        name=name, slug=name.lower().replace(" ", "-")
    )


@given('"{author:Q}" has posted "{content:Q}" in category "{cat:Q}"')
def step_has_posted(context, author, content, cat):
    make_post(author, content, cat)


@given('"{author:Q}" has posted "{content:Q}" in category "{cat:Q}" {days:d} days ago')
@given('"{author:Q}" has posted "{content:Q}" in category "{cat:Q}" {days:d} day ago')
def step_has_posted_ago(context, author, content, cat, days):
    make_post(author, content, cat, created_at=timezone.now() - datetime.timedelta(days=days))


@given('"{author:Q}" has posted "{content:Q}" with {count:d} images in category "{cat:Q}"')
def step_has_posted_images(context, author, content, count, cat):
    make_post(author, content, cat, images=count)


@given('"{author:Q}" has posted a text of {length:d} characters in category "{cat:Q}"')
def step_has_posted_long(context, author, length, cat):
    alphabet = "abcdefghij"
    context.long_text = "".join(alphabet[i % 10] for i in range(length))
    make_post(author, context.long_text, cat)


@given('I attach a {fmt} image "{name:Q}"')
def step_attach_image(context, fmt, name):
    context.upload_files.append(make_image(name, fmt))


@given('I attach an animated GIF image "{name:Q}"')
def step_attach_animated(context, name):
    context.upload_files.append(make_animated_gif(name))


@given('I attach a {fmt} image "{name:Q}" larger than 5 MiB')
def step_attach_huge(context, fmt, name):
    huge = make_huge_png(name, settings.POST_IMAGE_MAX_BYTES)
    assert huge.size > 5 * 1024 * 1024
    context.upload_files.append(huge)


@given('I attach a text file "{name:Q}"')
def step_attach_text(context, name):
    context.upload_files.append(SimpleUploadedFile(name, b"not an image", "image/jpeg"))


@when("I open the new post page")
def step_open_new_post(context):
    get(context, reverse("posts:create"))


def _publish(context, content, cat_name):
    context.post_count_before = Post.objects.count()
    data = {"content": content, "images": context.upload_files}
    if cat_name:
        data["category"] = category(cat_name).pk
    post(context, reverse("posts:create"), data)


@when('I publish a post "{content:Q}" in category "{cat:Q}"')
def step_publish(context, content, cat):
    _publish(context, content, cat)


@when('I publish a post of {length:d} characters in category "{cat:Q}"')
def step_publish_length(context, length, cat):
    _publish(context, "x" * length, cat)


@when('I publish a post "{content:Q}" without a category')
def step_publish_no_category(context, content):
    _publish(context, content, None)


@when("I delete the latest post")
def step_delete_latest(context):
    post(context, reverse("posts:delete", kwargs={"pk": latest_post().pk}))


@when("I open the latest post")
def step_open_latest(context):
    get(context, latest_post().get_absolute_url())


@then("the post should be rejected")
def step_rejected(context):
    assert context.response.status_code == 200, context.response.status_code
    assert Post.objects.count() == context.post_count_before, "A post was created"
    assert soup(context.response).select(".errorlist"), "No validation errors shown"


@then('the latest post should be in category "{cat:Q}"')
def step_latest_category(context, cat):
    assert latest_post().category.name == cat


@then("the latest post should have {count:d} image")
@then("the latest post should have {count:d} images")
def step_latest_images(context, count):
    actual = latest_post().images.count()
    assert actual == count, f"{actual} images"


@then("every image of the latest post should be stored as WebP")
def step_all_webp(context):
    for img in latest_post().images.all():
        assert img.image.name.endswith(".webp"), img.image.name
        with Image.open(img.image.path) as im:
            assert im.format == "WEBP", im.format


@then("the first image of the latest post should have a WebP thumbnail")
def step_thumb_webp(context):
    first = latest_post().first_image
    assert first.thumbnail.name.endswith(".webp")
    with Image.open(first.thumbnail.path) as im:
        assert im.format == "WEBP"
        assert im.size == settings.THUMBNAIL_SIZE, im.size


@then("the first image of the latest post should be an animated WebP")
def step_animated(context):
    with Image.open(latest_post().first_image.image.path) as im:
        assert im.format == "WEBP"
        assert getattr(im, "n_frames", 1) > 1, "Animation was lost"


@then('the latest post should have the hashtags "{names:Q}"')
def step_hashtags(context, names):
    expected = sorted(n.strip() for n in names.split(","))
    actual = sorted(latest_post().hashtags.values_list("name", flat=True))
    assert actual == expected, actual


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------


@when('I visit the wall of "{username:Q}"')
def step_visit_wall(context, username):
    get(context, reverse("posts:wall", kwargs={"username": username}))


@when("I visit the profile list")
def step_visit_profiles(context):
    get(context, reverse("accounts:user_list"))


@when("I visit the forum")
def step_visit_forum(context):
    get(context, reverse("posts:forum"))


@when('I visit the forum topic "{name:Q}"')
def step_visit_topic(context, name):
    get(context, category(name).get_absolute_url())


@when('I visit the hashtag page "{name:Q}"')
def step_visit_hashtag(context, name):
    get(context, reverse("posts:hashtag", kwargs={"name": name}))


@when('I add the category "{name:Q}" with slug "{slug:Q}" in the admin panel')
def step_admin_add_category(context, name, slug):
    post(
        context,
        reverse("admin:posts_category_add"),
        {"name": name, "slug": slug, "position": 0, "description": ""},
    )
    assert context.response.status_code == 302, body(context)


@then('the page should contain "{text:Q}"')
def step_contains(context, text):
    assert text in body(context), f"{text!r} not found in page"


@then("the page should contain the markup {markup}")
def step_contains_markup(context, markup):
    assert markup in body(context), f"{markup!r} not found in page"


@then('the page should not contain "{text:Q}"')
def step_not_contains(context, text):
    assert text not in body(context), f"{text!r} found in page"


@then("the response status should be {status:d}")
def step_status(context, status):
    assert context.response.status_code == status, context.response.status_code


@then("the page should contain a link to the new post page")
def step_link_new_post(context):
    assert soup(context.response).select(f'a[href="{reverse("posts:create")}"]')


@then('the page should link to the wall of "{username:Q}"')
def step_link_wall(context, username):
    href = reverse("posts:wall", kwargs={"username": username})
    assert soup(context.response).select(f'a[href="{href}"]'), f"No link to {href}"


@then('the page should link to the hashtag "{name:Q}"')
def step_link_hashtag(context, name):
    href = reverse("posts:hashtag", kwargs={"name": name})
    links = [a for a in soup(context.response).select("a.hashtag") if a["href"] == href]
    assert links, f"No hashtag link to {href}"
    href_found = client(context).get(href)
    assert href_found.status_code == 200


# --------------------------------------------------------------------------
# Tiles
# --------------------------------------------------------------------------


@then("I should see {count:d} tile")
@then("I should see {count:d} tiles")
def step_tile_count(context, count):
    actual = len(tiles(context.response))
    assert actual == count, f"{actual} tiles"


@then('the wall of "{username:Q}" should show {count:d} tile')
@then('the wall of "{username:Q}" should show {count:d} tiles')
def step_wall_tile_count(context, username, count):
    response = client(context).get(reverse("posts:wall", kwargs={"username": username}))
    actual = len(tiles(response))
    assert actual == count, f"{actual} tiles"


@then("the tiles should be laid out 3 per row")
def step_three_per_row(context):
    assert soup(context.response).select("div.tiles"), "No tile grid"
    css = (settings.BASE_DIR / "static" / "css" / "app.css").read_text()
    assert ".tiles { display: grid; grid-template-columns: repeat(3," in css


def _excerpt(context, number):
    return tile(context.response, number).select_one(".tile-excerpt").get_text()


@then('tile {number:d} should contain "{text:Q}"')
def step_tile_contains(context, number, text):
    assert text in _excerpt(context, number), _excerpt(context, number)


@then('tile {number:d} should show the excerpt "{text:Q}"')
def step_tile_excerpt(context, number, text):
    assert _excerpt(context, number) == text, _excerpt(context, number)


@then("tile {number:d} should show an excerpt of {length:d} characters")
def step_tile_excerpt_length(context, number, length):
    text = _excerpt(context, number)
    assert text.endswith("…"), text
    assert text[:-1] == context.long_text[:length], text
    assert len(text[:-1]) == length


@then("the lightbox content of tile {number:d} should contain the full text")
def step_lightbox_full(context, number):
    template = tile(context.response, number).select_one("template")
    assert context.long_text in template.get_text()


@then('the lightbox content of tile {number:d} should contain "{text:Q}"')
def step_lightbox_contains(context, number, text):
    template = tile(context.response, number).select_one("template")
    assert text in template.decode_contents(), template.decode_contents()


@then("tile {number:d} should be a lightbox trigger")
def step_lightbox_trigger(context, number):
    t = tile(context.response, number)
    opener = t.select_one("[data-lightbox-open]")
    assert opener is not None
    assert t.select_one(f'template#{opener["data-lightbox-open"]}') is not None


@then("tile {number:d} should show the thumbnail of the first image")
def step_tile_thumb(context, number):
    img = tile(context.response, number).select_one("img.tile-thumb")
    assert img is not None, "No thumbnail"
    first = latest_post().first_image
    assert img["src"] == first.thumbnail.url, img["src"]


@then('tile {number:d} should link to the forum topic "{name:Q}"')
def step_tile_category(context, number, name):
    link = tile(context.response, number).select_one(".tile-footer a.category-link")
    assert link["href"] == category(name).get_absolute_url()
    assert link.get_text(strip=True) == name


# --------------------------------------------------------------------------
# Forum
# --------------------------------------------------------------------------


def _topic_rows(context):
    return soup(context.response).select("tr.forum-topic")


@then('I should see the forum topic "{name:Q}"')
def step_see_topic(context, name):
    titles = [r.select_one("a.topic-title").get_text(strip=True) for r in _topic_rows(context)]
    assert name in titles, titles


@then('the forum topic "{name:Q}" should have {count:d} posts')
def step_topic_count(context, name, count):
    for row in _topic_rows(context):
        if row.select_one("a.topic-title").get_text(strip=True) == name:
            assert row.select_one("td.num").get_text(strip=True) == str(count)
            return
    raise AssertionError(f"Topic {name} not found")


# --------------------------------------------------------------------------
# Browser (Playwright) steps
# --------------------------------------------------------------------------


@when('I open the wall of "{username:Q}" in the browser')
def step_browser_wall(context, username):
    context.wall_url = context.base_url + reverse("posts:wall", kwargs={"username": username})
    context.page.goto(context.wall_url)


@when("I click tile {number:d} in the browser")
def step_browser_click(context, number):
    context.page.locator(".tile .tile-open").nth(number - 1).click()


@when("I press Escape in the browser")
def step_browser_escape(context):
    context.page.keyboard.press("Escape")


@then("the lightbox should be visible")
def step_lightbox_visible(context):
    context.page.wait_for_selector("#lightbox", state="visible", timeout=3000)
    assert context.page.url == context.wall_url, "The tile navigated away instead"


@then('the lightbox should contain "{text:Q}"')
def step_lightbox_text(context, text):
    assert text in context.page.inner_text("#lightbox .lightbox-body")


@then("the lightbox should be hidden")
def step_lightbox_hidden(context):
    context.page.wait_for_selector("#lightbox", state="hidden", timeout=3000)
