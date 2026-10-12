from django.urls import path

from . import views

app_name = "posts"

urlpatterns = [
    path("", views.home, name="home"),
    path("u/<str:username>/", views.wall, name="wall"),
    path("posts/new/", views.create_post, name="create"),
    path("posts/<int:pk>/", views.post_detail, name="detail"),
    path("posts/<int:pk>/delete/", views.delete_post, name="delete"),
    path("forum/", views.forum, name="forum"),
    path("forum/<slug:slug>/", views.forum_topic, name="forum_topic"),
    path("tags/<str:name>/", views.hashtag, name="hashtag"),
]
