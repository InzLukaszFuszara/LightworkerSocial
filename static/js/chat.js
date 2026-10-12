/* Lightworker Social – floating messenger (side panel + chat bubbles). */
(function () {
  "use strict";

  var configEl = document.getElementById("chat-config");
  if (!configEl) return;
  var cfg = JSON.parse(configEl.textContent);
  var csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute("content");

  var gettext = window.gettext || function (s) { return s; };
  var fmt = function (s, args) {
    return window.interpolate ? window.interpolate(s, args) : s.replace("%s", args[0]);
  };

  var panel = document.getElementById("chat-panel");
  var dock = document.getElementById("chat-dock");
  var bubbleTemplate = document.getElementById("chat-bubble-template");
  var searchInput = panel.querySelector(".chat-search");
  var statusSelect = panel.querySelector(".chat-status-select");
  var OPEN_KEY = "lws-chat-bubbles";
  var PANEL_KEY = "lws-chat-panel";
  var MAX_BUBBLES = window.matchMedia("(max-width: 700px)").matches ? 1 : 3;

  var state = { me: null, users: [], conversations: [], query: "" };
  var bubbles = new Map();

  // ------------------------------------------------------------------
  // Utilities
  // ------------------------------------------------------------------

  function storageGet(key, fallback) {
    try {
      var raw = window.localStorage.getItem(key);
      return raw === null ? fallback : JSON.parse(raw);
    } catch (e) { return fallback; }
  }

  function storageSet(key, value) {
    try { window.localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* ignore */ }
  }

  function conversationUrl(id, suffix) {
    return cfg.urls.conversation.replace("/0/", "/" + id + "/") + (suffix || "");
  }

  function messagesUrl(roomId) {
    return cfg.urls.messages.replace("/0/", "/" + roomId + "/");
  }

  function api(url, options) {
    options = options || {};
    var init = {
      method: options.method || "GET",
      credentials: "same-origin",
      headers: { "X-CSRFToken": csrfToken, "X-Requested-With": "XMLHttpRequest" }
    };
    if (options.data) {
      if (options.data instanceof FormData) {
        init.body = options.data;
      } else {
        var form = new FormData();
        Object.keys(options.data).forEach(function (k) { form.append(k, options.data[k]); });
        init.body = form;
      }
    }
    return fetch(url, init).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (body) {
        if (!response.ok) {
          var err = new Error(body.error || response.statusText);
          err.status = response.status;
          err.body = body;
          throw err;
        }
        return body;
      });
    });
  }

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (key) {
      if (key === "text") node.textContent = attrs[key];
      else if (key === "className") node.className = attrs[key];
      else node.setAttribute(key, attrs[key]);
    });
    (children || []).forEach(function (child) { if (child) node.appendChild(child); });
    return node;
  }

  function formatDuration(seconds) {
    seconds = Math.max(0, Math.ceil(seconds));
    var h = Math.floor(seconds / 3600);
    var m = Math.floor((seconds % 3600) / 60);
    var s = seconds % 60;
    var pad = function (n) { return n < 10 ? "0" + n : String(n); };
    return (h ? h + ":" + pad(m) : String(m)) + ":" + pad(s);
  }

  function muteLabel(minutes) {
    return minutes >= 60 ? fmt(gettext("%s h"), [minutes / 60]) : fmt(gettext("%s min"), [minutes]);
  }

  function debounce(fn, ms) {
    var timer;
    return function () {
      var args = arguments;
      clearTimeout(timer);
      timer = setTimeout(function () { fn.apply(null, args); }, ms);
    };
  }

  function statusDot(status) {
    return el("span", { className: "chat-dot " + (status || "offline"), "aria-hidden": "true" });
  }

  function statusText(status) {
    if (status === "available") return gettext("Available");
    if (status === "away") return gettext("Be right back");
    return gettext("Offline");
  }

  // ------------------------------------------------------------------
  // Side panel
  // ------------------------------------------------------------------

  function setPanelOpen(open) {
    panel.classList.toggle("collapsed", !open);
    document.body.classList.toggle("chat-panel-open", open);
    panel.querySelector(".chat-panel-toggle").setAttribute("aria-expanded", String(open));
    storageSet(PANEL_KEY, open);
  }

  function userItem(user) {
    var button = el("button", {
      type: "button",
      className: "chat-user",
      "data-username": user.username,
      title: statusText(user.status)
    }, [
      statusDot(user.status),
      el("span", { className: "chat-user-name", text: user.display_name }),
      el("span", { className: "chat-user-nick", text: "@" + user.username })
    ]);
    button.addEventListener("click", function () { openDirect(user.username); });
    return el("li", {}, [button]);
  }

  function matchesQuery(user) {
    if (!state.query) return true;
    return user.username.toLowerCase().indexOf(state.query.toLowerCase()) !== -1;
  }

  function renderUsers() {
    ["available", "away"].forEach(function (status) {
      var list = panel.querySelector('[data-list="' + status + '"]');
      var users = state.users.filter(function (u) { return u.status === status && matchesQuery(u); });
      list.innerHTML = "";
      users.forEach(function (u) { list.appendChild(userItem(u)); });
      if (!users.length) list.appendChild(el("li", { className: "chat-empty", text: gettext("Nobody here") }));
      panel.querySelector('[data-count="' + status + '"]').textContent = users.length;
    });
  }

  function renderConversations() {
    var list = panel.querySelector('[data-list="conversations"]');
    var total = 0;
    list.innerHTML = "";
    state.conversations.forEach(function (c) {
      total += c.unread;
      var badge = c.unread ? el("span", { className: "chat-badge", text: String(c.unread) }) : null;
      var button = el("button", {
        type: "button",
        className: "chat-conversation" + (c.kind === "group" ? " group" : ""),
        "data-conversation": c.id
      }, [
        el("span", { className: "chat-conversation-icon", "aria-hidden": "true", text: c.kind === "group" ? "👥" : "💬" }),
        el("span", { className: "chat-user-name", text: c.title }),
        badge
      ]);
      button.addEventListener("click", function () { openConversation(c.id); });
      list.appendChild(el("li", {}, [button]));
    });
    if (!state.conversations.length) {
      list.appendChild(el("li", { className: "chat-empty", text: gettext("No conversations yet") }));
    }
    var totalBadge = panel.querySelector(".chat-total-unread");
    totalBadge.hidden = !total;
    totalBadge.textContent = String(total);
  }

  function renderMe() {
    if (!state.me) return;
    if (document.activeElement !== statusSelect) statusSelect.value = state.me.status;
    panel.querySelector("[data-status-dot]").className = "chat-dot " + state.me.status;
  }

  function heartbeat(status) {
    return api(cfg.urls.heartbeat, { method: "POST", data: status ? { status: status } : null })
      .then(function (data) {
        state.me = data.me;
        state.users = data.users;
        state.conversations = data.conversations;
        renderMe();
        renderUsers();
        renderConversations();
        autoOpenDirect();
      })
      .catch(function () { /* offline – try again later */ });
  }

  function autoOpenDirect() {
    state.conversations.forEach(function (c) {
      if (c.kind === "direct" && c.unread && !bubbles.has(c.id)) openConversation(c.id);
      var bubble = bubbles.get(c.id);
      if (bubble) bubble.setUnread(bubble.minimized ? c.unread : 0);
    });
  }

  var searchUsers = debounce(function () {
    var resultsSection = panel.querySelector(".chat-search-results");
    var list = resultsSection.querySelector("ul");
    if (!state.query) {
      resultsSection.hidden = true;
      return;
    }
    api(cfg.urls.search + "?q=" + encodeURIComponent(state.query)).then(function (data) {
      list.innerHTML = "";
      data.users.forEach(function (u) { list.appendChild(userItem(u)); });
      if (!data.users.length) list.appendChild(el("li", { className: "chat-empty", text: gettext("No users found") }));
      resultsSection.hidden = false;
    });
  }, 250);

  // ------------------------------------------------------------------
  // Bubbles
  // ------------------------------------------------------------------

  function saveBubbles() {
    var data = [];
    bubbles.forEach(function (b) { data.push({ id: b.id, minimized: b.minimized, room: b.roomId }); });
    storageSet(OPEN_KEY, data);
  }

  function Bubble(id, options) {
    options = options || {};
    this.id = id;
    this.minimized = !!options.minimized;
    this.roomId = options.room || null;
    this.lastId = 0;
    this.detail = null;
    this.muteUntil = 0;
    this.ticks = 0;
    this.node = bubbleTemplate.content.firstElementChild.cloneNode(true);
    this.node.setAttribute("data-conversation", id);
    this.q = this.node.querySelector.bind(this.node);
    this.bind();
    this.applyMinimized();
    dock.insertBefore(this.node, dock.firstChild);
    this.load();
  }

  Bubble.prototype.bind = function () {
    var self = this;
    this.node.addEventListener("click", function (event) {
      var action = event.target.closest("[data-action]");
      if (!action) return;
      var name = action.getAttribute("data-action");
      if (name === "toggle") self.toggle();
      else if (name === "close") self.close();
      else if (name === "manage") self.toggleManage();
      else if (name === "copy-link") self.copyLink();
      else if (name === "leave") self.leave();
    });
    var composer = this.q(".chat-composer");
    var text = composer.querySelector('[name="text"]');
    var file = composer.querySelector('[name="image"]');
    composer.addEventListener("submit", function (event) {
      event.preventDefault();
      self.send();
    });
    text.addEventListener("input", function () { self.updateCounter(); });
    file.addEventListener("change", function () { self.showAttachment(); });
    this.q(".chat-new-room").addEventListener("submit", function (event) {
      event.preventDefault();
      self.createRoom(event.target);
    });
    var memberSearch = this.q(".chat-member-search");
    memberSearch.addEventListener("input", debounce(function () { self.searchMembers(memberSearch.value.trim()); }, 250));
    this.updateCounter();
  };

  Bubble.prototype.load = function () {
    var self = this;
    return api(conversationUrl(this.id)).then(function (data) {
      self.applyDetail(data.conversation);
      return self.fetchMessages(true);
    }).catch(function (err) { self.handleError(err); });
  };

  Bubble.prototype.refreshDetail = function () {
    var self = this;
    return api(conversationUrl(this.id)).then(function (data) {
      self.applyDetail(data.conversation);
    }).catch(function (err) { self.handleError(err); });
  };

  Bubble.prototype.applyDetail = function (detail) {
    this.detail = detail;
    this.node.classList.toggle("group", detail.kind === "group");
    this.q(".chat-bubble-title").textContent = (detail.kind === "group" ? "👥 " : "") + detail.title;
    this.node.setAttribute("aria-label", detail.title);
    this.q('[data-action="manage"]').hidden = detail.kind !== "group";
    var roomIds = detail.rooms.map(function (r) { return r.id; });
    if (roomIds.indexOf(this.roomId) === -1) {
      this.roomId = roomIds[0];
      this.lastId = 0;
      this.q(".chat-messages").innerHTML = "";
    }
    this.renderRooms();
    this.renderManage();
    this.setMute(detail.mute_seconds_left);
    saveBubbles();
  };

  Bubble.prototype.renderRooms = function () {
    var self = this;
    var nav = this.q(".chat-rooms");
    nav.innerHTML = "";
    nav.hidden = this.detail.kind !== "group";
    this.detail.rooms.forEach(function (room) {
      var tab = el("button", {
        type: "button",
        className: "chat-room-tab" + (room.id === self.roomId ? " active" : ""),
        "data-room": room.id,
        "aria-pressed": String(room.id === self.roomId),
        text: room.name
      });
      tab.addEventListener("click", function () { self.switchRoom(room.id); });
      nav.appendChild(tab);
    });
  };

  Bubble.prototype.switchRoom = function (roomId) {
    if (roomId === this.roomId) return;
    this.roomId = roomId;
    this.lastId = 0;
    this.q(".chat-messages").innerHTML = "";
    this.renderRooms();
    saveBubbles();
    this.fetchMessages(true);
  };

  Bubble.prototype.renderManage = function () {
    var self = this;
    var d = this.detail;
    if (d.kind !== "group") return;
    var owner = d.is_owner;
    this.node.querySelectorAll("[data-owner-only]").forEach(function (n) { n.hidden = !owner; });
    this.node.querySelectorAll("[data-member-only]").forEach(function (n) { n.hidden = owner; });
    this.q(".chat-invite-url").value = d.invite_url || "";

    var requests = this.q(".chat-requests");
    requests.innerHTML = "";
    (d.requests || []).forEach(function (r) {
      var approve = el("button", { type: "button", className: "btn btn-small", text: gettext("Approve") });
      var reject = el("button", { type: "button", className: "btn btn-small btn-secondary", text: gettext("Reject") });
      approve.addEventListener("click", function () { self.ownerAction("requests/" + r.id + "/approve/"); });
      reject.addEventListener("click", function () { self.ownerAction("requests/" + r.id + "/reject/"); });
      requests.appendChild(el("li", { className: "chat-request", "data-request": r.id }, [
        el("span", { text: r.user.display_name + " (@" + r.user.username + ")" }), approve, reject
      ]));
    });
    if (owner && !(d.requests || []).length) {
      requests.appendChild(el("li", { className: "chat-empty", text: gettext("No pending requests") }));
    }
    var manageButton = this.q('[data-action="manage"]');
    manageButton.classList.toggle("has-requests", owner && (d.requests || []).length > 0);

    var members = this.q(".chat-members");
    members.innerHTML = "";
    d.members.forEach(function (m) {
      var info = [el("span", { className: "chat-member-name", text: m.display_name + " (@" + m.username + ")" })];
      if (m.role === "owner") info.push(el("span", { className: "chat-tag", text: gettext("Owner") }));
      if (m.mute_seconds_left > 0) {
        info.push(el("span", {
          className: "chat-tag muted",
          "data-countdown-until": String(Date.now() + m.mute_seconds_left * 1000),
          "data-countdown-format": gettext("Muted: %s left"),
          text: fmt(gettext("Muted: %s left"), [formatDuration(m.mute_seconds_left)])
        }));
      }
      var item = el("li", { className: "chat-member", "data-user": m.id }, [el("div", {}, info)]);
      if (owner && m.role !== "owner") {
        var select = el("select", { className: "chat-mute-minutes", "aria-label": gettext("Mute duration") });
        cfg.muteChoices.forEach(function (min) {
          select.appendChild(el("option", { value: String(min), text: muteLabel(min) }));
        });
        var mute = el("button", { type: "button", className: "btn btn-small btn-secondary", "data-member-action": "mute", text: gettext("Mute") });
        mute.addEventListener("click", function () {
          self.ownerAction("members/" + m.id + "/mute/", { minutes: select.value });
        });
        var controls = [select, mute];
        if (m.mute_seconds_left > 0) {
          var unmute = el("button", { type: "button", className: "btn btn-small btn-secondary", "data-member-action": "unmute", text: gettext("Unmute") });
          unmute.addEventListener("click", function () { self.ownerAction("members/" + m.id + "/mute/", { minutes: 0 }); });
          controls.push(unmute);
        }
        var remove = el("button", { type: "button", className: "btn btn-small btn-danger", "data-member-action": "remove", text: gettext("Remove") });
        remove.addEventListener("click", function () {
          if (window.confirm(fmt(gettext("Remove %s from the group?"), [m.display_name]))) {
            self.ownerAction("members/" + m.id + "/remove/");
          }
        });
        controls.push(remove);
        item.appendChild(el("div", { className: "chat-member-controls" }, controls));
      }
      members.appendChild(item);
    });
  };

  Bubble.prototype.ownerAction = function (suffix, data) {
    var self = this;
    return api(conversationUrl(this.id, suffix), { method: "POST", data: data || {} })
      .then(function (body) { if (body.conversation) self.applyDetail(body.conversation); })
      .catch(function (err) { self.showError(err.message); });
  };

  Bubble.prototype.searchMembers = function (query) {
    var self = this;
    var list = this.q(".chat-member-search-results");
    list.innerHTML = "";
    if (!query) return;
    api(cfg.urls.search + "?q=" + encodeURIComponent(query)).then(function (data) {
      var memberIds = self.detail.members.map(function (m) { return m.id; });
      data.users.filter(function (u) { return memberIds.indexOf(u.id) === -1; }).forEach(function (u) {
        var add = el("button", { type: "button", className: "btn btn-small", text: gettext("Add") });
        add.addEventListener("click", function () {
          self.ownerAction("members/", { username: u.username }).then(function () {
            self.q(".chat-member-search").value = "";
            list.innerHTML = "";
          });
        });
        list.appendChild(el("li", { "data-username": u.username }, [
          statusDot(u.status), el("span", { text: u.display_name + " (@" + u.username + ")" }), add
        ]));
      });
      if (!list.children.length) list.appendChild(el("li", { className: "chat-empty", text: gettext("No users found") }));
    });
  };

  Bubble.prototype.createRoom = function (form) {
    var self = this;
    var input = form.querySelector('[name="name"]');
    if (!input.value.trim()) return;
    api(conversationUrl(this.id, "rooms/"), { method: "POST", data: { name: input.value.trim() } })
      .then(function (body) {
        input.value = "";
        return self.refreshDetail().then(function () { self.switchRoom(body.room.id); });
      })
      .catch(function (err) { self.showError(err.message); });
  };

  Bubble.prototype.toggleManage = function () {
    var manage = this.q(".chat-manage");
    manage.hidden = !manage.hidden;
    this.node.classList.toggle("managing", !manage.hidden);
  };

  Bubble.prototype.copyLink = function () {
    var input = this.q(".chat-invite-url");
    var self = this;
    var done = function () { self.showError(gettext("Link copied"), true); };
    if (navigator.clipboard) navigator.clipboard.writeText(input.value).then(done, function () {});
    else { input.select(); document.execCommand("copy"); done(); }
  };

  Bubble.prototype.leave = function () {
    var self = this;
    if (!window.confirm(gettext("Do you want to leave this group?"))) return;
    api(conversationUrl(this.id, "leave/"), { method: "POST" }).then(function () {
      self.close();
      heartbeat();
    }).catch(function (err) { self.showError(err.message); });
  };

  Bubble.prototype.fetchMessages = function (initial) {
    var self = this;
    if (!this.roomId) return Promise.resolve();
    var roomId = this.roomId;
    var url = messagesUrl(roomId) + (this.lastId ? "?after=" + this.lastId : "");
    return api(url).then(function (data) {
      if (roomId !== self.roomId) return;
      data.messages.forEach(function (m) { self.appendMessage(m); });
      self.setMute(data.mute_seconds_left);
      if (initial) self.scrollToBottom(true);
    }).catch(function (err) { self.handleError(err); });
  };

  Bubble.prototype.appendMessage = function (m) {
    if (m.id <= this.lastId) return;
    this.lastId = m.id;
    var list = this.q(".chat-messages");
    var nearBottom = list.scrollHeight - list.scrollTop - list.clientHeight < 60;
    var parts = [];
    if (!m.mine && this.detail && this.detail.kind === "group") {
      parts.push(el("span", { className: "chat-message-author", text: m.author.display_name }));
    }
    if (m.text) parts.push(el("span", { className: "chat-message-text", text: m.text }));
    if (m.image_url) {
      var self = this;
      var img = el("img", { src: m.image_url, alt: gettext("Image") });
      img.addEventListener("load", function () { if (nearBottom || m.mine) self.scrollToBottom(); });
      parts.push(el("a", { href: m.image_url, target: "_blank", rel: "noopener", className: "chat-message-image" }, [img]));
    }
    var time = new Date(m.created_at);
    parts.push(el("time", {
      className: "chat-message-time",
      datetime: m.created_at,
      text: time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    }));
    list.appendChild(el("li", {
      className: "chat-message " + (m.mine ? "mine" : "theirs"),
      "data-message": m.id
    }, parts));
    if (nearBottom || m.mine) this.scrollToBottom();
  };

  Bubble.prototype.scrollToBottom = function () {
    var list = this.q(".chat-messages");
    list.scrollTop = list.scrollHeight;
  };

  Bubble.prototype.setMute = function (seconds) {
    var until = seconds > 0 ? Date.now() + seconds * 1000 : 0;
    // The server rounds up to whole seconds; only re-sync on a real change
    // so that the countdown ticks smoothly.
    if (!until || !this.muteUntil || Math.abs(until - this.muteUntil) > 2000) this.muteUntil = until;
    this.updateMute();
  };

  Bubble.prototype.updateMute = function () {
    var left = this.muteUntil ? (this.muteUntil - Date.now()) / 1000 : 0;
    var muted = left > 0;
    var notice = this.q(".chat-muted-notice");
    notice.hidden = !muted;
    if (muted) notice.textContent = fmt(gettext("You are muted. You can write again in %s."), [formatDuration(left)]);
    this.q(".chat-composer").querySelectorAll("input, button").forEach(function (n) { n.disabled = muted; });
    this.node.classList.toggle("muted", muted);
    if (!muted) this.muteUntil = 0;
  };

  Bubble.prototype.updateCounter = function () {
    var text = this.q('.chat-composer [name="text"]');
    this.q(".chat-counter").textContent = text.value.length + " / " + cfg.maxLength;
  };

  Bubble.prototype.showAttachment = function () {
    var file = this.q('.chat-composer [name="image"]').files[0];
    var preview = this.q(".chat-attachment-preview");
    preview.innerHTML = "";
    preview.hidden = !file;
    if (!file) return;
    if (file.size > cfg.maxImageBytes) {
      this.showError(gettext("The image is larger than 5 MiB."));
      this.clearAttachment();
      return;
    }
    var self = this;
    var remove = el("button", { type: "button", className: "chat-icon", title: gettext("Remove"), text: "×" });
    remove.addEventListener("click", function () { self.clearAttachment(); });
    preview.appendChild(el("span", { text: "📎 " + file.name }));
    preview.appendChild(remove);
  };

  Bubble.prototype.clearAttachment = function () {
    this.q('.chat-composer [name="image"]').value = "";
    this.q(".chat-attachment-preview").hidden = true;
    this.q(".chat-attachment-preview").innerHTML = "";
  };

  Bubble.prototype.send = function () {
    var self = this;
    var form = this.q(".chat-composer");
    var text = form.querySelector('[name="text"]');
    var file = form.querySelector('[name="image"]');
    if (!text.value.trim() && !file.files.length) return;
    if (text.value.length > cfg.maxLength) {
      this.showError(fmt(gettext("A message can have at most %s characters."), [cfg.maxLength]));
      return;
    }
    var data = new FormData();
    data.append("text", text.value.trim());
    if (file.files.length) data.append("image", file.files[0]);
    form.classList.add("sending");
    api(messagesUrl(this.roomId), { method: "POST", data: data })
      .then(function (body) {
        text.value = "";
        self.clearAttachment();
        self.updateCounter();
        self.appendMessage(body.message);
        self.hideError();
      })
      .catch(function (err) {
        if (err.body && err.body.mute_seconds_left) self.setMute(err.body.mute_seconds_left);
        self.showError(err.message);
      })
      .then(function () { form.classList.remove("sending"); text.focus(); });
  };

  Bubble.prototype.showError = function (message, info) {
    var box = this.q(".chat-error");
    box.textContent = message;
    box.classList.toggle("info", !!info);
    box.hidden = false;
    clearTimeout(this.errorTimer);
    var self = this;
    this.errorTimer = setTimeout(function () { self.hideError(); }, 5000);
  };

  Bubble.prototype.hideError = function () { this.q(".chat-error").hidden = true; };

  Bubble.prototype.handleError = function (err) {
    if (err.status === 404 || err.status === 403) {
      this.gone = true;
      this.node.classList.add("gone");
      this.q(".chat-muted-notice").hidden = true;
      this.q(".chat-composer").querySelectorAll("input, button").forEach(function (n) { n.disabled = true; });
      var box = this.q(".chat-error");
      box.textContent = gettext("You are no longer a member of this conversation.");
      box.hidden = false;
    }
  };

  Bubble.prototype.setUnread = function (count) {
    var badge = this.q(".chat-bubble-unread");
    badge.hidden = !count;
    badge.textContent = String(count);
  };

  Bubble.prototype.applyMinimized = function () {
    this.node.classList.toggle("minimized", this.minimized);
  };

  Bubble.prototype.toggle = function () {
    this.minimized = !this.minimized;
    this.applyMinimized();
    if (!this.minimized) {
      this.setUnread(0);
      this.fetchMessages(false);
      this.scrollToBottom();
    }
    saveBubbles();
  };

  Bubble.prototype.restore = function () {
    if (this.minimized) this.toggle();
    var input = this.q('.chat-composer [name="text"]');
    if (!input.disabled) input.focus();
  };

  Bubble.prototype.close = function () {
    this.node.remove();
    bubbles.delete(this.id);
    saveBubbles();
  };

  Bubble.prototype.tick = function () {
    if (this.gone) return;
    this.ticks += 1;
    if (!this.minimized && this.ticks % cfg.pollSeconds === 0) this.fetchMessages(false);
    if (this.ticks % (cfg.pollSeconds * 5) === 0) this.refreshDetail();
    if (this.muteUntil) this.updateMute();
  };

  function openConversation(id, options) {
    id = Number(id);
    var existing = bubbles.get(id);
    if (existing) {
      existing.restore();
      dock.insertBefore(existing.node, dock.firstChild);
      return existing;
    }
    while (bubbles.size >= MAX_BUBBLES) {
      var oldest = dock.lastElementChild;
      var oldId = Number(oldest.getAttribute("data-conversation"));
      bubbles.get(oldId).close();
    }
    var bubble = new Bubble(id, options);
    bubbles.set(id, bubble);
    saveBubbles();
    return bubble;
  }

  function openDirect(username) {
    return api(cfg.urls.direct.replace("__USERNAME__", encodeURIComponent(username)), { method: "POST" })
      .then(function (data) {
        openConversation(data.conversation.id).restore();
        heartbeat();
      });
  }

  // ------------------------------------------------------------------
  // Wiring
  // ------------------------------------------------------------------

  panel.querySelector(".chat-panel-toggle").addEventListener("click", function () {
    setPanelOpen(panel.classList.contains("collapsed"));
  });
  setPanelOpen(storageGet(PANEL_KEY, window.innerWidth > 1100));

  statusSelect.addEventListener("change", function () { heartbeat(statusSelect.value); });

  searchInput.addEventListener("input", function () {
    state.query = searchInput.value.trim();
    renderUsers();
    searchUsers();
  });

  panel.querySelector(".chat-new-group").addEventListener("submit", function (event) {
    event.preventDefault();
    var input = event.target.querySelector('[name="name"]');
    var name = input.value.trim();
    if (!name) return;
    api(cfg.urls.createGroup, { method: "POST", data: { name: name } }).then(function (data) {
      input.value = "";
      var bubble = openConversation(data.conversation.id);
      bubble.restore();
      heartbeat();
    });
  });

  document.addEventListener("click", function (event) {
    var opener = event.target.closest("[data-chat-open]");
    if (opener) {
      event.preventDefault();
      openConversation(opener.getAttribute("data-chat-open")).restore();
      return;
    }
    var direct = event.target.closest("[data-chat-direct]");
    if (direct) {
      event.preventDefault();
      openDirect(direct.getAttribute("data-chat-direct"));
    }
  });

  storageGet(OPEN_KEY, []).slice(0, MAX_BUBBLES).reverse().forEach(function (b) {
    openConversation(b.id, { minimized: b.minimized, room: b.room });
  });

  var autoOpen = document.querySelector("[data-chat-autoopen]");
  if (autoOpen) openConversation(autoOpen.getAttribute("data-chat-open")).restore();

  // One clock drives polling and the mute countdowns.
  setInterval(function () {
    bubbles.forEach(function (b) { b.tick(); });
    document.querySelectorAll("[data-countdown-until]").forEach(function (node) {
      var left = (Number(node.getAttribute("data-countdown-until")) - Date.now()) / 1000;
      if (left <= 0) node.remove();
      else node.textContent = fmt(node.getAttribute("data-countdown-format"), [formatDuration(left)]);
    });
  }, 1000);

  heartbeat();
  setInterval(function () { heartbeat(); }, cfg.heartbeatSeconds * 1000);
})();
