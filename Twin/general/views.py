from django.views.generic import TemplateView


class LandingPageView(TemplateView):
    """Landing page"""

    template_name = "general/landing.html"
