"""Forms"""

from datetime import datetime
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, UserPatientRelation, GENDER_CHOICES


class CustomUserCreationForm(UserCreationForm):
    """Form for creating a new user.

    Required for creating users via admin or custom signup.
    """

    gender = forms.ChoiceField(
        choices=GENDER_CHOICES, widget=forms.RadioSelect, required=True
    )

    class Meta:
        model = CustomUser
        fields = [
            "first_name",
            "last_name",
            "gender",
            "date_of_birth",
            "email",
            "password1",
            "password2",
        ]

    def clean_email(self):
        """Ensure email is unique."""
        email = self.cleaned_data["email"]
        if CustomUser.objects.filter(email=email).exists():
            self.add_error("email", "This email is already in use.")
        return email


class CustomUserChangeAdminForm(UserChangeForm):
    """Form for modifying user info in Django admin."""

    class Meta(UserChangeForm.Meta):
        model = CustomUser
        fields = "__all__"


class CustomUserChangeForm(UserChangeForm):
    """Form for modifying user profile information.

    Args:
        user (CustomUser): Determines available fields.
            If user is not a superuser, 'is_staff' field is removed.
    """

    class Meta(UserChangeForm.Meta):
        model = CustomUser
        fields = [
            "first_name",
            "last_name",
            "gender",
            "date_of_birth",
            "email",
            "is_active",
            "is_staff",
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Remove 'is_staff' field for non-superusers
        if self.user and not self.user.is_superuser:
            self.fields.pop("is_staff", None)

         # If we have an instance with a DOB, format it for the date‑input
        dob = getattr(self.instance, 'date_of_birth', None)
        if dob:
            # Ensure it's a date or datetime
            if isinstance(dob, datetime):
                dob = dob.date()
            self.initial['date_of_birth'] = dob.strftime('%Y-%m-%d')


class RelationEditForm(forms.ModelForm):
    """Form for editing user-patient relationship."""

    comment = forms.CharField(
        label=_("Comment"),
        widget=forms.Textarea(attrs={"rows": "5"}),
        max_length=UserPatientRelation._meta.get_field("comment").max_length,
        required=False,
    )

    class Meta:
        model = UserPatientRelation
        fields = ["color", "comment"]
