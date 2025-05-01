from django.urls import path
from .views import (
    search_users,
    user_edit_view
)

urlpatterns = [
    # User search
    path("find_users/", search_users, name="staff_find_users"),
    # Edit user profile
    path("<str:pk>/edit_user/", user_edit_view, name="staff_edit_user"),
]
