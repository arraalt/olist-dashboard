# Proyek Analisis Data: E-Commerce Public Dataset (Olist)

Proyek ini menganalisis data pesanan marketplace **Olist (Brasil)** pada periode **Januari 2017 - Agustus 2018** dan menyajikannya dalam dashboard interaktif menggunakan **Streamlit**.

## Pertanyaan Bisnis
1. Bagaimana tren jumlah pesanan dan revenue bulanan (pesanan *delivered*), kapan puncaknya, dan berapa pertumbuhan MoM tertinggi?
2. Kategori produk apa yang menjadi 10 besar penyumbang revenue, dan bagaimana rata-rata review score masing-masing?
3. Seberapa besar keterlambatan pengiriman menurunkan review score, dan di state mana persentase terlambat paling tinggi?

Analisis lanjutan: **RFM Analysis** (manual grouping), **Geospatial Analysis** (peta per state dan per kota dari data geolocation, serta jarak penjual-pelanggan), dan **Binning** (kelompok ketepatan pengiriman dan kelompok jarak).

## Struktur Direktori
```
submission
├───dashboard
│   ├───dashboard.py      # kode dashboard Streamlit
│   └───main_data.csv     # data bersih hasil notebook (level item pesanan)
├───data                  # dataset mentah (Olist), termasuk geolocation_dataset.csv
├───notebook.ipynb        # proses analisis lengkap (sudah dijalankan)
├───README.md
├───requirements.txt
└───url.txt               # tautan dashboard di Streamlit Cloud
```

## Setup Environment
Disarankan memakai Python 3.10 atau lebih baru.

**Shell / Terminal (Windows, macOS, Linux)**
```
cd submission
python -m venv .venv
# Windows : .venv\Scripts\activate
# macOS/Linux : source .venv/bin/activate
pip install -r requirements.txt
```

**Anaconda**
```
conda create --name olist-dashboard python=3.11
conda activate olist-dashboard
pip install -r requirements.txt
```

## Menjalankan Dashboard
Jalankan dari folder `submission`:
```
streamlit run dashboard/dashboard.py
```
Dashboard akan terbuka di browser (biasanya `http://localhost:8501`). Gunakan filter rentang tanggal dan state di sidebar. Dashboard hanya membutuhkan `dashboard/main_data.csv`.

## Menjalankan Notebook
Buka `notebook.ipynb` dengan Jupyter/VS Code dari folder `submission` (agar folder `data/` terbaca), lalu jalankan semua sel. Menjalankan notebook akan membuat ulang `dashboard/main_data.csv`.
Jika memakai Google Colab, unggah seluruh berkas CSV ke sesi Colab terlebih dahulu.

## Deploy ke Streamlit Cloud
1. Unggah folder `submission` ke repositori GitHub (pastikan `requirements.txt` ada di root repositori dan `main_data.csv` ikut diunggah).
2. Buka [share.streamlit.io](https://share.streamlit.io), pilih **Create app**, lalu hubungkan repositori.
3. Isi **Main file path** dengan `dashboard/dashboard.py`, lalu klik **Deploy**.
4. Salin tautan aplikasi ke berkas `url.txt`.

## Catatan
- Revenue = total `price` barang (tanpa ongkir) dari pesanan berstatus *delivered*. Nilai uang dalam Real Brasil (R$).
- `geolocation_dataset.csv` dipakai untuk koordinat pelanggan dan penjual (median per kode pos).
- Jarak penjual-pelanggan dihitung dengan rumus haversine (jarak garis lurus), bukan jarak tempuh jalan.
- Peta pada dashboard memakai tile peta dari internet, jadi butuh koneksi internet saat dibuka.