from django import forms
from django.core.validators import MinLengthValidator
from django.utils.translation import gettext_lazy as _


class UserSearchForm(forms.Form):
    """Form for user search"""

    keyword = forms.CharField(
        label=_("Keyword"), max_length=100, validators=[MinLengthValidator(3)]
    )
