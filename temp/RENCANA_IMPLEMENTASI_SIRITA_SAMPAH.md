# 📘 RENCANA STRATEGIS DAN ARSITEKTUR IMPLEMENTASI
# MODUL SIRITA SAMPAH (ODOO 20 BACKEND)
**Sistem Informasi Pengelolaan Bank Sampah Terintegrasi Kampus Hijau IAIN Parepare**

---

## 1. 🎯 Latar Belakang & Tujuan Strategis

Saat ini, aplikasi Bank Sampah IAIN Parepare beroperasi dengan arsitektur terpisah (*siloed system*):
* **Frontend**: Flutter Multiplatform (PWA & Android Mobile).
* **Backend**: Skrip PHP 8.3 native berbasis Apache di container `bank_sampah_backend`.
* **Basis Data**: MariaDB 11.4 di container `bank_sampah_db`.

Sementara itu, IAIN Parepare telah memiliki ekosistem **SIRITA** (*Sistem Informasi Terintegrasi IAIN Parepare*) berbasis **Odoo 20** yang berjalan aktif di container `app_my_odoo:20-nlp` dan basis data PostgreSQL `app_my_postgres`.

### Tujuan Migrasi ke Odoo 20 (`sirita_sampah`):
1. **Unifikasi Ekosistem Kampus Hijau (*Green Campus ERP*)**: Menyatukan tata kelola Bank Sampah ke dalam tata kelola institusi induk IAIN Parepare.
2. **Integrasi Data Civitas (Single Identity)**: Nasabah bank sampah otomatis terhubung dengan data Mahasiswa (NIM), Dosen, dan Tenaga Kependidikan (NIP) yang ada di SIRITA.
3. **Modernisasi Akuntansi & Saldo Poin**: Saldo poin nasabah dapat dikelola sebagai virtual wallet yang terhubung dengan pos keuangan/pembayaran kampus (misal: pengurangan tagihan Ma'had Al-Jami'ah atau voucher kantin/merchandise).
4. **Efisiensi Sumber Daya Server**: Mengeliminasi kebutuhan container MariaDB dan PHP Apache mandiri, sehingga menghemat konsumsi RAM server sekitar 1.2 GB – 1.5 GB.

---

## 2. 🏛️ Arsitektur Sistem Hybrid Modern

```
+-----------------------------------------------------------------------------------+
|                            PENGGUNA & CLIENT LAYER                                |
|                                                                                   |
|  [ HP Mahasiswa / Nasabah ]              [ HP Petugas Lapangan ]                  |
|   Flutter PWA / Android APK               Flutter PWA / Android APK               |
|   (Katalog, Setor, Saldo)                 (Jemput, Timbang, Scan)                 |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          | HTTPS JSON REST API
                                          v
+-----------------------------------------------------------------------------------+
|                          GATEWAY & REVERSE PROXY LAYER                            |
|                                                                                   |
|                   Nginx Reverse Proxy (nginx-proxy / SSL Wildcard)                |
|                   Domain: https://banksampah.iainpare.ac.id                       |
|                                                                                   |
|       Routing Rule:                                                               |
|       - /                     ==> Web Frontend PWA (Nginx)                        |
|       - /bank_sampah_api/     ==> Odoo 20 REST Controller (app_my_odoo:8069)      |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                         BACKEND & BUSINESS LOGIC LAYER                            |
|                                                                                   |
|                     Odoo 20 Ecosystem (Container: app_my_odoo)                    |
|                        Modul Kustom: sirita_sampah                                |
|                                                                                   |
|  [ API Controller ]    [ Model Transaksi & Poin ]   [ Integrasi Ekosistem SIRITA ]|
|  - Auth JWT / Token    - Penimbangan & Kategori      - sirita_mahad (Potong Iuran)|
|  - Endpoint PWA        - Penugasan Kurir Lapangan    - res.partner (Data Mahasiswa)|
|  - Upload Foto Bukti   - Penarikan Saldo Rupiah      - mail.thread (Audit Chatter)|
|                        - Drop Points GPS             - Stock/Inventory (Pengepul) |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                              PERSISTENCE DATA LAYER                               |
|                                                                                   |
|                     PostgreSQL 16 (Container: app_my_postgres)                     |
+-----------------------------------------------------------------------------------+
```

---

## 3. 📂 Spesifikasi Struktur Direktori Modul `sirita_sampah`

Direktori modul akan berlokasi di:
`/home/iain/app-my/addons/sirita_sampah/`

