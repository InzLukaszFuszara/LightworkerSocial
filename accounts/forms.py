from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label=_("E-mail"),
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )

    error_messages = {
        "invalid_login": _("Invalid e-mail or password."),
        "inactive": _("This account is inactive."),
        "not_activated": _(
            "This account has not been activated yet. Click the link in the e-mail "
            "we sent you or request a new one."
        ),
    }

    def clean(self):
        try:
            return super().clean()
        except forms.ValidationError:
            # Inactive users never authenticate. If the password is right but
            # the address was never confirmed, say so (and only then, so the
            # message does not reveal which addresses are registered).
            user = self._unconfirmed_user()
            if user is not None:
                self.unconfirmed_user = user
                raise forms.ValidationError(
                    self.error_messages["not_activated"], code="not_activated"
                )
            raise

    def _unconfirmed_user(self):
        email = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if not email or not password:
            return None
        user = User.objects.filter(
            email__iexact=email, is_active=False, email_verified=False
        ).first()
        if user is not None and user.check_password(password):
            return user
        return None


class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "username", "first_name", "last_name")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("An account with this e-mail already exists."))
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_active = False  # until the e-mail address is confirmed
        if commit:
            user.save()
        return user


class ResendActivationForm(forms.Form):
    email = forms.EmailField(
        label=_("E-mail"),
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "bio")
        widgets = {"bio": forms.Textarea(attrs={"rows": 4})}
