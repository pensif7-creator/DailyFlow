# DailyFlow — Paket Upload Mudah

Paket ini disederhanakan agar lebih mudah diunggah melalui GitHub dari HP. Seluruh antarmuka HTML, CSS, dan JavaScript berada di satu file `index.html`; backend tetap Python Flask.

## Publikasikan sebagai web publik

1. Ekstrak ZIP ini. Pastikan `app.py`, `index.html`, `requirements.txt`, `render.yaml`, `Procfile`, dan `.gitignore` terlihat langsung di folder hasil ekstraksi.
2. Buat repositori baru di GitHub.
3. Pilih **Add file → Upload files**, pilih file-file tadi (jangan unggah ZIP-nya), lalu commit ke branch `main`.
4. Buka Render Dashboard, pilih **New → Blueprint**, hubungkan repositori, pastikan Blueprint Path adalah `render.yaml`, lalu deploy.
5. Setelah deploy berhasil, buka alamat `https://...onrender.com` yang tercantum di halaman service.

## Konfigurasi

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Health check: `/health`

`render.yaml` sudah berisi pengaturan tersebut.

## Data

Jadwal, pengeluaran, profil, dan anggaran disimpan di localStorage browser. Data tidak otomatis tersinkron antarperangkat. Ekspor cadangan JSON secara berkala. Jangan simpan informasi yang sangat sensitif.
