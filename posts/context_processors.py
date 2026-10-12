from django.conf import settings


def limits(request):
    return {"comment_max_length": settings.COMMENT_MAX_LENGTH}
