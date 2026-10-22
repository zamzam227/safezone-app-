# Safe-Zone App

Platform pelaporan cyberbullying untuk siswa SD: pengaduan aman, nomor referensi, pelacakan status (timeline), jurnal emosi, edukasi, dan dashboard petugas.

## Cara menjalankan (paling mudah)
Butuh **Python 3.9+** saja (https://www.python.org/downloads/, centang "Add Python to PATH" saat instal di Windows). Tidak perlu `pip install`.

- **Windows:** klik dua kali `jalankan.bat`
- **Mac/Linux:** `./jalankan.sh` atau `python3 server.py`

Buka http://localhost:3000. Pada jalan pertama dibuat akun `admin`; kata sandinya dicetak **sekali** di jendela terminal, jadi catat saat itu. Untuk menentukan sendiri: `ADMIN_PASSWORD="..."` sebelum menjalankan.

Buat akun petugas/admin tambahan (Windows: ganti `python3` dengan `python`):
```
python3 server.py add-user bu.sari "Bu Sari (Guru BK)" petugas "kata-sandi-kuat"
```
Siswa mendaftar sendiri lewat halaman Masuk. Uji otomatis: `python3 test_api.py`.

## Konfigurasi (environment)
| Variabel | Fungsi |
|---|---|
| `HOST` | Default `127.0.0.1` (hanya komputer ini). Isi `0.0.0.0` agar bisa diakses dari jaringan sekolah |
| `PORT` | Default 3000 |
| `DATA_DIR` | Lokasi database dan unggahan (default `./data`) |
| `ADMIN_PASSWORD` | Kata sandi admin awal |
| `COOKIE_SECURE=1` | Wajib saat lewat HTTPS |
| `TRUST_PROXY=1` | Pakai `X-Forwarded-For` bila di belakang reverse proxy |

## Peran dan hak akses
- **siswa**: hanya melihat/mengunggah/mengunduh pengaduan dan jurnal miliknya.
- **petugas**: melihat laporan yang belum ditugaskan atau ditugaskan kepadanya; mengambil/melepas laporan, mencatat tindak lanjut, memajukan status laporannya.
- **admin**: melihat semua laporan, menugaskan petugas mana pun, melihat seluruh riwayat aktivitas.
- Status hanya naik satu tahap per aksi petugas dan tercatat. Mulai tahap Tindak Lanjut wajib ada catatan. Catatan internal tidak tampil ke siswa.

## Keamanan yang diterapkan
Kata sandi di-hash scrypt; sesi acak 256-bit (hash disimpan di DB) di cookie HttpOnly + SameSite=Strict; pembatasan percobaan login/pendaftaran; header anti-CSRF pada permintaan ubah data; validasi input; unggahan dicek tipe (magic bytes) dan ukuran, disimpan dengan nama acak, hanya bisa diunduh lewat API dengan pengecekan hak akses; CSP tanpa inline script.

## Sebelum dipakai sungguhan di sekolah
- Pasang di balik HTTPS (Caddy/Nginx) dan set `COOKIE_SECURE=1`. Server ini dibuat sederhana; untuk trafik besar jalankan di belakang reverse proxy.
- Jadwalkan backup folder `data/` (database + unggahan).
- Pendaftaran siswa terbuka; untuk produksi sebaiknya akun dibuat/diverifikasi sekolah.
- Belum ada: pemulihan kata sandi, notifikasi, enkripsi data diam, audit keamanan independen, uji beban.
- Data laporan anak sangat sensitif: tetapkan kebijakan privasi, pihak berwenang, dan masa simpan bersama sekolah.
