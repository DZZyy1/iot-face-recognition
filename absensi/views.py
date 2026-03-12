from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import DataAnggota, LogDeteksi, StatistikLewat
from .serializers import DataAnggotaSerializer, LogDeteksiSerializer
import cv2
import face_recognition
import numpy as np
import json
from datetime import datetime

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