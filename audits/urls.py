from django.urls import path
from .views import audit_center
from . import views


urlpatterns = [
    path("", audit_center, name="audit_center"),
    path("certificates/<str:certificate_id>/download/", views.certificate_download, name="certificate-download"),
]
