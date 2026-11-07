# DESIGN — Dashboard Faultline

## 1. Arah visual

Dashboard analitik yang **serius dan mudah dibaca**: latar terang, satu warna aksen, angka besar untuk ringkasan, dan grafik yang masing-masing menjawab satu pertanyaan. Topiknya bencana, jadi hindari gaya dramatis (merah menyala, ikon api, animasi).

## 2. Prinsip

1. **Setiap grafik menjawab satu pertanyaan**, yang ditulis sebagai subjudul (mis. "Wilayah mana yang paling sering mengalami gempa?").
2. **Sumber dan batasan selalu terlihat.** Footer: "Sumber: USGS Earthquake Catalog · M ≥ 4.0 · Wilayah = pendekatan kotak batas · Bukan informasi darurat."
3. **Waktu ditampilkan dalam WIB** dengan label "WIB" di setiap kolom waktu.
4. **Filter memengaruhi semua visual** kecuali kartu "Run ETL terakhir".

## 3. Token

### 3.1 Tema Streamlit — `.streamlit/config.toml`

```toml
[theme]
base = "light"
primaryColor = "#1F6F78"
backgroundColor = "#F7F6F2"
secondaryBackgroundColor = "#EEECE6"
textColor = "#1C2430"
font = "sans serif"
```

### 3.2 Warna grafik

| Pemakaian | Hex |
|---|---|
| Seri utama | `#1F6F78` |
| Sorotan (M ≥ 6, dsb.) | `#C9741F` |
| Seri pembanding | `#8FA7B3` |
| Kedalaman: dangkal / menengah / dalam | `#C9741F` / `#1F6F78` / `#3B4A5C` |

Skala magnitudo di peta: ukuran titik naik dengan magnitudo; warna memakai skala berurutan dari `#8FA7B3` ke `#C9741F`.

### 3.3 Format angka

- Pemisah ribuan titik (`1.234`), desimal koma (`5,6`) — sesuai bahasa Indonesia.
- Magnitudo satu desimal, kedalaman nol desimal + "km".

## 4. Tata letak (satu halaman)

```
┌ Sidebar ─────────────┐ ┌ Konten ─────────────────────────────────────────┐
│ Rentang tanggal      │ │ Judul + 1 kalimat penjelasan                     │
│ Magnitudo minimum    │ │ [Total gempa] [Gempa M≥6] [Rata kedalaman] [Run] │
│ Wilayah (multi)      │ │ Tren bulanan (garis/bar, M≥6 disorot)           │
│ Tombol reset         │ │ Peta titik          │ Distribusi magnitudo        │
│ Info sumber data     │ │ Per wilayah (bar)   │ Komposisi kedalaman (bar)   │
└──────────────────────┘ │ Tabel 10 gempa terkuat (WIB)                     │
                         │ Footer sumber & batasan                          │
                         └──────────────────────────────────────────────────┘
```

### Visual dan pertanyaannya

| Visual | Pertanyaan | Jenis |
|---|---|---|
| Tren bulanan | Bagaimana jumlah gempa berubah dari waktu ke waktu? | Bar bulanan + garis M ≥ 6 |
| Peta titik | Di mana gempa-gempa itu terjadi? | Scatter map, gaya OpenStreetMap (tanpa token) |
| Distribusi magnitudo | Seberapa sering gempa besar dibanding gempa kecil? | Histogram bin 0,5 |
| Per wilayah | Wilayah mana yang paling aktif? | Bar horizontal, diurutkan |
| Kedalaman | Lebih banyak gempa dangkal atau dalam? | Bar 3 kategori |

### Kartu angka

| Kartu | Isi | Catatan |
|---|---|---|
| Total gempa | Jumlah sesuai filter | — |
| Gempa M ≥ 6 | Jumlah sesuai filter | Warna sorotan |
| Rata-rata kedalaman | km | — |
| Run ETL terakhir | Waktu WIB + jumlah baris ditolak | Tidak terpengaruh filter |

## 5. State

| State | Tampilan |
|---|---|
| Memuat | `st.spinner("Memuat data…")` per bagian, bukan seluruh halaman |
| Filter tanpa hasil | `st.info` + saran melonggarkan filter |
| Database tidak terjangkau | `st.error` dengan pesan manusiawi; detail hanya di log |

## 6. Aksesibilitas

- Warna kedalaman berbeda kecerahan, bukan hanya rona, agar tetap terbaca bagi buta warna.
- Setiap grafik punya judul teks; tabel memakai nama kolom bahasa Indonesia yang jelas.
