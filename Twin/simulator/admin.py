from django.contrib import admin
from .models import SimulationRequest, SimulationResult

# Register your models here.
admin.site.register(SimulationRequest)
admin.site.register(SimulationResult)
