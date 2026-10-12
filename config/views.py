from django.db import connection
from django.http import HttpResponse
from django.views.decorators.cache import never_cache


@never_cache
def healthz(request):
    """Healthcheck for Railway: the app is up and the database answers."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:  # noqa: BLE001 – any failure means "not healthy"
        return HttpResponse("database unavailable", status=503, content_type="text/plain")
    return HttpResponse("ok", content_type="text/plain")
