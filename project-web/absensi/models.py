from django.db import models

class DataAnggota(models.Model):
    nama = models.CharField(max_length=100)
    nim = models.CharField(max_length=50)
    foto_wajah = models.ImageField(upload_to='foto_anggota/', null=True, blank=True)
    encoding_wajah = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True 
        db_table = 'data_anggota'

    def __str__(self):
        return f"{self.nama} ({self.nim})"

class LogDeteksi(models.Model):
    id_anggota = models.ForeignKey(
        DataAnggota, 
        on_delete=models.CASCADE, 
        null=True,
        db_column='id_anggota'  # tambahkan ini
    )
    waktu_deteksi = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = 'log_deteksi'

class StatistikLewat(models.Model):
    id_anggota = models.ForeignKey(
        DataAnggota, 
        on_delete=models.CASCADE, 
        null=True,
        db_column='id_anggota'  # tambahkan ini
    )
    tanggal = models.DateField()
    jumlah_lewat = models.IntegerField(default=0)

    class Meta:
        managed = False
        db_table = 'statistik_lewat'
    
class SensorStatus(models.Model):
    last_ping = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sensor_status'