import os  
import cv2
import face_recognition
import numpy as np
import json
import base64
from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import DataAnggota, LogDeteksi, StatistikLewat
from .serializers import DataAnggotaSerializer, LogDeteksiSerializer
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from datetime import datetime, timedelta
from django.db.models import Count
from django.conf import settings
from .models import DataAnggota, LogDeteksi, StatistikLewat, SensorStatus
from django.utils import timezone

class DataAnggotaViewSet(viewsets.ModelViewSet):
    queryset = DataAnggota.objects.all()
    serializer_class = DataAnggotaSerializer

class LogDeteksiViewSet(viewsets.ModelViewSet):
    queryset = LogDeteksi.objects.all().order_by('-waktu_deteksi')
    serializer_class = LogDeteksiSerializer

@api_view(['POST'])
def deteksi_pir(request):
    if request.data.get('pir') != '1':
        return Response({'status': 'ignored'})

    # Ambil frame dari webcam
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        return Response({'status': 'error', 'message': 'Gagal ambil frame'}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Load encoding dari database
    anggota_list = DataAnggota.objects.exclude(encoding_wajah=None)
    known_encodings = []
    known_ids = []

    for anggota in anggota_list:
        encoding = np.array(json.loads(anggota.encoding_wajah))
        known_encodings.append(encoding)
        known_ids.append(anggota.id)

    # Deteksi wajah
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    hasil = []
    for face_encoding in face_encodings:
        matches = face_recognition.compare_faces(known_encodings, face_encoding)
        distances = face_recognition.face_distance(known_encodings, face_encoding)

        if len(distances) > 0 and matches[np.argmin(distances)]:
            id_anggota = known_ids[np.argmin(distances)]
            anggota = DataAnggota.objects.get(id=id_anggota)

            # Simpan log
            log = LogDeteksi.objects.create(
                id_anggota=anggota,
                status='TERDETEKSI'
            )
            hasil.append({'nama': anggota.nama, 'nim': anggota.nim})

    return Response({
        'status': 'ok',
        'terdeteksi': hasil,
        'jumlah_wajah': len(face_encodings)
    })


@login_required
def dashboard(request):
    total_anggota = DataAnggota.objects.count()
    total_log = LogDeteksi.objects.count()
    deteksi_hari_ini = LogDeteksi.objects.filter(
        waktu_deteksi__date=datetime.today().date()
    ).count()
    log_terbaru = LogDeteksi.objects.select_related('id_anggota').order_by('-waktu_deteksi')[:10]
    sensor_aktif = cek_sensor_aktif()
    
    return render(request, 'dashboard.html', {
        'total_anggota': total_anggota,
        'total_log': total_log,
        'deteksi_hari_ini': deteksi_hari_ini,
        'log_terbaru': log_terbaru,
        'sensor_aktif': sensor_aktif,
    })

@login_required
def anggota_list(request):
    anggota_list = DataAnggota.objects.all().order_by('-created_at')
    return render(request, 'anggota.html', {
        'anggota_list': anggota_list,
        'total_anggota': anggota_list.count(),
    })

@login_required
def log_list(request):
    logs = LogDeteksi.objects.select_related('id_anggota').order_by('-waktu_deteksi')
    search = request.GET.get('search')
    tanggal = request.GET.get('tanggal')
    if search:
        logs = logs.filter(id_anggota__nama__icontains=search)
    if tanggal:
        logs = logs.filter(waktu_deteksi__date=tanggal)
    return render(request, 'log.html', {
        'log_list': logs,
        'total_log': logs.count(),
    })

@login_required
def statistik(request):
    labels = []
    data = []
    for i in range(6, -1, -1):
        tgl = datetime.today().date() - timedelta(days=i)
        count = LogDeteksi.objects.filter(waktu_deteksi__date=tgl).count()
        labels.append(tgl.strftime('%d %b'))
        data.append(count)
    
    today = datetime.today().date()
    minggu_lalu = today - timedelta(days=7)
    bulan_ini = today.replace(day=1)
    
    top_anggota = LogDeteksi.objects.values(
        'id_anggota__nama', 'id_anggota__nim'
    ).annotate(total=Count('id')).order_by('-total')[:5]

    return render(request, 'statistik.html', {
        'chart_labels': labels,
        'chart_data': data,
        'deteksi_minggu': LogDeteksi.objects.filter(waktu_deteksi__date__gte=minggu_lalu).count(),
        'deteksi_bulan': LogDeteksi.objects.filter(waktu_deteksi__date__gte=bulan_ini).count(),
        'rata_rata': round(LogDeteksi.objects.count() / max((today - DataAnggota.objects.earliest('created_at').created_at.date()).days, 1), 1) if DataAnggota.objects.exists() else 0,
        'top_anggota': top_anggota,
    })
@login_required
def anggota_tambah(request):
    if request.method == 'POST':
        nama = request.POST.get('nama')
        nim = request.POST.get('nim')
        foto_base64 = request.POST.get('foto_base64')

        encoding_str = None
        foto_path = None

        if foto_base64:
            foto_data = foto_base64.split(',')[1]
            foto_bytes = base64.b64decode(foto_data)
            nparr = np.frombuffer(foto_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # Encode wajah
            encodings = face_recognition.face_encodings(rgb_img)
            if encodings:
                encoding_str = json.dumps(encodings[0].tolist())

            # Simpan foto
            media_dir = os.path.join(settings.MEDIA_ROOT, 'foto_anggota')
            os.makedirs(media_dir, exist_ok=True)
            foto_filename = f"{nim}_{nama}.jpg"
            foto_path = os.path.join(media_dir, foto_filename)
            cv2.imwrite(foto_path, img)

        DataAnggota.objects.create(
            nama=nama,
            nim=nim,
            encoding_wajah=encoding_str,
            foto_wajah=f"foto_anggota/{foto_filename}" if foto_path else None
        )
        return redirect('/anggota/')

    return render(request, 'anggota_tambah.html')
@login_required
def anggota_hapus(request, pk):
    anggota = DataAnggota.objects.get(id=pk)
    anggota.delete()
    return redirect('/anggota/')

@login_required
def anggota_detail(request, pk):
    anggota = DataAnggota.objects.get(id=pk)
    
    # Log hari ini
    hari_ini = datetime.today().date()
    log_hari_ini = LogDeteksi.objects.filter(
        id_anggota=anggota,
        waktu_deteksi__date=hari_ini
    ).count()
    
    # Log 7 hari terakhir
    labels = []
    data = []
    for i in range(6, -1, -1):
        tgl = hari_ini - timedelta(days=i)
        count = LogDeteksi.objects.filter(
            id_anggota=anggota,
            waktu_deteksi__date=tgl
        ).count()
        labels.append(tgl.strftime('%d %b'))
        data.append(count)
    
    # Log terbaru
    log_terbaru = LogDeteksi.objects.filter(
        id_anggota=anggota
    ).order_by('-waktu_deteksi')[:10]
    
    # Total semua log
    total_log = LogDeteksi.objects.filter(id_anggota=anggota).count()

    return render(request, 'anggota_detail.html', {
        'anggota': anggota,
        'log_hari_ini': log_hari_ini,
        'total_log': total_log,
        'log_terbaru': log_terbaru,
        'chart_labels': labels,
        'chart_data': data,
    })

def logout_view(request):
    logout(request)
    return redirect('/login/')

@api_view(['POST'])
def sensor_ping(request):
    obj, _ = SensorStatus.objects.get_or_create(id=1)
    obj.save()
    return Response({'status': 'ok'})

def cek_sensor_aktif():
    try:
        sensor = SensorStatus.objects.get(id=1)
        selisih = (timezone.now() - sensor.last_ping).seconds
        return selisih < 15  # aktif jika ping dalam 15 detik terakhir
    except:
        return False