```text
sirita_sampah/
├── __init__.py
├── __manifest__.py
├── controllers/
│   ├── __init__.py
│   ├── api_auth.py           # Endpoint Otentikasi & Registrasi
│   ├── api_master.py         # Endpoint Kategori Sampah & Drop Points
│   ├── api_transaction.py    # Endpoint Setor, Timbang, & Upload Bukti
│   └── api_withdrawal.py     # Endpoint Tarik Saldo & History
├── models/
│   ├── __init__.py
│   ├── res_partner.py        # Ekstensi Nasabah/Petugas & Saldo Poin
│   ├── sampah_category.py    # Kategori Sampah, Harga Beli, Poin per Kg
│   ├── sampah_transaction.py # Header & Lines Transaksi Sampah
│   ├── sampah_pickup_task.py # Penugasan Jemput Sampah Lapangan
│   ├── sampah_withdrawal.py  # Pengajuan Tarik Saldo Poin ke Rupiah
│   ├── sampah_drop_point.py  # Titik Drop Box / Lokasi GPS Kampus
│   └── system_config.py      # Pengaturan Rasio Poin, Min Weight, dll
├── security/
│   ├── security_groups.xml   # Grup Hak Akses (Nasabah, Petugas, Manager)
│   └── ir.model.access.csv   # Hak Akses Model Odoo
├── views/
│   ├── menu_views.xml        # Menu Induk Bank Sampah di Odoo Web
│   ├── category_views.xml    # Form/List Master Kategori Sampah
│   ├── transaction_views.xml # Form/Kanban/Pivot Transaksi Penimbangan
│   ├── pickup_views.xml      # Kalender & Kanban Penugasan Kurir
│   ├── withdrawal_views.xml  # Verifikasi Penarikan Saldo
│   ├── drop_point_views.xml  # Peta & Daftar Titik Pengumpulan
│   └── partner_views.xml     # Tab Khusus Bank Sampah di Profil Civitas
├── data/
│   ├── default_categories.xml # Inisialisasi Master Data Sampah
│   └── sequence_data.xml      # Penomoran Otomatis (TRX/2026/0001)
├── static/
│   └── description/
│       ├── icon.png          # Logo Bank Sampah (Celengan Hijau)
│       └── index.html
└── temp/
    └── RENCANA_IMPLEMENTASI_SIRITA_SAMPAH.md
```

---

## 4. 🗄️ Pemetaan Model Data (Data Schema Mapping)

### A. Nasabah & Petugas (`res.partner`)
Menggunakan model bawaan Odoo `res.partner` dengan *inheritance*:
* `is_nasabah_sampah`: Boolean
* `is_petugas_sampah`: Boolean
* `nasabah_code`: Char (misal `NSB-2026-001` atau NIM/NIP)
* `point_balance`: Float (Total saldo poin aktif)
* `rupiah_balance`: Float (Konversi saldo rupiah)
* `default_setor_method`: Selection (`drop_in`, `jemput`)
* `nasabah_address`: Text
* `latitude` / `longitude`: Float (koordinat rumah/lokasi jemput)

### B. Master Kategori Sampah (`sirita.sampah.category`)
* `name`: Char (Plastik Botol, Kardus, Kertas HVS, Kaleng Logam, dll)
* `code`: Char
* `price_per_kg`: Float (Harga beli dalam Rupiah per kg)
* `point_per_kg`: Float (Poin yang diperoleh per kg)
* `unit_id`: Many2one (`uom.uom`, default: kg)
* `icon_image`: Binary (Icon jenis sampah)
* `is_active`: Boolean
* `description`: Text

### C. Transaksi Penimbangan (`sirita.sampah.transaction`)
* `name`: Char (No Transaksi: `TRX/YYYY/MM/XXXX`)
* `partner_id`: Many2one (`res.partner`, Nasabah)
* `collector_id`: Many2one (`res.partner`, Petugas/Kurir penimbang)
* `date`: Datetime
* `transaction_type`: Selection (`drop_in`, `pickup`)
* `drop_point_id`: Many2one (`sirita.sampah.drop.point`, opsional)
* `state`: Selection (`draft`, `weighed`, `confirmed`, `done`, `cancelled`)
* `line_ids`: One2many (`sirita.sampah.transaction.line`)
  * `category_id`: Many2one
  * `weight`: Float (Berat dalam kg)
  * `point_earned`: Float (Kalkulasi otomatis)
  * `subtotal_rp`: Float (Kalkulasi otomatis)
* `total_weight`: Float (Computed)
* `total_points`: Float (Computed)
* `total_amount_rp`: Float (Computed)
* `photo_proof`: Binary (Foto bukti sampah / timbangan)
* `pickup_latitude` / `pickup_longitude`: Float

### D. Penarikan Saldo Poin (`sirita.sampah.withdrawal`)
* `name`: Char (No Penarikan: `WD/YYYY/MM/XXXX`)
* `partner_id`: Many2one (`res.partner`)
* `date`: Datetime
* `points_redeemed`: Float
* `amount_rp`: Float
* `payout_method`: Selection (`cash`, `bank_transfer`, `potong_mahad`, `voucher_kantin`)
* `bank_account_name`: Char
* `bank_account_number`: Char
* `state`: Selection (`submitted`, `approved`, `transferred`, `rejected`)
* `approved_by`: Many2one (`res.users`)
* `transfer_proof`: Binary

---

## 5. 🔌 Kompatibilitas REST API dengan Frontend Flutter PWA

