from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.EmailLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("signup/", views.signup, name="signup"),
    path("signup/done/", views.signup_done, name="signup_done"),
    path("activate/<str:token>/", views.activate, name="activate"),
    path("activate-resend/", views.resend_activation, name="resend_activation"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("users/", views.UserListView.as_view(), name="user_list"),
]
