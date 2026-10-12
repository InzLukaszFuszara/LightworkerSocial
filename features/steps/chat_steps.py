"""Step definitions for the messenger (chat) features."""

import datetime
import json

from behave import given, then, when
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone, translation
from helpers import make_huge_png, make_image
from PIL import Image

from chat.models import Conversation, Membership, Message, Presence

User = get_user_model()


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _user(username):
    return User.objects.get(username=username)


def act_as(context, username):
    """Log the shared test client in as ``username`` and return it."""
    client = context.test.client
    client.force_login(_user(username))
    return client


def _json(context):
    return json.loads(context.response.content.decode())


def _store(context, response):
    context.response = response
    return response


def _api_post(context, username, url, data=None):
    return _store(context, act_as(context, username).post(url, data or {}))


def _api_get(context, username, url, data=None):
    return _store(context, act_as(context, username).get(url, data or {}))


def _group(name):
    return Conversation.objects.get(kind=Conversation.GROUP, name=name)


def _conversation_url(conversation, suffix=""):
    return reverse("chat:conversation", kwargs={"conversation_id": conversation.pk}) + suffix


def _room(conversation, name):
    """Find a room by the name shown in the (Polish) user interface."""
    with translation.override("pl"):
        return _find_room(conversation, name)


def _find_room(conversation, name):
    for room in conversation.rooms.all():
        if room.display_name == name or room.name == name:
            return room
    raise AssertionError(f"No room {name!r}")


def _messages_url(room):
    return reverse("chat:room_messages", kwargs={"room_id": room.pk})


def _current_room(context):
    return context.chat_conversation.default_room


def _send(context, username, room, text="", image=None):
    data = {"text": text}
    if image is not None:
        data["image"] = image
    response = _api_post(context, username, _messages_url(room), data)
    context.chat_last_status = response.status_code
    return response


def _heartbeat_users(context):
    return {u["username"]: u["status"] for u in _json(context)["users"]}


# --------------------------------------------------------------------------
# Presence & search
# --------------------------------------------------------------------------


@given('"{username:Q}" is online with status "{status:Q}"')
def step_online(context, username, status):
    Presence.touch(_user(username), status)


@given('"{username:Q}" was last online {minutes:d} minutes ago')
def step_was_online(context, username, minutes):
    presence = Presence.touch(_user(username))
    Presence.objects.filter(pk=presence.pk).update(
        last_seen=timezone.now() - datetime.timedelta(minutes=minutes)
    )


@when('"{username:Q}" refreshes the messenger')
def step_refresh(context, username):
    _api_post(context, username, reverse("chat:heartbeat"))
    assert context.response.status_code == 200, context.response.status_code


@when("an anonymous visitor refreshes the messenger")
def step_refresh_anonymous(context):
    _store(context, Client().post(reverse("chat:heartbeat")))


@when('"{username:Q}" sets the status "{status:Q}"')
def step_set_status(context, username, status):
    _api_post(context, username, reverse("chat:heartbeat"), {"status": status})
    assert _json(context)["me"]["status"] == status


@then('the messenger should list "{username:Q}" as "{status:Q}"')
def step_listed_as(context, username, status):
    users = _heartbeat_users(context)
    assert users.get(username) == status, users


@then('the messenger should not list "{username:Q}"')
def step_not_listed(context, username):
    users = _heartbeat_users(context)
    assert username not in users, users


@when('"{username:Q}" searches the messenger for "{query:Q}"')
def step_search(context, username, query):
    _api_get(context, username, reverse("chat:search_users"), {"q": query})


@then('the search results should be "{names:Q}"')
def step_search_results(context, names):
    expected = [n.strip() for n in names.split(",")]
    actual = [u["username"] for u in _json(context)["users"]]
    assert actual == expected, actual


@then('the search result "{username:Q}" should have the status "{status:Q}"')
def step_search_status(context, username, status):
    found = {u["username"]: u["status"] for u in _json(context)["users"]}
    assert found[username] == status, found


# --------------------------------------------------------------------------
# Direct conversations & messages
# --------------------------------------------------------------------------


