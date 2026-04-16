import cv2
import face_recognition
import mysql.connector
import numpy as np
import json
import serial
import serial.tools.list_ports
import requests
from requests.auth import HTTPDigestAuth
import time
from datetime import datetime

# ============================================================
# KONFIGURASI
# ============================================================
CCTV_URL = 'http://10.10.111.47/ISAPI/Streaming/channels/101/picture?username=admin&password=123456xx'
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'face_recognition'
}
LOG_INTERVAL = 10       # Jeda minimum antar log per orang (detik)
CCTV_TIMEOUT = 5        # Timeout koneksi CCTV (detik)
FACE_TOLERANCE = 0.5    # Toleransi pencocokan wajah (semakin kecil semakin ketat)

# ============================================================
# KONEKSI DATABASE
# ============================================================
print("Menghubungkan ke database...")
try:
    db = mysql.connector.connect(**DB_CONFIG)
    cursor = db.cursor()
    print("Database terhubung!")
except Exception as e:
    print(f"Gagal koneksi database: {e}")
    exit()

# ============================================================
# LOAD ENCODING WAJAH
# ============================================================
def load_encodings():
    cursor.execute("SELECT id, nama, nim, encoding_wajah FROM data_anggota WHERE encoding_wajah IS NOT NULL")
    rows = cursor.fetchall()
    
    encodings = []
    names = []
    ids = []
    
    for row in rows:
        id_anggota, nama, nim, encoding_str = row
        try:
            encoding = np.array(json.loads(encoding_str))
            encodings.append(encoding)
            names.append(f"{nama} ({nim})")
            ids.append(id_anggota)
        except:
            print(f"Gagal load encoding untuk {nama}")
    
    return encodings, names, ids

print("Loading data wajah dari database...")
known_encodings, known_names, known_ids = load_encodings()
print(f"Total {len(known_encodings)} wajah terdaftar")

# ============================================================
# KONEKSI ESP32 via SERIAL
# ============================================================
def cari_port_esp32():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if 'USB' in port.description or 'CH340' in port.description or 'CP210' in port.description:
            return port.device
    return None

ser = None
port = cari_port_esp32()
if port:
    try:
        ser = serial.Serial(port, 115200, timeout=1)
        print(f"ESP32 terhubung di {port}")
    except:
        print(f"Gagal buka port {port}, mode standalone")
else:
    print("ESP32 tidak ditemukan, mode standalone (deteksi terus-menerus)")

# ============================================================
# FUNGSI AMBIL FRAME CCTV
# ============================================================
def ambil_frame_cctv():
    try:
        response = requests.get(
            'http://10.10.111.47/ISAPI/Streaming/channels/101/picture',
            auth=HTTPDigestAuth('admin', '123456xx'),
            timeout=CCTV_TIMEOUT
        )
        if response.status_code == 200:
            arr = np.asarray(bytearray(response.content), dtype=np.uint8)
            frame = cv2.imdecode(arr, -1)
            return frame
        else:
            print(f"CCTV error: {response.status_code}")
            return None
    except Exception as e:
        print(f"Gagal ambil frame CCTV: {e}")
        return None

# ============================================================
# FUNGSI SIMPAN LOG
# ============================================================
def simpan_log(id_anggota, nama):
    try:
        now = datetime.now()
        cursor.execute(
            "INSERT INTO log_deteksi (id_anggota, status) VALUES (%s, %s)",
            (id_anggota, "TERDETEKSI")
        )
        cursor.execute("""
            INSERT INTO statistik_lewat (id_anggota, tanggal, jumlah_lewat)
            VALUES (%s, %s, 1)
            ON DUPLICATE KEY UPDATE jumlah_lewat = jumlah_lewat + 1
        """, (id_anggota, now.date()))
        db.commit()
        print(f"[{now.strftime('%H:%M:%S')}] ✓ Terdeteksi: {nama}")
    except Exception as e:
        print(f"Gagal simpan log: {e}")
        db.rollback()

# ============================================================
# FUNGSI PROSES FRAME
# ============================================================
def proses_frame(frame):
    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
    rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings_list = face_recognition.face_encodings(rgb_frame, face_locations)

    hasil = []
    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings_list):
        name = "Tidak Dikenal"
        color = (0, 0, 255)
        id_anggota = None

        if known_encodings:
            matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=FACE_TOLERANCE)
            distances = face_recognition.face_distance(known_encodings, face_encoding)
            best_match = np.argmin(distances)

            if matches[best_match]:
                name = known_names[best_match]
                id_anggota = known_ids[best_match]
                color = (0, 255, 0)

        # Scale balik koordinat
        top, right, bottom, left = top*4, right*4, bottom*4, left*4
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        cv2.rectangle(frame, (left, bottom-35), (right, bottom), color, cv2.FILLED)
        cv2.putText(frame, name, (left+6, bottom-6),
                    cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)

        hasil.append((id_anggota, name))

    return frame, hasil

# ============================================================
# MAIN LOOP
# ============================================================
print("\n" + "="*50)
print("Sistem Deteksi Wajah IoT - VisionGuard")
print("Tekan Q untuk keluar")
print("="*50 + "\n")

last_log_time = {}
pir_aktif = False

while True:
    try:
        # Cek sinyal PIR dari ESP32
        if ser and ser.in_waiting > 0:
            data = ser.readline().decode('utf-8').strip()
            if 'Gerakan terdeteksi' in data:
                pir_aktif = True
                print(f"[PIR] Gerakan terdeteksi!")

        # Ambil frame — jika ESP32 tidak ada, ambil terus-menerus
        if pir_aktif or ser is None:
            frame = ambil_frame_cctv()
            pir_aktif = False  # Reset setelah ambil frame

            if frame is None:
                time.sleep(1)
                continue

            # Proses deteksi wajah
            frame, hasil = proses_frame(frame)

            # Simpan log untuk wajah yang dikenali
            now = datetime.now()
            for id_anggota, nama in hasil:
                if id_anggota is not None:
                    last_time = last_log_time.get(id_anggota)
                    if last_time is None or (now - last_time).seconds >= LOG_INTERVAL:
                        last_log_time[id_anggota] = now
                        simpan_log(id_anggota, nama)

            # Tampilkan frame
            cv2.imshow("VisionGuard - Sistem Deteksi Wajah", frame)

        # Keluar dengan Q
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        time.sleep(0.1)

    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(1)
        continue

# Cleanup
cv2.destroyAllWindows()
if ser:
    ser.close()
db.close()
print("\nSistem deteksi dihentikan.")