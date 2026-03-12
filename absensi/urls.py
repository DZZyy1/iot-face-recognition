from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'anggota', views.DataAnggotaViewSet)
router.register(r'log', views.LogDeteksiViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('deteksi/', views.deteksi_pir, name='deteksi-pir'),
]