@given('"{username:Q}" starts a conversation with "{other:Q}"')
@when('"{username:Q}" starts a conversation with "{other:Q}"')
def step_start_direct(context, username, other):
    _api_post(context, username, reverse("chat:start_direct", kwargs={"username": other}))
    if context.response.status_code == 200:
        context.chat_conversation = Conversation.objects.get(
            pk=_json(context)["conversation"]["id"]
        )


@given('"{username:Q}" sends the message "{text:Q}"')
@when('"{username:Q}" sends the message "{text:Q}"')
def step_send(context, username, text):
    _send(context, username, _current_room(context), text)


@when('"{username:Q}" sends a message of {length:d} characters')
def step_send_length(context, username, length):
    _send(context, username, _current_room(context), "x" * length)


@given('"{username:Q}" sends a {fmt} image "{name:Q}"')
@when('"{username:Q}" sends a {fmt} image "{name:Q}"')
def step_send_image(context, username, fmt, name):
    _send(context, username, _current_room(context), image=make_image(name, fmt))


@when('"{username:Q}" sends an image larger than 5 MiB')
def step_send_huge(context, username):
    _send(
        context,
        username,
        _current_room(context),
        image=make_huge_png("huge.png", settings.CHAT_IMAGE_MAX_BYTES),
    )


@then("the message should be rejected")
def step_message_rejected(context):
    assert context.chat_last_status == 400, context.chat_last_status
    assert "error" in _json(context)


@then("the message should be accepted")
def step_message_accepted(context):
    assert context.chat_last_status == 201, context.response.content


def _room_texts(context, username, room):
    _api_get(context, username, _messages_url(room))
    assert context.response.status_code == 200, context.response.status_code
    return [(m["text"], m["author"]["username"]) for m in _json(context)["messages"]]


@then('"{username:Q}" should see the message "{text:Q}" from "{author:Q}"')
def step_sees_message(context, username, text, author):
    conversation = Conversation.objects.direct_between(_user(username), _user(author))
    assert (text, author) in _room_texts(context, username, conversation.default_room)


@when('"{username:Q}" reads the conversation')
def step_read(context, username):
    _api_get(context, username, _messages_url(_current_room(context)))


@then('"{username:Q}" should have {count:d} unread message')
@then('"{username:Q}" should have {count:d} unread messages')
def step_unread(context, username, count):
    membership = Membership.objects.get(conversation=context.chat_conversation, user=_user(username))
    assert membership.unread_count() == count, membership.unread_count()
    response = act_as(context, username).post(reverse("chat:heartbeat"))
    unread = {c["id"]: c["unread"] for c in json.loads(response.content)["conversations"]}
    assert unread[context.chat_conversation.pk] == count, unread


@then('there should be {count:d} conversation between "{a:Q}" and "{b:Q}"')
def step_conversation_count(context, count, a, b):
    actual = (
        Conversation.objects.filter(kind=Conversation.DIRECT, memberships__user=_user(a))
        .filter(memberships__user=_user(b))
        .count()
    )
    assert actual == count, actual


@then("the image of the last message should be stored as WebP")
def step_image_webp(context):
    message = Message.objects.order_by("-pk").first()
    assert message.image.name.endswith(".webp"), message.image.name
    with Image.open(message.image.path) as img:
        assert img.format == "WEBP", img.format


def _download_last_image(context, username):
    message = Message.objects.order_by("-pk").first()
    url = reverse("chat:message_image", kwargs={"message_id": message.pk})
    return act_as(context, username).get(url)


@then('"{username:Q}" should be able to download the image of the last message')
def step_download_image(context, username):
    response = _download_last_image(context, username)
    assert response.status_code == 200, response.status_code
    assert response["Content-Type"] == "image/webp"


@then('"{username:Q}" should not be able to download the image of the last message')
def step_cannot_download(context, username):
    assert _download_last_image(context, username).status_code == 404


@when('"{username:Q}" opens the conversation')
def step_open_conversation(context, username):
    _api_get(context, username, _conversation_url(context.chat_conversation))


# --------------------------------------------------------------------------
# Groups
# --------------------------------------------------------------------------


