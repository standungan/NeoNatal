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
| [ERD.svg](ERD.svg) | Diagram-diagram dari ERD.md dalam satu gambar — untuk dicetak, atau dibuka tanpa perender Mermaid | Pengembang penerus, DBA |
| [Presentasi-Neonatal-Care.pptx](Presentasi-Neonatal-Care.pptx) | Presentasi pengenalan sistem beserta tampilan antarmukanya | Rapat serah terima |
| [pdf/](pdf/) | Keenam dokumen di atas dalam bentuk PDF A4 — untuk dicetak, ditandatangani, atau diarsipkan | Semua penerima |

**Panduan pemasangan server** ada di [`DEPLOYMENT.md`](../../DEPLOYMENT.md) pada akar
repositori — letaknya sengaja dipertahankan karena dirujuk oleh `docker-compose.yml`
dan `backend/README.md`.

Deliverable yang berwujud kode, bukan dokumen — source code backend, dashboard web,
aplikasi Android beserta APK-nya, dan firmware IoT — ada di foldernya masing-masing
(`backend/`, `web/`, `frontend/`, `hardware/`). Pemetaan lengkapnya ada di
[SRS §8.2](SRS.md).

## Menghasilkan ulang dokumen

Sebagian berkas di folder ini dibuat oleh skrip — `MANUAL.html`, `api.html`, `ERD.svg`, dan
seluruh isi `pdf/`; jangan disunting langsung, karena perubahannya akan tertimpa pada
pembuatan berikutnya.

```bash
python docs/generate_manual_html.py
```

Membaca `docs/MANUAL.md` dan menulis `MANUAL.html` di sini, dengan seluruh gambar
disisipkan ke dalam berkasnya — jadi satu berkas itu bisa dikirim sendirian tanpa
folder gambar.

```bash
python docs/api/dump_api_inputs.py <folder-skema>
python docs/api/generate_api_html.py <folder-skema> docs/deliverables/api.html
```

Langkah pertama menulis `openapi.json` dan `roles_full.json` ke `<folder-skema>` (folder
sementara mana pun) dengan mengimpor aplikasi langsung — tidak perlu backend yang hidup.
Peran tiap endpoint dibaca dari penjaga rute yang sebenarnya ditegakkan server, bukan
ditulis tangan. Jalankan dengan Python dari `backend/venv`, karena skripnya mengimpor
aplikasi.

```bash
python docs/generate_erd_svg.py
```

Membaca blok Mermaid di `ERD.md` pada folder ini dan menulis `ERD.svg` di sampingnya —
kelima diagram dalam satu gambar, dengan label berupa teks SVG biasa sehingga tetap utuh
bila dicetak atau dibuka di Inkscape. Perlu Chrome dan mermaid-cli
(`npm install -g @mermaid-js/mermaid-cli`); bila mermaid-cli belum terpasang, skrip
memakai `npx` dan mengunduhnya sekali. Lengkung garis relasi sedikit berbeda di setiap
pembuatan, jadi selisih kecil pada berkasnya wajar walau `ERD.md` tidak berubah.

```bash
python docs/generate_pdfs.py            # keenam dokumen
python docs/generate_pdfs.py SRS ERD    # sebagian saja
```

Menulis PDF A4 bernomor halaman ke `pdf/`, lalu **memeriksa setiap halamannya**: judul yang
tertinggal di dasar halaman, halaman yang nyaris kosong, teks yang menyentuh tepi, dan
diagram yang teksnya lebih kecil dari 7 pt. Skrip keluar dengan kode gagal bila ada yang
tidak lolos, jadi PDF yang tata letaknya rusak tidak lolos tanpa ketahuan. Diagram yang
terlalu tinggi dipotong di celah antar-tabel menjadi beberapa halaman, dan yang terlalu
lebar diberi halaman lanskap. Perlu `pip install mistune pypdfium2`, ditambah Chrome dan
mermaid-cli seperti di atas; presentasi diekspor lewat PowerPoint.
