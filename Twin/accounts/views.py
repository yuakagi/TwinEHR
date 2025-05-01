import json
from typing import Any
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import DetailView
from django.utils.decorators import method_decorator
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.forms.models import model_to_dict
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django_ratelimit.decorators import ratelimit
from clinical_records.models import Patients
from twin_utils import UUIDEncoder, is_ajax
from .models import CustomUser, UserPatientRelation
from .forms import RelationEditForm, CustomUserCreationForm


# Sign in
class CustomLoginView(LoginView):
    """Sign in view"""

    template_name = "account/login.html"

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        # Redirect if already logged in
        if request.user.is_authenticated:
            return redirect("account_user_home", pk=request.user.pk)
        # Other default dispatch behaviors
        return super().dispatch(request, *args, **kwargs)

    # Redirect to user home after successful login
    def get_success_url(self):
        return reverse("account_user_home", kwargs={"pk": self.request.user.pk})


# Sign out
class CustomLogoutView(LogoutView):
    template_name = "general/landing.html"

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        if request.method == "GET":
            return self.post(request, *args, **kwargs)
        return super().dispatch(request, *args, **kwargs)


# Sing up
# NOTE: Currently, creating a user is only allowed for authorized users.
@login_required
@user_passes_test(lambda u: u.is_staff)
@ratelimit(key="ip", rate="5/m", method="POST", block=True)
def signup_view(request: HttpRequest):
    """Handles user signup process"""
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # If you want to implement auto-login after successful signup, add the lines below:
            # if user.is_active:
            #   login(request, user)
            return redirect("account_user_home", pk=request.user.pk)
    else:
        form = CustomUserCreationForm()

    return render(request, "account/signup.html", {"form": form})


def redirect_to_user_home(request: HttpRequest) -> HttpResponse:
    """Redirects to user home."""
    if request.user.is_authenticated:
        return redirect("account_user_home", pk=request.user.pk)
    else:
        return redirect("landing")


class UserHomeView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """User home"""

    model = CustomUser
    template_name = "account/user_home.html"
    context_object_name = "account"

    def test_func(self):
        """Test function for UserPassesTestMixin"""
        # Superuser has access to all pages.
        if self.request.user.is_staff:
            return True
        # Other users can only have access to their own page.
        else:
            obj = self.get_object()
            return obj.pk == self.request.user.pk

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        relations = UserPatientRelation.objects.filter(
            user=self.get_object(), is_active=True
        )

        # Fetch all relevant Patients from clinical_records DB in one query
        patient_ids = [r.patient_id for r in relations]
        patients_map = {
            p.patient_id: p
            for p in Patients.objects.filter(
                patient_id__in=patient_ids
            )
        }
        print(patients_map)

        # Attach the corresponding patient object to each relation manually
        for r in relations:
            print(r)
            print(r.patient_id)
            r.patient = patients_map.get(r.patient_id)
            print(r.patient)

        print(relations)

        context["relations"] = relations
        return context


@login_required
@csrf_protect
@ratelimit(key="user", rate="10/m", method="POST", block=True)
def follow_unfollow(request: HttpRequest) -> HttpResponse:
    """Follow or unfollow patient.
    Once a relation is created, then it is not deleted. Instead, it is inactivated.
    """
    if (request.method == "POST") and is_ajax(request):
        patient = request.POST.get("patient", None)
        patient = get_object_or_404(Patients, pk=patient)
        try:
            relation = UserPatientRelation.objects.get(
                user=request.user, patient_id=patient.patient_id
            )
        except UserPatientRelation.DoesNotExist:
            relation = None

        # Create new
        if relation is None:
            relation = UserPatientRelation.objects.create(
                user=request.user, patient_id=patient.patient_id, comment=""
            )
            following = True
        # Activate or deactivate
        else:
            if relation.is_active:
                relation.is_active = False
                relation.save()
                following = False
            else:
                relation.is_active = True
                relation.save()
                following = True
        ctx = {"following": following, "relation": model_to_dict(relation)}
        # NOTE: You need UUIDEncoder here because relation objects contain UUIDs, which are
        #       not serializable by default.
        return HttpResponse(
            json.dumps(ctx, cls=UUIDEncoder), content_type="application/json"
        )


@login_required
@csrf_protect
@ratelimit(key="user", rate="10/m", method="POST", block=True)
def edit_user_patient_relation(request: HttpRequest) -> JsonResponse:
    """Edit user-patient relation"""
    if request.method == "POST" and (is_ajax(request)):
        form = RelationEditForm(data=request.POST)
        if form.is_valid():
            user = CustomUser.objects.get(pk=request.POST.get("user"))
            patient = Patients.objects.get(pk=request.POST.get("patient"))
            try:
                relation = UserPatientRelation.objects.get(
                    user=user, patient_id=patient.patient_id
                )
                relation.color = form.cleaned_data["color"]
                relation.comment = form.cleaned_data["comment"]
                relation.save()
                ctx = {
                    "message": "Successfully saved",
                    "relation": model_to_dict(relation),
                }
                return JsonResponse(ctx, status=200)

            except UserPatientRelation.DoesNotExist:
                ctx = {"message": "Bad request, requested user-patient does not exist."}
                return JsonResponse(ctx, status=400)
        else:
            # TODO: Handle form error messanges in the html template, returning form as context.
            ctx = {"message": "Form invalid"}
            return JsonResponse(ctx, status=400)