@given('"{username:Q}" has created the group "{name:Q}"')
def step_create_group(context, username, name):
    _api_post(context, username, reverse("chat:create_group"), {"name": name})
    assert context.response.status_code == 201, context.response.content


@given('"{username:Q}" uses the language "{lang:Q}"')
def step_actor_language(context, username, lang):
    context.test.client.cookies[settings.LANGUAGE_COOKIE_NAME] = lang


@when('"{username:Q}" opens the group "{name:Q}"')
def step_open_group(context, username, name):
    _api_get(context, username, _conversation_url(_group(name)))
    context.chat_viewer = username


@then('"{username:Q}" should be the owner of the group')
def step_is_owner(context, username):
    data = _json(context)["conversation"]
    assert data["is_owner"] is True
    owners = [m["username"] for m in data["members"] if m["role"] == "owner"]
    assert owners == [username], owners


@then('the group should have the rooms "{names:Q}"')
def step_rooms(context, names):
    expected = [n.strip() for n in names.split(",")]
    actual = [r["name"] for r in _json(context)["conversation"]["rooms"]]
    assert actual == expected, actual


@then('the groups "{a:Q}" and "{b:Q}" should have different links')
def step_different_links(context, a, b):
    assert _group(a).get_absolute_url() != _group(b).get_absolute_url()


@then('the link of the group "{name:Q}" should open the group page')
def step_link_opens(context, name):
    group = _group(name)
    response = act_as(context, group.owner.username).get(group.get_absolute_url())
    assert response.status_code == 200
    assert name in response.content.decode()


@when('"{username:Q}" opens the link of the group "{name:Q}"')
def step_open_link(context, username, name):
    _api_get(context, username, _group(name).get_absolute_url())
    assert context.response.status_code == 200, context.response.status_code


@given('"{username:Q}" asks to join the group "{name:Q}"')
@when('"{username:Q}" asks to join the group "{name:Q}"')
def step_ask_join(context, username, name):
    client = act_as(context, username)
    _store(context, client.post(_group(name).get_absolute_url(), follow=True))


def _group_detail(context, username, name):
    response = act_as(context, username).get(_conversation_url(_group(name)))
    return json.loads(response.content)["conversation"]


@then('"{owner:Q}" should see a join request from "{username:Q}"')
def step_sees_request(context, owner, username):
    detail = _group_detail(context, owner, "Lightworkers")
    assert [r["user"]["username"] for r in detail["requests"]] == [username], detail["requests"]


@then('"{owner:Q}" should see no join requests')
def step_no_requests(context, owner):
    assert _group_detail(context, owner, "Lightworkers")["requests"] == []


def _decide(context, owner, username, decision):
    detail = _group_detail(context, owner, "Lightworkers")
    request_id = next(r["id"] for r in detail["requests"] if r["user"]["username"] == username)
    _api_post(
        context,
        owner,
        _conversation_url(_group("Lightworkers"), f"requests/{request_id}/{decision}/"),
    )
    assert context.response.status_code == 200, context.response.content


@when('"{owner:Q}" approves the join request of "{username:Q}"')
def step_approve(context, owner, username):
    _decide(context, owner, username, "approve")


@when('"{owner:Q}" rejects the join request of "{username:Q}"')
def step_reject(context, owner, username):
    _decide(context, owner, username, "reject")


@then('"{username:Q}" should be a member of the group "{name:Q}"')
def step_is_member(context, username, name):
    assert Membership.objects.filter(conversation=_group(name), user=_user(username)).exists()


@then('"{username:Q}" should not be a member of the group "{name:Q}"')
def step_not_member(context, username, name):
    assert not Membership.objects.filter(conversation=_group(name), user=_user(username)).exists()


@given('"{owner:Q}" adds "{username:Q}" to the group "{name:Q}"')
@when('"{owner:Q}" adds "{username:Q}" to the group "{name:Q}"')
def step_add_member(context, owner, username, name):
    _api_post(
        context, owner, _conversation_url(_group(name), "members/"), {"username": username}
    )


@then('the group "{name:Q}" should be in the conversations of "{username:Q}"')
def step_in_conversations(context, name, username):
    response = act_as(context, username).post(reverse("chat:heartbeat"))
    titles = [c["title"] for c in json.loads(response.content)["conversations"]]
    assert name in titles, titles


