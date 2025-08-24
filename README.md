# API Pelacak Pengeluaran (Expensee API)

Ini adalah layanan backend untuk aplikasi Expensee. API ini menyediakan berbagai endpoint untuk otentikasi pengguna, mengunggah struk, dan melacak pengeluaran.

## Teknologi yang Digunakan

- **Framework**: FastAPI
- **Database**: PostgreSQL dengan SQLAlchemy ORM
- **Otentikasi**: JWT (JSON Web Tokens)
- **Pemrosesan Gambar**: Google Cloud Vision & Google Generative AI
- **Penyimpanan File**: Google Cloud Storage
- **Kontainerisasi**: Docker & Docker Compose

---

## Panduan Menjalankan Proyek

Ada dua cara untuk menjalankan proyek ini: menggunakan **Docker** (direkomendasikan) atau menjalankannya secara **Lokal** di mesin Anda.

### Prasyarat

Pastikan perangkat Anda telah terinstal:

- **Python** versi 3.9 atau lebih tinggi.
- **Docker** dan **Docker Compose** (untuk metode Docker).
- **Git** untuk mengkloning repositori.

---

### Cara 1: Menjalankan dengan Docker (Direkomendasikan)

Metode ini paling mudah karena semua layanan (API dan database) akan berjalan di dalam kontainer Docker.

#### 1. Clone Repositori

Buka terminal Anda dan jalankan perintah berikut:

```bash
git clone https://github.com/nabil-devId/expensee-api.git
cd expensee-api
```

#### 2. Konfigurasi Environment

Salin file `.env.example` menjadi `.env`. File ini berisi semua konfigurasi yang dibutuhkan oleh aplikasi.

```bash
cp .env.example .env
```

Setelah itu, buka file `.env` dan isi variabel-variabel berikut sesuai dengan konfigurasi Anda:

- `POSTGRES_USER`: Nama pengguna untuk database PostgreSQL.
- `POSTGRES_PASSWORD`: Kata sandi untuk database.
- `POSTGRES_DB`: Nama database.
- `SECRET_KEY`: Kunci rahasia untuk enkripsi JWT.
- `GCS_BUCKET_NAME`: Nama bucket di Google Cloud Storage untuk menyimpan file.
- `GOOGLE_APPLICATION_CREDENTIALS`: Path ke file JSON kredensial Google Cloud Anda.

**PENTING**: Pastikan file kredensial Google Cloud (misalnya: `service-account.json`) berada di direktori utama proyek agar dapat diakses oleh Docker.

#### 3. Jalankan Aplikasi dengan Docker Compose

Perintah ini akan membangun *image* dan menjalankan kontainer untuk API dan database.

```bash
docker-compose up -d --build
```

#### 4. Jalankan Migrasi Database

Setelah kontainer berjalan, terapkan skema database terbaru menggunakan Alembic.

```bash
docker-compose exec api alembic upgrade head
```

#### 5. Selesai

API sekarang dapat diakses di `http://localhost:8000`.

---

### Cara 2: Menjalankan Secara Lokal (Tanpa Docker)

Metode ini cocok untuk pengembangan di mana Anda ingin menjalankan API langsung di mesin Anda.

#### 1. Clone Repositori dan Konfigurasi Environment

Lakukan langkah 1 dan 2 dari metode Docker di atas.

#### 2. Siapkan Database PostgreSQL

Pastikan Anda memiliki server PostgreSQL yang berjalan di mesin Anda. Catat *host*, *port*, *user*, *password*, dan nama *database*, lalu sesuaikan nilainya di file `.env`.

#### 3. Buat dan Aktifkan Virtual Environment

Sangat disarankan untuk menggunakan *virtual environment* agar dependensi proyek tidak tercampur dengan pustaka Python global.

```bash
python3 -m venv venv
source venv/bin/activate
```

#### 4. Instal Dependensi

Instal semua pustaka Python yang dibutuhkan dari file `requirements.txt`.

```bash
pip install -r requirements.txt
```

#### 5. Jalankan Migrasi Database

Pastikan koneksi database di `.env` sudah benar, lalu jalankan perintah ini dari terminal:

```bash
alembic upgrade head
```

#### 6. Jalankan Aplikasi

Gunakan Uvicorn untuk menjalankan server FastAPI.

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Flag `--reload` akan me-restart server secara otomatis setiap kali ada perubahan pada kode.

#### 7. Selesai

API sekarang dapat diakses di `http://localhost:8000`.

---

## Dokumentasi API

Setelah aplikasi berjalan, Anda dapat mengakses dokumentasi API interaktif yang dibuat secara otomatis oleh FastAPI:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

Melalui halaman dokumentasi tersebut, Anda bisa melihat semua *endpoint* yang tersedia dan mencobanya secara langsung.