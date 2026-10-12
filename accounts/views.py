from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.generic import ListView

from .forms import EmailAuthenticationForm, ProfileForm, SignUpForm


class EmailLoginView(LoginView):
    form_class = EmailAuthenticationForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


def signup(request):
    if request.user.is_authenticated:
        return redirect(request.user.get_absolute_url())
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, _("Welcome! Your account has been created."))
        return redirect(user.get_absolute_url())
    return render(request, "accounts/signup.html", {"form": form})


@login_required
def edit_profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Your profile has been updated."))
        return redirect(request.user.get_absolute_url())
    return render(request, "accounts/profile_form.html", {"form": form})


class UserListView(ListView):
    template_name = "accounts/user_list.html"
    context_object_name = "profiles"
    paginate_by = 30

    def get_queryset(self):
        return get_user_model().objects.filter(is_active=True).order_by("username")