@given('"{owner:Q}" creates the room "{room:Q}" in the group "{name:Q}"')
@when('"{owner:Q}" creates the room "{room:Q}" in the group "{name:Q}"')
def step_create_room(context, owner, room, name):
    _api_post(context, owner, _conversation_url(_group(name), "rooms/"), {"name": room})


@when('"{username:Q}" writes "{text:Q}" in the room "{room:Q}" of the group "{name:Q}"')
def step_write_room(context, username, text, room, name):
    _send(context, username, _room(_group(name), room), text)


@then('"{username:Q}" should see "{text:Q}" in the room "{room:Q}" of the group "{name:Q}"')
def step_sees_in_room(context, username, text, room, name):
    texts = [t for t, _a in _room_texts(context, username, _room(_group(name), room))]
    assert text in texts, texts


@then('"{username:Q}" should not see "{text:Q}" in the room "{room:Q}" of the group "{name:Q}"')
def step_not_sees_in_room(context, username, text, room, name):
    texts = [t for t, _a in _room_texts(context, username, _room(_group(name), room))]
    assert text not in texts, texts


@when('"{owner:Q}" removes "{username:Q}" from the group "{name:Q}"')
def step_remove(context, owner, username, name):
    _api_post(
        context,
        owner,
        _conversation_url(_group(name), f"members/{_user(username).pk}/remove/"),
    )


@given('"{owner:Q}" mutes "{username:Q}" in the group "{name:Q}" for {minutes:d} minutes')
@when('"{owner:Q}" mutes "{username:Q}" in the group "{name:Q}" for {minutes:d} minutes')
def step_mute(context, owner, username, minutes, name):
    _api_post(
        context,
        owner,
        _conversation_url(_group(name), f"members/{_user(username).pk}/mute/"),
        {"minutes": minutes},
    )


def _about_minutes(seconds, minutes):
    return minutes * 60 - 5 <= seconds <= minutes * 60


@then('"{username:Q}" should see about {minutes:d} minutes until the mute ends')
def step_sees_mute(context, username, minutes):
    seconds = _json(context)["conversation"]["mute_seconds_left"]
    assert _about_minutes(seconds, minutes), seconds


@then("the response should tell about {minutes:d} minutes until the mute ends")
def step_response_mute(context, minutes):
    seconds = _json(context)["mute_seconds_left"]
    assert _about_minutes(seconds, minutes), seconds


@when('the mute of "{username:Q}" in the group "{name:Q}" expires')
def step_mute_expires(context, username, name):
    Membership.objects.filter(conversation=_group(name), user=_user(username)).update(
        muted_until=timezone.now() - datetime.timedelta(seconds=1)
    )


@when('"{username:Q}" leaves the group "{name:Q}"')
def step_leave(context, username, name):
    _api_post(context, username, _conversation_url(_group(name), "leave/"))


# --------------------------------------------------------------------------
# Browser
# --------------------------------------------------------------------------


def _browser_login(context, username):
    client = Client()
    client.force_login(_user(username))
    session = client.cookies[settings.SESSION_COOKIE_NAME].value
    context.page.context.add_cookies(
        [{"name": settings.SESSION_COOKIE_NAME, "value": session, "url": context.base_url}]
    )


@when('"{username:Q}" opens the home page in the browser')
def step_browser_home(context, username):
    _browser_login(context, username)
    context.page.set_viewport_size({"width": 1400, "height": 900})
    context.page.goto(context.base_url + reverse("posts:home"))


@when('"{username:Q}" opens the link of the group "{name:Q}" in the browser')
def step_browser_group(context, username, name):
    _browser_login(context, username)
    context.page.set_viewport_size({"width": 1400, "height": 900})
    context.page.goto(context.base_url + _group(name).get_absolute_url())


@then("the messenger panel should be visible on the right")
def step_panel_visible(context):
    panel = context.page.locator("#chat-panel .chat-panel-inner")
    panel.wait_for(state="visible")
    box = panel.bounding_box()
    width = context.page.viewport_size["width"]
    assert box["x"] + box["width"] >= width - 20, box
    assert box["x"] > width / 2, box


