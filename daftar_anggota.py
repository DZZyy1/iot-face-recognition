import cv2
import face_recognition
import mysql.connector
import numpy as np
import json

# Koneksi database
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",  # kosong jika pakai XAMPP default
    database="face_recognition"
)
cursor = db.cursor()

# Input data anggota
nama = input("Masukkan nama anggota: ")
nim = input("Masukkan NIM/ID anggota: ")

# Ambil foto dari webcam
print("\nBersiap ambil foto... Tekan SPASI untuk foto, ESC untuk batal")
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    cv2.imshow("Ambil Foto - Tekan SPASI", frame)
    
    key = cv2.waitKey(1)
    if key == 32:  # SPASI
        foto = frame
        break
    elif key == 27:  # ESC
        print("Dibatalkan!")
        cap.release()
        cv2.destroyAllWindows()
        exit()

cap.release()
cv2.destroyAllWindows()

# Proses encoding wajah
print("Memproses wajah...")
rgb_foto = cv2.cvtColor(foto, cv2.COLOR_BGR2RGB)
encodings = face_recognition.face_encodings(rgb_foto)

if len(encodings) == 0:
    print("Wajah tidak terdeteksi! Coba lagi.")
    exit()

encoding = encodings[0]
encoding_str = json.dumps(encoding.tolist())

# Simpan ke database
sql = "INSERT INTO data_anggota (nama, nim, encoding_wajah) VALUES (%s, %s, %s)"
cursor.execute(sql, (nama, nim, encoding_str))
db.commit()

print(f"\nBerhasil! {nama} ({nim}) sudah terdaftar!")
db.close()