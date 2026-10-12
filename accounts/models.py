from django.contrib.auth.models import AbstractUser, UserManager
from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

username_validator = RegexValidator(
    r"^[A-Za-z0-9_.-]+$",
    _("Use only letters, digits and the characters . _ -"),
)


class EmailUserManager(UserManager):
    """User manager that uses e-mail as the login identifier."""

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The e-mail address must be set")
        email = self.normalize_email(email).lower()
        extra_fields.setdefault("username", email.split("@")[0])
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra_fields)

    def get_by_natural_key(self, email):
        return self.get(email__iexact=email)


class User(AbstractUser):
    """A user of the portal. Logs in with e-mail + password.

    The ``username`` is only the public handle used in profile URLs.
    """

    username = models.CharField(
        _("username"),
        max_length=40,
        unique=True,
        validators=[username_validator],
        help_text=_("Public name shown in the address of your profile."),
    )
    email = models.EmailField(_("e-mail address"), unique=True)
    bio = models.TextField(_("about me"), max_length=500, blank=True)
    email_verified = models.BooleanField(
        _("e-mail verified"),
        default=False,
        help_text=_("Set when the user confirms the address with the activation link."),
    )
    activation_sent_at = models.DateTimeField(_("activation e-mail sent at"), null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = EmailUserManager()

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["username"]

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    def get_absolute_url(self):
        return reverse("posts:wall", kwargs={"username": self.username})
