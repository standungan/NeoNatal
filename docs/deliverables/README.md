# Dokumen Deliverable — Sistem Monitoring Bayi pada Inkubator

Dokumen yang diserahkan sesuai **Kontrak Pasal 3.1**. Satu folder ini adalah yang
dibaca penerima; berkas sumber dan perkakas pembuatnya tetap di `docs/`.

| Dokumen | Isi | Untuk siapa |
|---|---|---|
| [SRS.md](SRS.md) | Spesifikasi Kebutuhan Perangkat Lunak — kebutuhan fungsional berkode, kebutuhan non-fungsional yang terukur, dan peta deliverable | Pemberi kerja, penguji |
| [UAT_REPORT.md](UAT_REPORT.md) | Laporan pengujian penerimaan: skenario, hasil, dan temuan | Pemberi kerja, penguji |
| [MANUAL.html](MANUAL.html) | Panduan pengguna, disusun per peran — perawat, dokter, admin. Buka di peramban | Petugas bangsal |
| [api.html](api.html) | Referensi API lengkap, dihasilkan dari skema OpenAPI aplikasi. Buka di peramban | Pengembang penerus, integrator |
| [ERD.md](ERD.md) | Entity Relationship Diagram — 16 tabel, kolom, relasi, dan aturan retensi | Pengembang penerus, DBA |
| [Presentasi-Neonatal-Care.pptx](Presentasi-Neonatal-Care.pptx) | Presentasi pengenalan sistem beserta tampilan antarmukanya | Rapat serah terima |

**Panduan pemasangan server** ada di [`DEPLOYMENT.md`](../../DEPLOYMENT.md) pada akar
repositori — letaknya sengaja dipertahankan karena dirujuk oleh `docker-compose.yml`
dan `backend/README.md`.

Deliverable yang berwujud kode, bukan dokumen — source code backend, dashboard web,
aplikasi Android beserta APK-nya, dan firmware IoT — ada di foldernya masing-masing
(`backend/`, `web/`, `frontend/`, `hardware/`). Pemetaan lengkapnya ada di
[SRS §8.2](SRS.md).

## Menghasilkan ulang dokumen

Dua berkas HTML di folder ini dibuat oleh skrip; jangan disunting langsung, karena
perubahannya akan tertimpa pada pembuatan berikutnya.

```bash
python docs/generate_manual_html.py
```

Membaca `docs/MANUAL.md` dan menulis `MANUAL.html` di sini, dengan seluruh gambar
disisipkan ke dalam berkasnya — jadi satu berkas itu bisa dikirim sendirian tanpa
folder gambar.

```bash
python docs/api/generate_api_html.py <folder-skema> docs/deliverables/api.html
```

`<folder-skema>` berisi `openapi.json` dan `roles_full.json` yang diambil dari aplikasi
saat berjalan, jadi pembaruannya perlu backend yang hidup.
