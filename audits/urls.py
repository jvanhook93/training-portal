# audits/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path(
        "certificates/<str:certificate_id>/download/",
        views.certificate_download,
        name="certificate-download",
    ),
]
