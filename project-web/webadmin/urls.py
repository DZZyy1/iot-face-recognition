"""
URL configuration for webadmin project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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
from django.urls import path, include
from django.contrib.auth import views as auth_views
from absensi import views as absensi_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('absensi.urls')),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', absensi_views.logout_view, name='logout'),
    path('dashboard/', absensi_views.dashboard, name='dashboard'),
    path('anggota/', absensi_views.anggota_list, name='anggota'),
    path('log/', absensi_views.log_list, name='log'),
    path('statistik/', absensi_views.statistik, name='statistik'),
    path('anggota/tambah/', absensi_views.anggota_tambah, name='anggota-tambah'),
    path('anggota/<int:pk>/hapus/', absensi_views.anggota_hapus, name='anggota-hapus'),
    path('anggota/<int:pk>/', absensi_views.anggota_detail, name='anggota-detail'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


