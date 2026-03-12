from django.db import models

class DataAnggota(models.Model):
    nama = models.CharField(max_length=100)
    nim = models.CharField(max_length=50)
    encoding_wajah = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'data_anggota'

    def __str__(self):
        return f"{self.nama} ({self.nim})"

class LogDeteksi(models.Model):
    id_anggota = models.ForeignKey(DataAnggota, on_delete=models.CASCADE, null=True)
    waktu_deteksi = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = 'log_deteksi'

class StatistikLewat(models.Model):
    id_anggota = models.ForeignKey(DataAnggota, on_delete=models.CASCADE, null=True)
    tanggal = models.DateField()
    jumlah_lewat = models.IntegerField(default=0)

    class Meta:
        managed = False
        db_table = 'statistik_lewat'