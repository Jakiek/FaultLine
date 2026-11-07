# DESIGN — Dashboard Faultline

## 1. Arah visual

Dashboard analitik yang **tenang, editorial, dan mudah dibaca**. Palet hijau zaitun dan lime pucat, judul serif, dan angka besar bergaris tipis. Arah ini berasal dari referensi visual pemilik: panel zaitun dengan kartu lime berangka besar, judul serif dengan daftar bernomor bergaris tipis, serta wordmark serif dengan garis navigasi. Topiknya bencana, jadi hindari gaya dramatis seperti merah menyala, ikon api, atau animasi.

## 2. Prinsip

1. **Setiap grafik menjawab satu pertanyaan.** Nama visual ditulis kecil, lalu pertanyaannya menjadi judul serif, misalnya "Wilayah mana yang paling aktif?".
2. **Sumber dan batasan selalu terlihat.** Footer: "Sumber: USGS Earthquake Catalog · M ≥ 4.0 · Wilayah = pendekatan kotak batas · Bukan informasi darurat." Hero dan sidebar juga menyebut USGS dan "bukan informasi darurat".
3. **Waktu ditampilkan dalam WIB** dengan label "WIB" di setiap kolom waktu. Filter tanggal memakai tanggal UTC sesuai gudang data, dan label filternya menyebut "UTC".
4. **Filter memengaruhi semua visual** kecuali kartu "Run ETL terakhir" dan panel pipeline.
5. **Satu tempat yang berani:** hero (panel zaitun + kartu lime). Bagian lain tetap putih, tenang, dan konsisten.

## 3. Token

### 3.1 Warna

| Nama | Hex | Pemakaian |
|---|---|---|
| Zaitun | `#34401A` | Panel hero, sidebar, teks di atas lime |
| Lime pucat | `#E4F4B5` | Kartu angka hero |
| Lime terang | `#D3EE8C` | Aksen di atas zaitun: tombol reset, chip wilayah, teks kecil hero |
| Daun | `#5E7A22` | Seri utama grafik, warna primer widget |
| Kuning tua | `#B07D12` | Sorotan M ≥ 6 (kontras ≥ 3:1 terhadap putih) |
| Sage | `#C5CFA8` | Seri pembanding, awal skala peta |
| Tinta | `#1E2414` | Teks utama |
| Abu zaitun | `#5F6852` | Teks sekunder, judul sumbu |
| Garis | `#E3E5DA` | Garis tipis dan tepi panel |
| Kertas | `#FBFBF8` / `#FFFFFF` | Latar halaman / panel grafik |

Kedalaman, dibedakan lewat kecerahan, bukan hanya rona: dangkal `#CDE68A` · menengah `#5E7A22` · dalam `#2E3A14`.

Peta: ukuran titik `2^(M−4)` sehingga gempa besar menonjol. Warna memakai skala sage → daun → kuning tua.

### 3.2 Tipografi

| Peran | Font | Catatan |
|---|---|---|
| Judul, wordmark, pertanyaan grafik | Libre Baskerville 400/700 | Wordmark "Faultline" 700; judul lain 400 |
| Teks, label, angka besar | Work Sans 300–600 | Angka kartu memakai 300 dengan `letter-spacing` negatif |

Font dimuat lewat tema Streamlit (`.streamlit/config.toml`) dari Google Fonts, dengan fallback Georgia untuk serif dan Helvetica/Arial untuk sans.

### 3.3 Bentuk

- Panel hero dan pipeline: radius 28px. Kartu lime: 22px. Panel grafik: 24px dengan garis tipis, tanpa bayangan.
- Tombol berbentuk pil.
- Navigasi dan footer dibatasi garis tipis berwarna tinta.

### 3.4 Format angka

- Pemisah ribuan titik (`1.234`), desimal koma (`5,6`), sesuai bahasa Indonesia, termasuk sumbu Plotly (`separators=",."`).
- Magnitudo satu desimal; kedalaman nol desimal + "km".
- Jam memakai titik (`23.30 WIB`).

