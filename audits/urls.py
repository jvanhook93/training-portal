from django.urls import path
from .views import audit_center

urlpatterns = [
    path("", audit_center, name="audit_center"),
]
