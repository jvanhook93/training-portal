from django.urls import path
from . import views

urlpatterns = [
    path("training/<int:course_version_id>/", views.my_training, name="my_training"),
    path("training/<int:course_version_id>/video-ping/", views.video_ping, name="video_ping"),
]