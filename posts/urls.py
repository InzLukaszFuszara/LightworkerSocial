from django.urls import path

from . import views

app_name = "posts"

urlpatterns = [
    path("", views.home, name="home"),
    path("u/<str:username>/", views.wall, name="wall"),
    path("posts/new/", views.create_post, name="create"),
    path("posts/<int:pk>/", views.post_detail, name="detail"),
    path("posts/<int:pk>/delete/", views.delete_post, name="delete"),
    path("posts/<int:pk>/like/", views.like_post, name="like"),
    path("posts/<int:pk>/comments/", views.add_comment, name="add_comment"),
    path("comments/<int:pk>/like/", views.like_comment, name="like_comment"),
    path("comments/<int:pk>/delete/", views.delete_comment, name="delete_comment"),
    path("forum/", views.forum, name="forum"),
    path("forum/<slug:slug>/", views.forum_topic, name="forum_topic"),
    path("tags/<str:name>/", views.hashtag, name="hashtag"),
]
