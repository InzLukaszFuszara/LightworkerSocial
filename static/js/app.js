(function () {
  "use strict";

  var lightbox = document.getElementById("lightbox");
  var body = lightbox && lightbox.querySelector(".lightbox-body");
  var panel = lightbox && lightbox.querySelector(".lightbox-panel");
  var lastFocus = null;

  function openLightbox(templateId) {
    var tpl = document.getElementById(templateId);
    if (!lightbox || !tpl) return false;
    body.innerHTML = "";
    body.appendChild(tpl.content.cloneNode(true));
    lastFocus = document.activeElement;
    lightbox.hidden = false;
    document.body.classList.add("no-scroll");
    panel.focus();
    return true;
  }

  function closeLightbox() {
    if (!lightbox || lightbox.hidden) return;
    lightbox.hidden = true;
    body.innerHTML = "";
    document.body.classList.remove("no-scroll");
    if (lastFocus) lastFocus.focus();
  }

  document.addEventListener("click", function (event) {
    var opener = event.target.closest("[data-lightbox-open]");
    if (opener && !event.ctrlKey && !event.metaKey && !event.shiftKey && event.button === 0) {
      if (openLightbox(opener.getAttribute("data-lightbox-open"))) event.preventDefault();
      return;
    }
    if (event.target.closest("[data-lightbox-close]")) closeLightbox();
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") closeLightbox();
  });

  // Confirmation for destructive forms.
  document.addEventListener("submit", function (event) {
    var msg = event.target.getAttribute("data-confirm");
    if (msg && !window.confirm(msg)) event.preventDefault();
  });

  // Likes of posts and comments without reloading the page. The same post can
  // be shown twice (tile + lightbox), so every button with the same key is updated.
  function updateLikes(key, liked, count) {
    document.querySelectorAll('[data-like="' + key + '"] .like-button').forEach(function (button) {
      button.classList.toggle("liked", liked);
      button.setAttribute("aria-pressed", String(liked));
      button.title = button.getAttribute(liked ? "data-label-unlike" : "data-label-like");
      button.querySelector(".like-count").textContent = count;
    });
  }

  document.addEventListener("submit", function (event) {
    var form = event.target.closest("[data-like]");
    if (!form || event.defaultPrevented || !window.fetch) return;
    event.preventDefault();
    var button = form.querySelector(".like-button");
    button.disabled = true;
    fetch(form.action, {
      method: "POST",
      body: new FormData(form),
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" }
    })
      .then(function (response) {
        if (!response.ok) throw new Error(response.statusText);
        return response.json();
      })
      .then(function (data) { updateLikes(form.getAttribute("data-like"), data.liked, data.count); })
      .catch(function () { form.submit(); })
      .then(function () { button.disabled = false; });
  });

  // Live character counter for the post editor.
  document.querySelectorAll("[data-counter-for]").forEach(function (counter) {
    var field = document.getElementById(counter.getAttribute("data-counter-for"));
    var max = parseInt(counter.getAttribute("data-max"), 10);
    if (!field) return;
    function update() {
      counter.textContent = field.value.length + " / " + max;
      counter.classList.toggle("over", field.value.length > max);
    }
    field.addEventListener("input", update);
    update();
  });
})();
