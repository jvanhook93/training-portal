from django.contrib import admin
from .models import Course, CourseVersion, Assignment, VideoProgress

admin.site.register(Course)
admin.site.register(CourseVersion)
admin.site.register(Assignment)
admin.site.register(VideoProgress)