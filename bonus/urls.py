"""
URL configuration for bonus project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path
from pa_bonus import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('upload/', views.upload_file, name='upload_file'),
    path('upload_history/', views.upload_history, name='upload_history'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('history/', views.HistoryView.as_view(), name='history'),
    path('history/detail/<int:pk>/', views.HistoryDetailView.as_view(), name='history_detail'),
    path('rewards/', views.RewardsView.as_view(), name='rewards'),
    path('rewards/requests/', views.RewardsRequestsView.as_view(), name='reward_requests'),
    path('rewards/requests/detail/', views.RequestsDetailView.as_view(), name='requests_detail'),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)