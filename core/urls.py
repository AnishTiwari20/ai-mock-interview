"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from interview.views import home
from interview.views import home, start_interview
from interview.views import home, start_interview, upload_resume
from interview.views import dashboard
from interview import views
from interview.views import signup


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home),
    path('interview/', start_interview, name='interview'),
    path('upload-resume/', upload_resume, name='upload_resume'),
    path("dashboard/", dashboard, name="dashboard"),
    path('download-report/<int:session_id>/', views.download_report, name='download_report'),
    path("signup/", signup, name="signup"),

    # Built-in authentication URLs
    path('accounts/', include('django.contrib.auth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)