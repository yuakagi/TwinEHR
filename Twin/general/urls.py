from django.urls import path
from .views import LandingPageView

urlpatterns = [
    # Landing page
    path("", LandingPageView.as_view(), name="landing"),
]
