"""Custom user and related classes"""

import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _

# Const
GENDER_CHOICES = (
    ("F", _("Female")),
    ("M", _("Male")),
    ("O", _("Other")),
)

COLOR_CHOICES = (
    ("light", _("white")),
    ("primary", _("blue")),
    ("secondary", _("gray")),
    ("success", _("green")),
    ("info", _("purple")),
    ("warning", _("yellow")),
    ("danger", _("red")),
    ("dark", _("black")),
)


# Classes
class CustomUserManager(BaseUserManager):
    """Custom manager for CustomUser without username field."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("The Email field must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    """Main user class."""

    # *** PRIMARY KEY ***
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, verbose_name=_("user ID")
    )

    # *** Username field ***
    # NOTE: This part is deprecating username and making email as login id.
    email = models.EmailField(
        verbose_name=_("email address"),
        unique=True,
        blank=False,
        null=False,
    )
    # Remove username field (Django requires `username` by default)
    username = None
    # Use email as login id
    USERNAME_FIELD = "email"  # Use email as the primary login field

    # *** Other fields ***
    gender = models.CharField(
        max_length=1,
        verbose_name=_("gender"),
        choices=GENDER_CHOICES,
        blank=False,
        null=False,
    )
    date_of_birth = models.DateField(
        verbose_name=_("date of birth"), blank=False, null=False
    )
    # *** AUTOMATICALLY UPDATED FIELDS ***
    last_update = models.DateTimeField(
        verbose_name=_("last updated"),
        auto_now=True,
    )

    # *** REQUIRED FIELDS FOR 'createsuperuser' ***
    # NOTE: Do not include USERNAME_FIELD here
    REQUIRED_FIELDS = [
        "first_name",
        "last_name",
        "gender",
        "date_of_birth",
    ]

    objects = CustomUserManager()

    def __str__(self):
        return self.email


class UserPatientRelation(models.Model):
    """User-patient relationships"""

    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, verbose_name=_("user")
    )
    # NOTE: Django doesn’t currently provide any support for foreign key or many-to-many relationships spanning multiple databases.
    # Do NOT use ForeignKey.
    patient_id = models.CharField(max_length=200, verbose_name=_("patient"))
    color = models.CharField(
        verbose_name=_("color"),
        choices=COLOR_CHOICES,
        blank=False,
        null=False,
        default="primary",
    )
    comment = models.CharField(max_length=300, blank=True, verbose_name=_("comment"))
    is_active = models.BooleanField(default=True, null=False, verbose_name=_("active"))

    def __str__(self) -> str:
        return f"{self.user}-{self.patient_id}"

    class Meta:
        unique_together = ["user", "patient_id"]
