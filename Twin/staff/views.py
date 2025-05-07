from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_protect
from django.db.models import Q
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from accounts.models import CustomUser
from accounts.forms import CustomUserChangeForm
from .forms import UserSearchForm


# Create your views here.
@login_required
@user_passes_test(lambda u: u.is_staff)
@csrf_protect
def search_users(request: HttpRequest) -> HttpResponse:
    """Search users with keywords.
    Args:
        request (HttpRequest): HTTP request.
    Returns:
        HttpResponse: HTTP Response .
    """
    # Parse dates from database
    if request.method == "GET":
        users = []
        return render(
            request,
            "staff/user_search.html",
            {"form": UserSearchForm()},
        )
    elif request.method == "POST":
        form = UserSearchForm(request.POST)
        if form.is_valid():
            kw = form.cleaned_data["keyword"]
            patient_list = CustomUser.objects.filter(
                Q(email__contains=kw)
                | Q(first_name__contains=kw)
                | Q(last_name__contains=kw)
            )
            users = patient_list.order_by("-email")
            return render(
                request,
                "staff/user_search.html",
                {"users": users, "form": UserSearchForm()},
            )
        else:
            return render(
                request,
                "staff/user_search.html",
                {"form": form},
            )


@login_required
@user_passes_test(lambda u: u.is_staff)
@csrf_protect
def user_edit_view(request: HttpRequest, pk: str) -> HttpResponse:
    """Edits user profiles."""
    # Here, 'user' is the current user, and 'account' is the user to be edited.
    user = request.user
    account = get_object_or_404(
        CustomUser,
        pk=pk,
    )
    if user.is_staff:
        if request.method == "GET":
            form = CustomUserChangeForm(instance=account, user=user)
            return render(
                request,
                "staff/user_edit.html",
                {"account": account, "form": form},
            )
        if request.method == "POST":
            form = CustomUserChangeForm(request.POST, instance=account, user=user)
            if form.is_valid():
                form.save()
                messages.success(
                    request, "User information has been successfully saved."
                )
                return redirect("account_user_home", pk=account.pk)
            else:
                return render(
                    request,
                    "staff/user_edit.html",
                    {"account": account, "form": form},
                )
