from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET
from django.views.generic import ListView

from . import activation
from .forms import EmailAuthenticationForm, ProfileForm, ResendActivationForm, SignUpForm

SIGNUP_EMAIL_SESSION_KEY = "accounts_signup"


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
        sent = activation.send_activation_email(request, user)
        if not sent:
            messages.error(
                request,
                _("We could not send the activation e-mail. Please try again in a moment."),
            )
        request.session[SIGNUP_EMAIL_SESSION_KEY] = {"email": user.email, "sent": sent}
        return redirect("accounts:signup_done")
    return render(request, "accounts/signup.html", {"form": form})


def signup_done(request):
    signup_info = request.session.get(SIGNUP_EMAIL_SESSION_KEY)
    if not signup_info:
        return redirect("accounts:signup")
    return render(
        request,
        "accounts/signup_done.html",
        {**signup_info, "days": settings.ACCOUNT_ACTIVATION_DAYS},
    )


@require_GET
def activate(request, token):
    try:
        user = activation.user_from_token(token)
    except activation.ActivationError as exc:
        return render(
            request,
            "accounts/activation_failed.html",
            {"reason": exc.reason, "form": ResendActivationForm()},
            status=400,
        )
    if user.email_verified:
        messages.info(request, _("Your account is already active. You can log in."))
        return redirect("accounts:login")
    activation.activate(user)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    request.session.pop(SIGNUP_EMAIL_SESSION_KEY, None)
    messages.success(request, _("Your e-mail address has been confirmed. Welcome!"))
    return redirect(user.get_absolute_url())


def resend_activation(request):
    form = ResendActivationForm(
        request.POST or None, initial={"email": request.GET.get("email", "")}
    )
    if request.method == "POST" and form.is_valid():
        user = (
            get_user_model()
            .objects.filter(
                email__iexact=form.cleaned_data["email"], is_active=False, email_verified=False
            )
            .first()
        )
        if user is not None and activation.can_resend(user):
            activation.send_activation_email(request, user)
        # Same answer whether or not the address exists (no account enumeration).
        messages.success(
            request,
            _(
                "If an account with this address is waiting for activation, "
                "we have sent a new activation link."
            ),
        )
        return redirect(reverse("accounts:login"))
    return render(request, "accounts/resend_activation.html", {"form": form})


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
