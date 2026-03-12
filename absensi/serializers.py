from rest_framework import serializers
from .models import DataAnggota, LogDeteksi, StatistikLewat

class DataAnggotaSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataAnggota
        fields = '__all__'

class LogDeteksiSerializer(serializers.ModelSerializer):
    nama_anggota = serializers.CharField(source='id_anggota.nama', read_only=True)
    class Meta:
        model = LogDeteksi
        fields = '__all__'

class StatistikLewatSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatistikLewat
        fields = '__all__'