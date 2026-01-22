from django.urls import path
from . import views

urlpatterns = [
    path("", views.audit_center, name="audit_center"),
    path("certificates/<str:certificate_id>/download/", views.certificate_download, name="certificate-download"),
]
