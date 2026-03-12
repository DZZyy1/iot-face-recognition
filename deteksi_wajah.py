import cv2
import face_recognition
import mysql.connector
import numpy as np
import json
from datetime import datetime

# Koneksi database
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="face_recognition"
)
cursor = db.cursor()

# Load semua encoding wajah dari database
print("Loading data wajah dari database...")
cursor.execute("SELECT id, nama, nim, encoding_wajah FROM data_anggota")
rows = cursor.fetchall()

known_encodings = []
known_names = []
known_ids = []

for row in rows:
    id_anggota, nama, nim, encoding_str = row
    encoding = np.array(json.loads(encoding_str))
    known_encodings.append(encoding)
    known_names.append(f"{nama} ({nim})")
    known_ids.append(id_anggota)

print(f"Total {len(known_encodings)} wajah terdaftar")

# Mulai webcam
cap = cv2.VideoCapture(0)
print("Deteksi dimulai... Tekan Q untuk keluar")

last_log_time = {}  # Hindari log spam

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Resize untuk proses lebih cepat
    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
    rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    # Deteksi wajah
    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=0.5)
        distances = face_recognition.face_distance(known_encodings, face_encoding)

        name = "Tidak Dikenal"
        color = (0, 0, 255)  # Merah
        id_anggota = None

        if len(distances) > 0:
            best_match = np.argmin(distances)
            if matches[best_match]:
                name = known_names[best_match]
                id_anggota = known_ids[best_match]
                color = (0, 255, 0)  # Hijau

                # Simpan log (max 1x per 10 detik per orang)
                now = datetime.now()
                last_time = last_log_time.get(id_anggota)
                if last_time is None or (now - last_time).seconds >= 10:
                    last_log_time[id_anggota] = now

                    # INSERT log deteksi
                    cursor.execute(
                        "INSERT INTO log_deteksi (id_anggota, status) VALUES (%s, %s)",
                        (id_anggota, "TERDETEKSI")
                    )
                    # UPDATE statistik
                    cursor.execute("""
                        INSERT INTO statistik_lewat (id_anggota, tanggal, jumlah_lewat)
                        VALUES (%s, %s, 1)
                        ON DUPLICATE KEY UPDATE jumlah_lewat = jumlah_lewat + 1
                    """, (id_anggota, now.date()))
                    db.commit()
                    print(f"[{now.strftime('%H:%M:%S')}] Terdeteksi: {name}")

        # Gambar kotak & nama (scale back up)
        top, right, bottom, left = top*4, right*4, bottom*4, left*4
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        cv2.rectangle(frame, (left, bottom-35), (right, bottom), color, cv2.FILLED)
        cv2.putText(frame, name, (left+6, bottom-6),
                    cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)

    cv2.imshow("Sistem Deteksi Wajah", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
db.close()
print("Deteksi selesai!")