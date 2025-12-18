# Hackfest0x09 First Blood Discord Bot

---

### Intermezzo
Sebuah Discord bot yang memantau platform CTFd untuk **First Blood** pada challenge dan mengumumkannya secara otomatis di channel Discord yang ditentukan.

---

### Persyaratan

Pastikan perangkat lunak berikut sudah terinstal di sistem Anda:

- Python 3.8+
- Discord Bot Token dengan izin untuk menambahkan bot ke server
- CTFd API Key dengan izin membaca data challenge dan solve
- Modul Python:
  - `discord.py`
  - `aiohttp`
  - `python-dotenv`

Periksa instalasi Python dan pip dengan perintah berikut:

```bash
python --version
pip --version
```

---

### Fitur

- Pemantauan Real-time: Mengecek API CTFd setiap beberapa detik untuk menemukan first blood terbaru.
- Pengumuman Otomatis: Mengirim pesan ke Discord ketika first blood ditemukan.
- Penyimpanan Persisten: Menyimpan first blood yang sudah diumumkan ke file CSV agar tidak duplikat.
- Konversi Waktu: Mengubah waktu UTC dari CTFd ke WIB (UTC+7) agar mudah dibaca.
- Debugging: Menampilkan log proses untuk memudahkan troubleshooting.

---

### Konfigurasi

1. Buat Discord Bot di Discord Developer Portal dan dapatkan token.

2. Invite Bot ke Server dengan permission Send Messages.

3. Buat file .env di root project:
```bash
CTFD_API_KEY="ctfd_abcd123..."
CTFD_API_URL="https://ctf.example.com/api/v1/challenges"
DISCORD_CHANNEL_ID=123456789012345678
DISCORD_BOT_TOKEN="YOUR_DISCORD_BOT_TOKEN"
MESSAGE_THUMBNAIL="https://ctf.example.com/files/123abc/image.png"
```

#### Cara Menjalankan

  ```bash
  python main.py
  ```
- Bot akan otomatis mulai mengecek first blood setiap CHECK_INTERVAL detik (default: 5 detik).
- Saat first blood terdeteksi, bot mengirim pesan ke Discord dengan nama challenge, user, dan waktu solve dalam WIB.
