"""Custom class related admins"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .forms import CustomUserCreationForm, CustomUserChangeAdminForm
from .models import CustomUser, UserPatientRelation


# Register your models here.
class CustomUserAdmin(UserAdmin):
    """Custom user admin."""

    add_form = CustomUserCreationForm
    form = CustomUserChangeAdminForm
    model = CustomUser

    # List of fields you want to show on the admin screen.
    list_display = [
        "email",
        "is_staff",
        "first_name",
        "last_name",
    ]

    # Change username -> email
    ordering = ["email"]
    search_fields = ["email"]

    # Data field
    # NOTE: username,password,first_name,last_name,email are included by default. Do not put them in the list.
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal info",
            {"fields": ("first_name", "last_name", "gender", "date_of_birth")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )
    # Data field for new record creation
    # NOTE: username,password are included by default. Do not put them in the list.
    #       Ensure to include all that are 'null=False' or 'blank=False'
    # Completely define your own fieldsets
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                    "gender",
                    "date_of_birth",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )


class UserPatientRelationAdmin(admin.ModelAdmin):
    """Admin for user and patient relationships."""

    list_display = ["user", "patient_id", "comment"]


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(UserPatientRelation, UserPatientRelationAdmin)
