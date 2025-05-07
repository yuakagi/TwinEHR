from django.urls import path
from .views import simulation_page_view, submit_simulation_request, retrieve_simulation_results,browse_simulation

urlpatterns = [
    # Simulation results
    path("home/", simulation_page_view, name="simulator_home"),
    # Simulation API funcs
    path("api/submit/", submit_simulation_request, name="simulator_submit_request"),
    path("api/retrieve/", retrieve_simulation_results, name="simulator_poll"),
    path("api/browse/", browse_simulation, name="simulator_browse"),

]
