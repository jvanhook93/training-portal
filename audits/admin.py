from django.contrib import admin
from .models import AuditEvent

admin.site.register(AuditEvent)

admin.site.site_header = "IntegraNet Training Administration"
admin.site.site_title = "IntegraNet Training"
admin.site.index_title = "Training Portal Dashboard"