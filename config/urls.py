from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.i18n import JavaScriptCatalog
from django.views.static import serve

from .views import healthz

urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
    path("chat/", include("chat.urls")),
    path("accounts/", include("accounts.urls")),
    path("", include("posts.urls")),
]

if settings.DEBUG or settings.SERVE_MEDIA:
    # Uploaded post images (chat images are served by chat.views with a
    # membership check and never through this URL).
    media_prefix = settings.MEDIA_URL.strip("/")
    urlpatterns += [
        re_path(
            rf"^{media_prefix}/(?P<path>(?!chat/).*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        )
    ]
