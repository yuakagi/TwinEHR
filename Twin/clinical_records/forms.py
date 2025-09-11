from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from accounts.models import UserPatientRelation


class PatientSearchForm(forms.Form):
    """Search patients by demographic or clinical information."""

    # Patient info
    patient_id = forms.CharField(label=_("Patient ID"), required=False, max_length=100)
    first_name = forms.CharField(label=_("First name"), required=False, max_length=100)
    last_name = forms.CharField(label=_("Last name"), required=False, max_length=100)
    sex = forms.ChoiceField(
        label=_("Sex"),
        choices=[("F", _("female")), ("M", _("male"))],
        required=False,
        widget=forms.RadioSelect,
    )
    min_age = forms.IntegerField(
        label=_("Minimum age"), required=False, min_value=0, max_value=120
    )

    max_age = forms.IntegerField(
        label=_("Maximum age"), required=False, min_value=0, max_value=120
    )

    # Date range
    search_start = forms.DateField(label=_("Search period start"), required=False)
    search_end = forms.DateField(label=_("Period end"), required=False)

    # Clinical codes (Select2 via AJAX)
    dx_code = forms.CharField(
        label=_("Diagnosis code"),
        required=False,
        widget=forms.Select(attrs={"class": "select2-dx"}),
    )

    med_code = forms.CharField(
        label=_("Medication code"),
        required=False,
        widget=forms.Select(attrs={"class": "select2-med"}),
    )
    lab_code = forms.CharField(
        label=_("Lab test code"),
        required=False,
        widget=forms.Select(attrs={"class": "select2-lab"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        

    def clean(self):
        cleaned_data = super().clean()

        # Flags
        has_code = any(cleaned_data.get(f) for f in ["dx_code", "med_code", "lab_code"])
        has_info = any(
            cleaned_data.get(f)
            for f in ["patient_id", "first_name", "last_name", "min_age", "max_age"]
        )
        start = cleaned_data.get("search_start")
        end = cleaned_data.get("search_end")
        min_age = cleaned_data.get("min_age")
        max_age = cleaned_data.get("max_age")

        # Must fill at least one field
        if not (has_info or has_code or start or end):
            raise ValidationError(_("Please fill in at least one field."))

        # If using code filters, date range is required
        if has_code and (not start or not end):
            raise ValidationError(
                _("Please specify a date range when searching with codes.")
            )

        # Validate date range
        if start and end and start > end:
            raise ValidationError(_("Start date must be before end date."))

        # Validate age range
        if min_age is not None and max_age is not None and max_age < min_age:
            raise ValidationError(
                _("Minimum age must be smaller than or equal to maximum age.")
            )


class ClinicalRecordSelectionForm(forms.Form):
    """Select a date range and date for viewing clinical records."""

    period = forms.IntegerField(
        label=_("Select period (days)"),
        min_value=1,
        max_value=365,
        required=True,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    date_selection = forms.ChoiceField(
        label=_("Select a date"),
        choices=[],
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(
        self,
        *args,
        dates: list[str] | None = None,
        allow_all: bool = False,
        initial_period: int = 1,
        **kwargs,
    ):
        """
        Args:
            dates: List of date strings.
            allow_all: Whether to include an "all records" option.
            initial_period: Default number of days to include in the period.
        """
        super().__init__(*args, **kwargs)

        choices = []
        if dates:
            if allow_all:
                choices.append(("all", _("All Records")))
                self.fields["date_selection"].initial = "all"
            choices.extend((d, d) for d in dates)
            self.fields["date_selection"].initial = (
                self.fields["date_selection"].initial or dates[0]
            )
        else:
            self.fields["date_selection"].initial = None
            self.fields["date_selection"].widget.attrs["disabled"] = True

        self.fields["date_selection"].choices = choices
        self.fields["period"].initial = initial_period


class RelationEditForm(forms.ModelForm):
    """Edit user-patient relationship metadata."""

    comment = forms.CharField(
        label=_("Comment"),
        required=False,
        max_length=UserPatientRelation._meta.get_field("comment").max_length,
        widget=forms.Textarea(attrs={"rows": 10}),
    )

    class Meta:
        model = UserPatientRelation
        fields = ["color", "comment"]