def _panel_list(context, section):
    return context.page.locator(f'#chat-panel [data-list="{section}"]')


@then('the panel section "{section:Q}" should list "{username:Q}"')
def step_panel_lists(context, section, username):
    _panel_list(context, section).locator(f'[data-username="{username}"]').wait_for(timeout=5000)


@then('the panel section "{section:Q}" should not list "{username:Q}"')
def step_panel_not_lists(context, section, username):
    assert _panel_list(context, section).locator(f'[data-username="{username}"]').count() == 0


@when('I type "{text:Q}" into the messenger search')
def step_type_search(context, text):
    context.page.fill("#chat-search", text)


@when('I click "{username:Q}" in the messenger panel')
def step_click_user(context, username):
    _panel_list(context, "available").locator(f'[data-username="{username}"]').click()


def _bubble(context):
    return context.page.locator("#chat-dock .chat-bubble").first


@then('a chat bubble titled "{title:Q}" should be docked at the bottom of the window')
def step_bubble_docked(context, title):
    bubble = _bubble(context)
    bubble.locator(".chat-bubble-title", has_text=title).wait_for(timeout=5000)
    box = bubble.bounding_box()
    height = context.page.viewport_size["height"]
    assert abs(box["y"] + box["height"] - height) <= 2, box


@when('I type "{text:Q}" into the chat bubble and send it')
def step_bubble_send(context, text):
    composer = _bubble(context).locator(".chat-composer")
    composer.locator('[name="text"]').fill(text)
    composer.locator(".chat-send").click()


@then('the chat bubble should show the message "{text:Q}"')
def step_bubble_message(context, text):
    _bubble(context).locator(".chat-message.mine", has_text=text).wait_for(timeout=5000)


@then('the chat bubble should show the room tabs "{names:Q}"')
def step_room_tabs(context, names):
    tabs = _bubble(context).locator(".chat-rooms .chat-room-tab")
    tabs.first.wait_for(timeout=5000)
    expected = [n.strip() for n in names.split(",")]
    assert tabs.all_inner_texts() == expected, tabs.all_inner_texts()
    rooms_box = _bubble(context).locator(".chat-rooms").bounding_box()
    messages_box = _bubble(context).locator(".chat-messages").bounding_box()
    assert rooms_box["y"] < messages_box["y"], "Tabs are not above the messages"


@when('I click the room tab "{name:Q}"')
def step_click_tab(context, name):
    _bubble(context).locator(".chat-room-tab", has_text=name).click()


@then('the room tab "{name:Q}" should be active')
def step_tab_active(context, name):
    _bubble(context).locator(".chat-room-tab.active", has_text=name).wait_for(timeout=3000)


@then("there should be no JavaScript errors")
def step_no_js_errors(context):
    assert not context.console_errors, context.console_errors


@when("I close the chat bubble")
def step_close_bubble(context):
    _bubble(context).locator('[data-action="close"]').click()


@then("no chat bubble should be open")
def step_no_bubble(context):
    context.page.locator("#chat-dock .chat-bubble").first.wait_for(state="detached", timeout=3000)


@when("I open the group settings in the chat bubble")
def step_open_settings(context):
    _bubble(context).locator('[data-action="manage"]').click()


@then('the group settings should show the link of the group "{name:Q}"')
def step_settings_link(context, name):
    field = _bubble(context).locator(".chat-manage .chat-invite-url")
    field.wait_for(state="visible", timeout=3000)
    assert field.input_value().endswith(_group(name).get_absolute_url()), field.input_value()


@then("the chat bubble should show the mute countdown")
def step_mute_countdown(context):
    notice = _bubble(context).locator(".chat-muted-notice")
    notice.wait_for(state="visible", timeout=5000)
    first = notice.inner_text()
    assert "14:5" in first or "15:00" in first, first
    context.page.wait_for_timeout(2500)
    assert notice.inner_text() != first, (first, notice.inner_text(), context.console_errors)


@then("the chat bubble input should be disabled")
def step_input_disabled(context):
    assert _bubble(context).locator('.chat-composer [name="text"]').is_disabled()

