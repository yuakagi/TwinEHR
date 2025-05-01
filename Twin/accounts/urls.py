from django.urls import path
from .views import (
    CustomLoginView,
    CustomLogoutView,
    signup_view,
    UserHomeView,
    redirect_to_user_home,
    follow_unfollow,
    edit_user_patient_relation,
)

urlpatterns = [
    # Log in
    path("login/", CustomLoginView.as_view(), name="account_login"),
    # log out
    path(
        "logout/",
        CustomLogoutView.as_view(),
        name="account_logout",
    ),
    # Sign up
    path("signup/", signup_view, name="account_signup"),
    # User home and redirect
    path("<uuid:pk>/home/", UserHomeView.as_view(), name="account_user_home"),
    path(
        "account_user_home_redirect/",
        redirect_to_user_home,
        name="account_user_home_redirect",
    ),
    # Follow or unfollow patient
    path(
        "account_follow_unfollow/",
        follow_unfollow,
        name="account_follow_unfollow",
    ),
    # Edit user-patient relation
    path(
        "edit_user_patient_relation/",
        edit_user_patient_relation,
        name="account_edit_user_patient_relation",
    ),
]
