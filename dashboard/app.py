"""Dashboard Faultline — streamlit run dashboard/app.py"""

import logging
import sys
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dashboard import queries as q  # noqa: E402
from dashboard.format import angka, desimal, waktu_wib  # noqa: E402

load_dotenv()
log = logging.getLogger(__name__)

# Token warna (DESIGN § 3.2)
UTAMA = "#1F6F78"
SOROTAN = "#C9741F"
PEMBANDING = "#8FA7B3"
WARNA_KEDALAMAN = {"dangkal": SOROTAN, "menengah": UTAMA, "dalam": "#3B4A5C"}
BATAS_PETA = 5000
SUMBER = (
    "Sumber: USGS Earthquake Catalog · M ≥ 4.0 · Wilayah = pendekatan kotak batas · "
    "Bukan informasi darurat."
)

st.set_page_config(page_title="Faultline — Analitik Gempa Indonesia", layout="wide")
st.markdown(
    """
    <style>
      .kartu { background:#EEECE6; border-radius:8px; padding:0.9rem 1rem; height:100%; }
      .kartu .label { font-size:0.85rem; color:#4A5563; }
      .kartu .nilai { font-size:1.9rem; font-weight:600; line-height:1.2; color:#1C2430; }
      .kartu .nilai.sorotan { color:#9A5413; }
      .kartu .catatan { font-size:0.8rem; color:#4A5563; }
      .footer { font-size:0.8rem; color:#4A5563; border-top:1px solid #D9D6CE; padding-top:0.6rem; margin-top:1.5rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def kartu(label: str, nilai: str, catatan: str = "", sorotan: bool = False) -> None:
    kelas = "nilai sorotan" if sorotan else "nilai"
    st.markdown(
        f'<div class="kartu"><div class="label">{label}</div>'
        f'<div class="{kelas}">{nilai}</div><div class="catatan">{catatan}</div></div>',
        unsafe_allow_html=True,
    )


def gaya(fig: go.Figure, tinggi: int = 340) -> go.Figure:
    fig.update_layout(
        height=tinggi,
        margin=dict(l=8, r=8, t=8, b=8),
        separators=",.",              # desimal koma, ribuan titik
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#1C2430"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    fig.update_xaxes(gridcolor="#E2DFD8")
    fig.update_yaxes(gridcolor="#E2DFD8")
    return fig


def judul_visual(judul: str, pertanyaan: str) -> None:
    st.markdown(f"**{judul}**  \n<span style='color:#4A5563'>{pertanyaan}</span>", unsafe_allow_html=True)


# --- Data awal & sidebar ---

st.title("Faultline — Analitik Gempa Indonesia")
st.write(
    "Gempa bermagnitudo 4,0 ke atas di sekitar Indonesia sejak 2016, diambil setiap hari dari katalog USGS, "
    "dibersihkan, lalu disimpan dalam gudang data PostgreSQL."
)

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
    st.header("Filter")
    rentang = st.date_input(
        "Rentang tanggal (UTC)", key="rentang", min_value=awal_data, max_value=akhir_data, format="DD/MM/YYYY"
    )
    st.slider("Magnitudo minimum", 4.0, 8.0, step=0.1, key="mag_min", format="%.1f")
    st.multiselect("Wilayah", q.WILAYAH, key="wilayah", help="Pendekatan kotak batas, bukan batas provinsi.")
    st.button("Reset filter", on_click=reset_filter, width="stretch")
    st.caption(
        "Data: [USGS Earthquake Catalog](https://earthquake.usgs.gov/earthquakes/search/) (bukan BMKG). "
        "Diperbarui otomatis setiap hari. Wilayah ditentukan dengan kotak batas lintang/bujur, "
        "jadi gempa di perbatasan bisa masuk wilayah tetangga. **Bukan informasi darurat atau peringatan dini.**"
    )

mulai, akhir = (rentang[0], rentang[-1]) if len(rentang) else (awal_data, akhir_data)
filter_ = q.Filter(mulai, akhir, round(st.session_state.mag_min, 1), tuple(st.session_state.wilayah))

# --- Kartu angka ---

with st.spinner("Memuat data…"):
    ringkas = q.ringkasan(filter_)
    run = q.run_terakhir()

k1, k2, k3, k4 = st.columns(4)
with k1:
    kartu("Total gempa", angka(ringkas.total), f"{mulai:%d-%m-%Y} s.d. {akhir:%d-%m-%Y}")
with k2:
    kartu("Gempa M ≥ 6", angka(ringkas.jumlah_m6), "sesuai filter", sorotan=True)
with k3:
    rata = "–" if ringkas.total == 0 else f"{desimal(ringkas.rata_kedalaman, 0)} km"
    kartu("Rata-rata kedalaman", rata, "sesuai filter")
with k4:
    if run.empty:
        kartu("Run ETL terakhir", "–", "belum ada run sukses")
    else:
        r = run.iloc[0]
        kartu(
            "Run ETL terakhir",
            waktu_wib(r.selesai).replace(" WIB", ""),
            f"WIB · {r['mode']} · {angka(r.jumlah_ditolak)} baris ditolak pada run terakhir",
        )

if ringkas.total == 0:
    st.info("Tidak ada gempa yang cocok dengan filter. Coba perlebar rentang tanggal, turunkan magnitudo minimum, atau pilih lebih banyak wilayah.")
    st.markdown(f'<div class="footer">{SUMBER}</div>', unsafe_allow_html=True)
    st.stop()

# --- Tren bulanan ---

st.subheader("Tren bulanan")
judul_visual("Jumlah gempa per bulan", "Bagaimana jumlah gempa berubah dari waktu ke waktu?")
with st.spinner("Memuat data…"):
    tren = q.tren_bulanan(filter_)
fig = go.Figure()
fig.add_bar(x=tren.bulan, y=tren.jumlah, name="Semua gempa", marker_color=PEMBANDING,
            hovertemplate="%{x|%b %Y}: %{y:,} gempa<extra></extra>")
fig.add_scatter(x=tren.bulan, y=tren.jumlah_m6, name="M ≥ 6", mode="lines+markers",
                line=dict(color=SOROTAN, width=2), marker=dict(size=4),
                hovertemplate="%{x|%b %Y}: %{y:,} gempa M ≥ 6<extra></extra>")
fig.update_yaxes(title="Jumlah gempa")
st.plotly_chart(gaya(fig, 320), theme=None, config={"displaylogo": False})

# --- Peta & distribusi magnitudo ---

kiri, kanan = st.columns(2)
with kiri:
    judul_visual("Peta titik gempa", "Di mana gempa-gempa itu terjadi?")
    with st.spinner("Memuat data…"):
        titik = q.titik_peta(filter_, BATAS_PETA)
    titik["waktu"] = titik.waktu_utc.map(waktu_wib)
    titik["mag"] = titik.magnitudo.map(desimal)
    peta = px.scatter_map(
        titik, lat="lintang", lon="bujur", size="magnitudo", color="magnitudo",
        color_continuous_scale=[PEMBANDING, SOROTAN], size_max=14, opacity=0.75,
        hover_name="tempat", hover_data={"mag": True, "waktu": True, "kedalaman_km": ":.0f",
                                         "lintang": False, "bujur": False, "magnitudo": False},
        labels={"mag": "Magnitudo", "waktu": "Waktu", "kedalaman_km": "Kedalaman (km)", "magnitudo": "M"},
        center={"lat": -2.5, "lon": 118}, zoom=3.2, map_style="open-street-map",
    )
    st.plotly_chart(gaya(peta, 420), theme=None, config={"displaylogo": False})
    if len(titik) == BATAS_PETA:
        st.caption(f"Peta menampilkan {angka(BATAS_PETA)} gempa terkuat sesuai filter agar tetap ringan.")

with kanan:
    judul_visual("Distribusi magnitudo", "Seberapa sering gempa besar dibanding gempa kecil?")
    with st.spinner("Memuat data…"):
        dist = q.distribusi_magnitudo(filter_)
    dist["label"] = dist.bin_magnitudo.map(lambda b: f"{desimal(b)}–{desimal(b + 0.4)}")
    fig = go.Figure(go.Bar(
        x=dist.label, y=dist.jumlah,
        marker_color=[SOROTAN if b >= 6 else UTAMA for b in dist.bin_magnitudo],
        hovertemplate="M %{x}: %{y:,} gempa<extra></extra>",
    ))
    fig.update_xaxes(title="Magnitudo (bin 0,5)", type="category")
    fig.update_yaxes(title="Jumlah gempa", type="log")
    st.plotly_chart(gaya(fig, 420), theme=None, config={"displaylogo": False})
    st.caption("Sumbu tegak memakai skala logaritmik karena gempa kecil jauh lebih banyak. Batang jingga: M ≥ 6.")

# --- Per wilayah & kedalaman ---

kiri, kanan = st.columns(2)
with kiri:
    judul_visual("Per wilayah", "Wilayah mana yang paling aktif?")
    with st.spinner("Memuat data…"):
        wil = q.per_wilayah(filter_)
    fig = go.Figure(go.Bar(
        x=wil.jumlah, y=wil.wilayah, orientation="h", marker_color=UTAMA,
        customdata=wil.magnitudo_maks,
        hovertemplate="%{y}: %{x:,} gempa · M maks %{customdata:.1f}<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title="Jumlah gempa")
    st.plotly_chart(gaya(fig), theme=None, config={"displaylogo": False})

with kanan:
    judul_visual("Komposisi kedalaman", "Lebih banyak gempa dangkal atau dalam?")
    with st.spinner("Memuat data…"):
        dalam = q.kedalaman(filter_)
    label = {"dangkal": "Dangkal (< 70 km)", "menengah": "Menengah (70–300 km)", "dalam": "Dalam (> 300 km)"}
    fig = go.Figure(go.Bar(
        x=dalam.kelas_kedalaman.map(label), y=dalam.jumlah,
        marker_color=dalam.kelas_kedalaman.map(WARNA_KEDALAMAN),
        hovertemplate="%{x}: %{y:,} gempa<extra></extra>",
    ))
    fig.update_yaxes(title="Jumlah gempa")
    st.plotly_chart(gaya(fig), theme=None, config={"displaylogo": False})

# --- Tabel terkuat ---

st.subheader("10 gempa terkuat")
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

st.markdown(f'<div class="footer">{SUMBER}</div>', unsafe_allow_html=True)
