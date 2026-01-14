from django.urls import path
from . import views
from .views import dashboard, complete_course_version, download_certificate
import os
from django.conf import settings

urlpatterns = [
    path("training/<int:course_version_id>/", views.my_training, name="my_training"),
    path("training/<int:course_version_id>/video-ping/", views.video_ping, name="video_ping"),

    path("dashboard/", dashboard, name="dashboard"),

    path("training/<int:course_version_id>/complete/", complete_course_version, name="complete_training"),
    path("certificates/<str:certificate_id>/download/", download_certificate, name="download_certificate"),
    path("training/<int:course_version_id>/quiz/", views.take_quiz, name="take_quiz"),
    path("training/<int:course_version_id>/quiz/submit/", views.submit_quiz, name="submit_quiz"),

    path("api/courses/", views.courses_list, name="api-courses-list"),
    path("api/me/assignments/", views.my_assignments, name="api-my-assignments"),
]
