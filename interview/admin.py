from django.contrib import admin
from .models import InterviewSession, InterviewResponse, Resume

admin.site.register(InterviewSession)
admin.site.register(InterviewResponse)
admin.site.register(Resume)