Untuk memastikan aplikasi **Flutter PWA yang sudah berjalan di HP tidak mengalami error**, Controller di Odoo 20 akan mereplikasi struktur JSON lama dari `bank_sampah_api`:

| Endpoint PHP Lama | Controller Odoo Baru | Deskripsi |
| :--- | :--- | :--- |
| `POST /auth/login.php` | `POST /bank_sampah_api/auth/login` | Login nasabah/petugas, return JWT token & profil |
| `GET /waste_categories/index.php` | `GET /bank_sampah_api/waste_categories/` | List kategori sampah aktif & poin per kg |
| `GET /transactions/index.php` | `GET /bank_sampah_api/transactions/` | Riwayat setor sampah (filter per nasabah) |
| `POST /transactions/index.php` | `POST /bank_sampah_api/transactions/` | Simpan setor sampah (berat, kategori, poin) |
| `POST /transactions/upload_photo.php` | `POST /bank_sampah_api/transactions/upload_photo` | Upload foto bukti timbangan |
| `GET /withdrawals/index.php` | `GET /bank_sampah_api/withdrawals/` | List pengajuan tarik saldo |
| `POST /withdrawals/index.php` | `POST /bank_sampah_api/withdrawals/` | Buat permohonan penarikan saldo poin |
| `GET /drop_points/index.php` | `GET /bank_sampah_api/drop_points/` | Titik koordinat GPS drop box kampus |
| `GET /dashboard/stats.php` | `GET /bank_sampah_api/dashboard/stats` | Ringkasan kg sampah & total poin nasabah |

Format Response Standar (Zero Breaking Changes):
```json
{
  "success": true,
  "message": "Operasi berhasil",
  "data": { ... }
}
```

---

## 6. 🚀 Rencana Eksekusi Bertahap (5 Milestones)

### 🔹 Milestone 1: Fondasi Modul & Manifest
* Buat direktori dan berkas deklarasi `__manifest__.py` di `/home/iain/app-my/addons/sirita_sampah/`.
* Pasang icon celengan daur ulang hijau di `static/description/icon.png`.
* Definisikan hak akses dasar (`ir.model.access.csv`) dan grup pengguna Odoo.

### 🔹 Milestone 2: ORM Data Models & Views Back-Office
* Implementasikan seluruh kelas model Python di `models/`.
* Buat tampilan UI Odoo Web (Form, Tree/List, Kanban timbangan sampah, grafik analitik sampah per fakultas/gedung).
* Uji coba instalasi modul di Odoo 20 via antarmuka Apps (`app_my_odoo`).

### 🔹 Milestone 3: REST API Controllers
* Tulis `controllers/` Odoo dengan routing `@http.route(..., type='http', auth='public', csrf=False)`.
* Implementasikan otentikasi token yang cocok dengan [lib/api_service.dart](file:///home/iain/app-sampah/lib/api_service.dart).
* Verifikasi komunikasi antara Flutter PWA di HP dengan endpoint Odoo API.

### 🔹 Milestone 4: Migrasi Data Eksisting (MariaDB ➡️ PostgreSQL)
* Ekspor data tabel `users`, `waste_categories`, `transactions`, dan `drop_points` dari MariaDB `bank_sampah`.
* Jalankan skrip ETL transformasi untuk menyuntikkan data historis ke tabel `sirita_sampah_*` di PostgreSQL Odoo.
* Verifikasi integritas saldo poin nasabah.

### 🔹 Milestone 5: Switching Routing & Decommissioning
* Perbarui Nginx proxy (`/home/iain/nginx/conf.d/banksampah.conf`) untuk mengarahkan `/bank_sampah_api/` langsung ke `app_my_odoo:8069`.
* Nonaktifkan container `bank_sampah_backend` dan `bank_sampah_db`.
* Monitoring performa dan stabilitas PWA & Odoo.

---

## 7. 💡 Nilai Tambah Enterprise untuk Kampus IAIN Parepare

1. **Dashboard Pimpinan Terpadu (Green Metrics)**:
   Rektor dan Wakil Rektor Bidang Administrasi Umum & Keuangan (AUPK) dapat memantau indikator keberlanjutan kampus (*UI GreenMetric World University Rankings*) secara real-time:
   * Total tonase sampah terdaur ulang.
   * Estimasi reduksi emisi karbon (CO2 reduction).
   * Nilai ekonomis sampah terkelola.
2. **Koneksi Pembayaran Ma'had Al-Jami'ah**:
   Mahasiswa yang aktif memilah sampah dan mengumpulkan poin dapat mengajukan konversi poin untuk memotong tagihan asrama Ma'had Al-Jami'ah langsung di modul `sirita_mahad`.
3. **Akuntabilitas Finansial BLU**:
   Setiap transaksi penjualan sampah ke pihak ketiga/pengepul tercatat dengan dokumen *Sales Order* dan faktur resmi Odoo yang transparan dan dapat diaudit.