## 4. Tata letak (satu halaman)

```
┌ Sidebar zaitun ─────┐ ┌ Konten (maks 1240px) ───────────────────────────────┐
│ Saring data          │ │ Faultline (serif)          Tren Peta Wilayah Data Pipeline │
│ Rentang tanggal (UTC)│ │ ───────────────────────────────────────────────────── │
│ Magnitudo minimum    │ │ ┌ Panel zaitun ─────────┐ ┌ Total ┐ ┌ M ≥ 6 ┐        │
│ Wilayah (multi)      │ │ │ judul serif + ringkas │ │ + bar │ │       │        │
│ (Reset filter)       │ │ │ lencana batasan       │ ├ Rata  ┤ ├ Run   ┤        │
│ Info sumber data     │ │ └───────────────────────┘ └ kedal.┘ └ ETL   ┘        │
└──────────────────────┘ │ Tren bulanan (2 panel: semua · M ≥ 6)                │
                         │ Peta titik            │ Distribusi magnitudo        │
                         │ Per wilayah           │ Komposisi kedalaman         │
                         │ Tabel 10 gempa terkuat (WIB)                        │
                         │ Dari USGS ke halaman ini: 01–04 │ panel run terakhir │
                         │ ─ footer sumber & batasan ───────────────────────── │
                         └─────────────────────────────────────────────────────┘
```

Di bawah 900px, hero dan pipeline menjadi satu kolom. Di bawah 480px, kartu lime menjadi satu kolom.

### Visual dan pertanyaannya

| Visual | Pertanyaan | Jenis |
|---|---|---|
| Tren bulanan | Bagaimana jumlah gempa berubah dari waktu ke waktu? | Dua panel berbagi sumbu waktu: semua gempa, lalu M ≥ 6 dengan skala sendiri |
| Peta titik | Di mana gempa-gempa itu terjadi? | Scatter map OpenStreetMap (tanpa token), maks 5.000 gempa terkuat |
| Distribusi magnitudo | Seberapa sering gempa besar dibanding gempa kecil? | Histogram bin 0,5, sumbu log, bin ≥ 6 disorot |
| Per wilayah | Wilayah mana yang paling aktif? | Bar horizontal, diurutkan |
| Kedalaman | Lebih banyak gempa dangkal atau dalam? | Bar 3 kategori |
| 10 gempa terkuat | Gempa mana yang paling kuat pada rentang ini? | Tabel |

### Kartu angka (hero)

| Kartu | Isi | Catatan |
|---|---|---|
| Total gempa | Jumlah sesuai filter + bar mini per tahun | Bar terakhir lebih gelap |
| Gempa M ≥ 6 | Jumlah sesuai filter | Angka berwarna sorotan gelap |
| Rata-rata kedalaman | km | — |
| Run ETL terakhir | Tanggal & jam WIB + jumlah baris ditolak | Tidak terpengaruh filter |

### Panel pipeline

Daftar bernomor 01–04 (Extract, Staging, Transform, Load). Penomoran dipakai karena isinya memang tahap berurutan. Di sebelahnya, panel run terakhir menampilkan baris baru, diperbarui, ditolak, dan diambil.

## 5. State

| State | Tampilan |
|---|---|
| Memuat | `st.spinner("Memuat data…")` per bagian, bukan seluruh halaman |
| Filter tanpa hasil | `st.info` + saran melonggarkan filter |
| Gudang data kosong | `st.info` dengan perintah backfill |
| Database tidak terjangkau | `st.error` dengan pesan manusiawi; detail hanya di log |

## 6. Aksesibilitas

- Warna kedalaman berbeda kecerahan, bukan hanya rona.
- Teks lime di atas zaitun dan teks zaitun di atas lime memenuhi kontras teks.
- Navigasi memakai tautan jangkar dengan garis bawah saat fokus atau hover.
- Bar mini memakai `role="img"`, `aria-label`, dan `<title>` per tahun.
- Setiap grafik punya judul teks; tabel memakai nama kolom bahasa Indonesia yang jelas.
