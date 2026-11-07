"""Dashboard Faultline — streamlit run dashboard/app.py"""

import html
import logging
import sys
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dashboard import queries as q  # noqa: E402
from dashboard.format import angka, desimal, jam_wib, tanggal_pendek_wib, waktu_wib  # noqa: E402

load_dotenv()
log = logging.getLogger(__name__)

# Token warna (DESIGN § 3)
ZAITUN = "#34401A"
UTAMA = "#5E7A22"
SOROTAN = "#B07D12"
PEMBANDING = "#C5CFA8"
TINTA = "#1E2414"
ABU = "#5F6852"
GARIS = "#E3E5DA"
WARNA_KEDALAMAN = {"dangkal": "#CDE68A", "menengah": UTAMA, "dalam": "#2E3A14"}
FONT = "Work Sans, Helvetica Neue, Arial, sans-serif"
BATAS_PETA = 5000
SUMBER = (
    "Sumber: USGS Earthquake Catalog · M ≥ 4.0 · Wilayah = pendekatan kotak batas · "
    "Bukan informasi darurat."
)

st.set_page_config(page_title="Faultline — Analitik Gempa Indonesia", layout="wide")

CSS = """
<style>
  :root {
    --zaitun: #34401A; --lime: #E4F4B5; --lime-terang: #D3EE8C; --tinta: #1E2414;
    --abu: #5F6852; --garis: #E3E5DA; --kertas: #FFFFFF; --sorotan: #B07D12;
    --serif: "Libre Baskerville", Georgia, "Times New Roman", serif;
  }
  [data-testid="stHeader"] { background: transparent; }
  [data-testid="stMainBlockContainer"], .block-container { max-width: 1240px; padding-top: 2.5rem; }

  /* Navigasi: wordmark serif + garis tipis */
  .nav { display:flex; align-items:baseline; justify-content:space-between; gap:1rem; flex-wrap:wrap;
         border-bottom:1px solid var(--tinta); padding-bottom:0.9rem; margin-bottom:1.75rem; }
  .nav .merek { font-family:var(--serif); font-weight:700; font-size:1.65rem; color:var(--tinta); letter-spacing:-0.01em; }
  .nav .tautan { display:flex; gap:1.6rem; flex-wrap:wrap; }
  .nav .tautan a { color:var(--tinta); text-decoration:none; font-size:0.95rem; font-weight:500; }
  .nav .tautan a:hover, .nav .tautan a:focus-visible { text-decoration:underline; text-underline-offset:4px; }

  /* Hero: panel zaitun + empat kartu lime */
  .hero { display:grid; grid-template-columns: 1.08fr 1fr; gap:1rem; margin-bottom:0.75rem; }
  .hero-panel { background:var(--zaitun); color:#EEF3DC; border-radius:28px; padding:2.4rem 2.4rem 2rem;
                display:flex; flex-direction:column; justify-content:space-between; min-height:340px; }
  .hero-panel .kecil { color:var(--lime-terang); font-size:0.95rem; margin:0 0 1.1rem; }
  .hero-panel h1 { font-family:var(--serif); font-weight:400; font-size:clamp(2rem, 3.4vw, 2.9rem);
                   line-height:1.15; letter-spacing:-0.015em; color:#F6F8EC; margin:0 0 1rem; padding:0; }
  .hero-panel p.isi { color:#C9D2B0; font-size:1.02rem; line-height:1.6; max-width:34rem; margin:0; }
  .hero-panel .lencana { display:flex; gap:0.5rem; flex-wrap:wrap; margin-top:1.6rem; }
  .hero-panel .lencana span { border:1px solid #5A6A38; border-radius:999px; padding:0.3rem 0.8rem;
                              font-size:0.82rem; color:#DDE5C4; }
  .ubin-grid { display:grid; grid-template-columns:1fr 1fr; gap:1rem; }
  .ubin { background:var(--lime); border-radius:22px; padding:1.3rem 1.4rem 1.2rem; display:flex;
          flex-direction:column; justify-content:space-between; min-height:162px; color:var(--zaitun); }
  .ubin .angka { font-weight:300; font-size:clamp(2.4rem, 4vw, 3.3rem); line-height:1; letter-spacing:-0.04em; }
  .ubin .angka small { font-size:0.45em; letter-spacing:0; margin-left:0.15em; }
  .ubin .ket { font-size:0.92rem; color:#3E4A22; line-height:1.35; }
  .ubin .ket b { font-weight:600; }
  .ubin.sorot .angka { color:#7A560A; }
  .ubin svg { display:block; width:100%; height:46px; margin:0.4rem 0 0.2rem; }
  .run-strip { color:var(--abu); font-size:0.88rem; margin:0.4rem 0 2.6rem; }

  /* Judul bagian: nama visual kecil + pertanyaan serif */
  .bagian { margin:0.2rem 0 0.9rem; scroll-margin-top:4rem; }
  .bagian .nama { color:var(--abu); font-size:0.9rem; font-weight:500; margin:0 0 0.35rem; }
  .bagian h2 { font-family:var(--serif); font-weight:400; font-size:1.45rem; line-height:1.3;
               color:var(--tinta); margin:0; padding:0; letter-spacing:-0.01em; }
  .catatan-grafik { color:var(--abu); font-size:0.85rem; margin-top:-0.3rem; }

  /* Panel grafik putih bersudut besar */
  [class*="st-key-panel-"] { background:var(--kertas); border:1px solid var(--garis) !important;
                             border-radius:24px !important; padding:1.4rem 1.5rem 1rem !important; }

  /* Pipeline: daftar bernomor + panel run */
  .pipa { display:grid; grid-template-columns: 1.1fr 1fr; gap:2.5rem; margin:3rem 0 1rem; align-items:stretch;
          scroll-margin-top:4rem; }
  .pipa h2 { font-family:var(--serif); font-weight:400; font-size:clamp(1.9rem, 3vw, 2.6rem); line-height:1.15;
             letter-spacing:-0.015em; margin:0 0 1rem; padding:0; color:var(--tinta); }
  .pipa p.isi { color:var(--abu); font-size:1.02rem; line-height:1.6; max-width:36rem; margin:0 0 1.6rem; }
  .pipa ol { list-style:none; margin:0; padding:0; border-top:1px solid var(--garis); }
  .pipa li { display:grid; grid-template-columns:3rem 1fr; padding:1rem 0; border-bottom:1px solid var(--garis);
             color:var(--tinta); line-height:1.5; margin:0; }
  .pipa li .no { color:var(--abu); font-weight:500; }
  .pipa li b { font-weight:600; }
  .panel-run { background:#D9DDB8; border-radius:28px; padding:2rem; display:flex; flex-direction:column;
               justify-content:space-between; color:var(--zaitun); min-height:360px; }
  .panel-run .judul { font-size:0.95rem; color:#4A5528; margin:0; }
  .panel-run .besar { font-family:var(--serif); font-size:clamp(1.6rem, 2.6vw, 2.1rem); line-height:1.2; margin:0.5rem 0 0; }
  .panel-run dl { display:grid; grid-template-columns:1fr 1fr; gap:0.9rem 1.2rem; margin:1.6rem 0 0; }
  .panel-run dt { font-size:0.85rem; color:#4A5528; }
  .panel-run dd { margin:0; font-weight:300; font-size:2.1rem; letter-spacing:-0.03em; line-height:1.1; }
  .panel-run .kaki { font-size:0.88rem; color:#4A5528; margin-top:1.4rem; line-height:1.5; }

  .footer { display:flex; justify-content:space-between; gap:1rem; flex-wrap:wrap; font-size:0.82rem; color:var(--abu);
            border-top:1px solid var(--tinta); padding-top:0.9rem; margin-top:2.5rem; }

  /* Sidebar */
  [data-testid="stSidebar"] h2 { font-family:var(--serif); font-weight:400; }
  [data-testid="stSidebar"] .stButton button { background:var(--lime-terang); color:var(--zaitun); border:none; font-weight:600; }
  [data-testid="stSidebar"] [data-testid="stMultiSelectTagsContainer"] > span,
  [data-testid="stSidebar"] [data-testid="stMultiSelectTagsContainer"] > span * { color:var(--zaitun) !important; fill:var(--zaitun) !important; }
  [data-testid="stSidebar"] .stButton button:hover { background:#E4F4B5; color:var(--zaitun); }

  @media (max-width: 900px) {
    .hero, .pipa { grid-template-columns: 1fr; }
    .hero-panel { min-height:auto; padding:1.8rem; }
  }
  @media (max-width: 480px) {
    .ubin-grid { grid-template-columns: 1fr; }
    .nav .tautan { gap:1rem; }
  }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def tampil_html(isi: str) -> None:
    """Render HTML tanpa indentasi, agar Markdown tidak menganggapnya blok kode."""
    st.markdown("\n".join(b.strip() for b in isi.splitlines() if b.strip()), unsafe_allow_html=True)


def judul_bagian(id_: str, nama: str, pertanyaan: str) -> None:
    st.markdown(
        f'<div class="bagian" id="{id_}"><p class="nama">{nama}</p><h2>{pertanyaan}</h2></div>',
        unsafe_allow_html=True,
    )


def gaya(fig: go.Figure, tinggi: int = 340) -> go.Figure:
    fig.update_layout(
        height=tinggi,
        margin=dict(l=8, r=8, t=8, b=8),
        separators=",.",              # desimal koma, ribuan titik
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=TINTA, size=13),
        hoverlabel=dict(font_family=FONT, bgcolor="#FFFFFF", bordercolor=GARIS),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    fig.update_xaxes(gridcolor="#EEF0E6", linecolor=GARIS, title_font_color=ABU, automargin=True)
    fig.update_yaxes(gridcolor="#EEF0E6", linecolor=GARIS, title_font_color=ABU, automargin=True, tickformat=",d")
    return fig


def grafik(fig: go.Figure, tinggi: int = 340) -> None:
    st.plotly_chart(gaya(fig, tinggi), theme=None, config={"displaylogo": False, "displayModeBar": False})


def batang_mini(tahun: list[int], jumlah: list[int]) -> str:
    """SVG batang per tahun untuk kartu total; nilainya dari query SQL per_tahun."""
    if not jumlah:
        return ""
    maks, lebar, tinggi = max(jumlah), 10, 46
    batang = []
    for i, (t, n) in enumerate(zip(tahun, jumlah)):
        h = max(2, round(n / maks * (tinggi - 4)))
        warna = "#34401A" if i == len(jumlah) - 1 else "#7E9440"
        batang.append(
            f'<rect x="{i * lebar + 1.5}" y="{tinggi - h}" width="{lebar - 3}" height="{h}" rx="1.5" fill="{warna}">'
            f"<title>{t}: {angka(n)} gempa</title></rect>"
        )
    return (
        f'<svg viewBox="0 0 {len(jumlah) * lebar} {tinggi}" preserveAspectRatio="none" role="img" '
        f'aria-label="Jumlah gempa per tahun, {tahun[0]}–{tahun[-1]}">{"".join(batang)}</svg>'
    )


# --- Navigasi ---

st.markdown(
    '<nav class="nav" aria-label="Navigasi halaman"><span class="merek">Faultline</span>'
    '<span class="tautan"><a href="#tren">Tren</a><a href="#peta">Peta</a><a href="#wilayah">Wilayah</a>'
    '<a href="#terkuat">Data</a><a href="#pipeline">Pipeline</a></span></nav>',
    unsafe_allow_html=True,
)

# --- Data awal & sidebar ---

try:
    awal_data, akhir_data = q.rentang_data()
except Exception:
    log.exception("Database tidak terjangkau")
    st.error("Database belum bisa dihubungi. Coba muat ulang halaman beberapa saat lagi.")
    st.stop()

if awal_data is None:
    st.info("Gudang data masih kosong. Jalankan `python -m etl.run --mode backfill --mulai 2016-01-01` terlebih dahulu.")
    st.stop()

BAWAAN = {"rentang": (awal_data, akhir_data), "mag_min": 4.0, "wilayah": list(q.WILAYAH)}
for kunci, nilai in BAWAAN.items():
    st.session_state.setdefault(kunci, nilai)


def reset_filter() -> None:
    for kunci, nilai in BAWAAN.items():
        st.session_state[kunci] = nilai


with st.sidebar:
    st.header("Saring data")
    rentang = st.date_input(
        "Rentang tanggal (UTC)", key="rentang", min_value=awal_data, max_value=akhir_data, format="DD/MM/YYYY"
    )
    st.slider("Magnitudo minimum", 4.0, 8.0, step=0.1, key="mag_min", format="%.1f")
    st.multiselect("Wilayah", q.WILAYAH, key="wilayah", help="Pendekatan kotak batas, bukan batas provinsi.")
    st.button("Reset filter", on_click=reset_filter, width="stretch")
    st.caption(
        "Data: [USGS Earthquake Catalog](https://earthquake.usgs.gov/earthquakes/search/), bukan BMKG. "
        "Diperbarui otomatis setiap hari. Wilayah ditentukan dengan kotak batas lintang/bujur, "
        "jadi gempa di perbatasan bisa masuk wilayah tetangga. **Bukan informasi darurat atau peringatan dini.**"
    )

mulai, akhir = (rentang[0], rentang[-1]) if len(rentang) else (awal_data, akhir_data)
filter_ = q.Filter(mulai, akhir, round(st.session_state.mag_min, 1), tuple(st.session_state.wilayah))

# --- Hero ---

with st.spinner("Memuat data…"):
    ringkas = q.ringkasan(filter_)
    run = q.run_terakhir()
    tahunan = q.per_tahun(filter_)

ada_data = ringkas.total > 0
rata = f'{desimal(ringkas.rata_kedalaman, 0)}<small>km</small>' if ada_data else "–"
if run.empty:
    run_angka, run_ket = "–", "Belum ada run ETL yang sukses."
else:
    r = run.iloc[0]
    run_angka = tanggal_pendek_wib(r.selesai)
    run_ket = (
        f"Run ETL terakhir, {jam_wib(r.selesai)}. "
        f"<b>{angka(r.jumlah_ditolak)} baris ditolak</b> pada run terakhir."
    )

tampil_html(
    f"""
    <section class="hero">
      <div class="hero-panel">
        <div>
          <p class="kecil">Analitik gempa Indonesia</p>
          <h1>Gempa Indonesia sejak 2016, dirangkum dari katalog USGS.</h1>
          <p class="isi">Data diambil setiap pagi, dibersihkan dengan aturan yang tercatat, lalu disimpan
          di gudang data PostgreSQL. Semua angka di halaman ini mengikuti filter di panel kiri.</p>
        </div>
        <div class="lencana"><span>Magnitudo 4,0 ke atas</span><span>Waktu tampil dalam WIB</span>
          <span>Bukan informasi darurat</span></div>
      </div>
      <div class="ubin-grid">
        <div class="ubin">
          <div class="angka">{angka(ringkas.total)}</div>
          {batang_mini(tahunan.tahun.tolist(), tahunan.jumlah.tolist())}
          <div class="ket">gempa tercatat, {mulai:%d/%m/%Y}–{akhir:%d/%m/%Y}</div>
        </div>
        <div class="ubin sorot">
          <div class="angka">{angka(ringkas.jumlah_m6)}</div>
          <div class="ket">gempa bermagnitudo 6 ke atas pada rentang yang sama</div>
        </div>
        <div class="ubin">
          <div class="angka">{rata}</div>
          <div class="ket">rata-rata kedalaman pusat gempa</div>
        </div>
        <div class="ubin">
          <div class="angka" style="font-size:clamp(1.9rem,3vw,2.5rem)">{run_angka}</div>
          <div class="ket">{run_ket}</div>
        </div>
      </div>
    </section>
    """
)

if not ada_data:
    st.info("Tidak ada gempa yang cocok dengan filter. Coba perlebar rentang tanggal, turunkan magnitudo minimum, atau pilih lebih banyak wilayah.")
    st.markdown(f'<div class="footer"><span>{SUMBER}</span></div>', unsafe_allow_html=True)
    st.stop()

st.markdown(
    '<p class="run-strip">Kartu run ETL tidak terpengaruh filter. Rentang tanggal memakai tanggal UTC sesuai '
    "gudang data; waktu kejadian ditampilkan dalam WIB.</p>",
    unsafe_allow_html=True,
)

# --- Tren bulanan ---

with st.container(key="panel-tren"):
    judul_bagian("tren", "Tren bulanan", "Bagaimana jumlah gempa berubah dari waktu ke waktu?")
    with st.spinner("Memuat data…"):
        tren = q.tren_bulanan(filter_)
    # Dua panel berbagi sumbu waktu: jumlah M ≥ 6 (0–5 per bulan) tenggelam bila
    # digambar pada skala yang sama dengan total (ratusan per bulan).
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.08)
    fig.add_bar(x=tren.bulan, y=tren.jumlah, name="Semua gempa", marker_color="#9DB063",
                hovertemplate="%{x|%b %Y}: %{y:,} gempa<extra></extra>", row=1, col=1)
    fig.add_bar(x=tren.bulan, y=tren.jumlah_m6, name="M ≥ 6", marker_color=SOROTAN,
                hovertemplate="%{x|%b %Y}: %{y:,} gempa M ≥ 6<extra></extra>", row=2, col=1)
    fig.update_yaxes(title="Semua gempa", row=1, col=1)
    fig.update_yaxes(title="M ≥ 6", row=2, col=1, rangemode="tozero", dtick=2)
    fig.update_layout(showlegend=False, bargap=0.15)
    grafik(fig, 380)
    st.markdown(
        '<p class="catatan-grafik">Panel bawah memakai skala sendiri agar gempa M ≥ 6 yang jarang tetap terlihat.</p>',
        unsafe_allow_html=True,
    )

# --- Peta & distribusi magnitudo ---

kiri, kanan = st.columns(2, gap="medium")
with kiri, st.container(key="panel-peta"):
    judul_bagian("peta", "Peta titik", "Di mana gempa-gempa itu terjadi?")
    with st.spinner("Memuat data…"):
        titik = q.titik_peta(filter_, BATAS_PETA)
    titik["waktu"] = titik.waktu_utc.map(waktu_wib)
    titik["mag"] = titik.magnitudo.map(desimal)
    # Energi gempa naik ~32× per satu magnitudo; ukuran 2^(M−4) membuat gempa besar
    # menonjol tanpa menutupi ribuan gempa kecil.
    titik["ukuran"] = 2 ** (titik.magnitudo - 4)
    peta = px.scatter_map(
        titik.sort_values("magnitudo"), lat="lintang", lon="bujur", size="ukuran", color="magnitudo",
        color_continuous_scale=[PEMBANDING, UTAMA, SOROTAN], size_max=22, opacity=0.65,
        hover_name="tempat", hover_data={"mag": True, "waktu": True, "kedalaman_km": ":.0f",
                                         "lintang": False, "bujur": False, "magnitudo": False, "ukuran": False},
        labels={"mag": "Magnitudo", "waktu": "Waktu", "kedalaman_km": "Kedalaman (km)", "magnitudo": "M"},
        center={"lat": -2.5, "lon": 118}, zoom=2.55, map_style="open-street-map",
    )
    peta.update_layout(coloraxis_colorbar=dict(
        orientation="h", thickness=8, len=0.5, x=0, xanchor="left", y=-0.04, yanchor="top",
        title=dict(text="Magnitudo", side="top"),
    ))
    grafik(peta, 420)
    if len(titik) == BATAS_PETA:
        st.markdown(
            f'<p class="catatan-grafik">Peta menampilkan {angka(BATAS_PETA)} gempa terkuat sesuai filter agar tetap ringan.</p>',
            unsafe_allow_html=True,
        )

with kanan, st.container(key="panel-magnitudo"):
    judul_bagian("magnitudo", "Distribusi magnitudo", "Seberapa sering gempa besar dibanding gempa kecil?")
    with st.spinner("Memuat data…"):
        dist = q.distribusi_magnitudo(filter_)
    dist["label"] = dist.bin_magnitudo.map(lambda b: f"{desimal(b)}–{desimal(b + 0.4)}")
    fig = go.Figure(go.Bar(
        x=dist.label, y=dist.jumlah,
        marker_color=[SOROTAN if b >= 6 else UTAMA for b in dist.bin_magnitudo],
        hovertemplate="M %{x}: %{y:,} gempa<extra></extra>",
    ))
    fig.update_xaxes(title="Magnitudo (bin 0,5)", type="category", tickangle=-35)
    fig.update_yaxes(title="Jumlah gempa", type="log", dtick=1, tickformat=",d")
    grafik(fig, 420)
    st.markdown(
        '<p class="catatan-grafik">Sumbu tegak memakai skala logaritmik karena gempa kecil jauh lebih banyak. '
        "Batang kuning tua: M ≥ 6.</p>",
        unsafe_allow_html=True,
    )

# --- Per wilayah & kedalaman ---

kiri, kanan = st.columns(2, gap="medium")
with kiri, st.container(key="panel-wilayah"):
    judul_bagian("wilayah", "Per wilayah", "Wilayah mana yang paling aktif?")
    with st.spinner("Memuat data…"):
        wil = q.per_wilayah(filter_)
    fig = go.Figure(go.Bar(
        x=wil.jumlah, y=wil.wilayah, orientation="h", marker_color=UTAMA,
        customdata=wil.magnitudo_maks,
        hovertemplate="%{y}: %{x:,} gempa · M maks %{customdata:.1f}<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title="Jumlah gempa", tickformat=",d")
    grafik(fig)

with kanan, st.container(key="panel-kedalaman"):
    judul_bagian("kedalaman", "Komposisi kedalaman", "Lebih banyak gempa dangkal atau dalam?")
    with st.spinner("Memuat data…"):
        dalam = q.kedalaman(filter_)
    label = {"dangkal": "Dangkal<br>< 70 km", "menengah": "Menengah<br>70–300 km", "dalam": "Dalam<br>> 300 km"}
    fig = go.Figure(go.Bar(
        x=dalam.kelas_kedalaman.map(label), y=dalam.jumlah,
        marker_color=dalam.kelas_kedalaman.map(WARNA_KEDALAMAN),
        marker_line=dict(color=UTAMA, width=[1 if k == "dangkal" else 0 for k in dalam.kelas_kedalaman]),
        hovertemplate="%{x}: %{y:,} gempa<extra></extra>",
    ))
    fig.update_yaxes(title="Jumlah gempa")
    grafik(fig)

# --- Tabel terkuat ---

with st.container(key="panel-terkuat"):
    judul_bagian("terkuat", "10 gempa terkuat", "Gempa mana yang paling kuat pada rentang ini?")
    with st.spinner("Memuat data…"):
        kuat = q.terkuat(filter_)
    st.dataframe(
        {
            "Waktu (WIB)": kuat.waktu_utc.map(waktu_wib),
            "Magnitudo": kuat.magnitudo.map(desimal),
            "Kedalaman (km)": kuat.kedalaman_km.map(lambda x: desimal(x, 0)),
            "Wilayah (pendekatan)": kuat.wilayah,
            "Lokasi menurut USGS": kuat.tempat,
            "ID USGS": kuat.event_id,
        },
        hide_index=True,
    )

# --- Pipeline ---

if run.empty:
    panel_run = '<p class="judul">Belum ada run ETL yang sukses.</p>'
else:
    r = run.iloc[0]
    panel_run = f"""
      <div>
        <p class="judul">Run #{r.run_id}, mode {html.escape(str(r['mode']))}</p>
        <p class="besar">Selesai {tanggal_pendek_wib(r.selesai)}, {jam_wib(r.selesai)}</p>
      </div>
      <dl>
        <div><dt>Baris baru</dt><dd>{angka(r.jumlah_insert)}</dd></div>
        <div><dt>Diperbarui</dt><dd>{angka(r.jumlah_update)}</dd></div>
        <div><dt>Ditolak</dt><dd>{angka(r.jumlah_ditolak)}</dd></div>
        <div><dt>Diambil dari USGS</dt><dd>{angka(r.jumlah_diambil)}</dd></div>
      </dl>
      <p class="kaki">Baris baru 0 pada data yang sudah pernah dimuat berarti run ulang tidak membuat duplikat.</p>
    """

tampil_html(
    f"""
    <section class="pipa" id="pipeline">
      <div>
        <h2>Dari USGS ke halaman ini</h2>
        <p class="isi">Setiap pagi pukul 08.00 WIB, pipeline berjalan otomatis lewat GitHub Actions dengan empat tahap berurutan.</p>
        <ol>
          <li><span class="no">01</span><span><b>Extract.</b> Katalog USGS diambil per jendela waktu, dengan jeda antar-permintaan dan percobaan ulang.</span></li>
          <li><span class="no">02</span><span><b>Staging.</b> Respons mentah disimpan apa adanya dan tidak pernah dihapus, sehingga transform bisa diulang.</span></li>
          <li><span class="no">03</span><span><b>Transform.</b> Waktu dikonversi ke UTC, wilayah ditentukan, dan baris diperiksa dengan aturan kualitas Q1–Q5.</span></li>
          <li><span class="no">04</span><span><b>Load.</b> Upsert berdasarkan ID event: revisi USGS memperbarui baris lama tanpa menggandakannya.</span></li>
        </ol>
      </div>
      <div class="panel-run">{panel_run}</div>
    </section>
    """
)

st.markdown(
    f'<div class="footer"><span>{SUMBER}</span><span>Proyek portofolio Naufal Dzaky</span></div>',
    unsafe_allow_html=True,
)
