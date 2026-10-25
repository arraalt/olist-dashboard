"""Dashboard Analisis E-Commerce (Olist) - Jan 2017 s.d. Agu 2018.

Jalankan dari folder `submission`:
    streamlit run dashboard/dashboard.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# --------------------------------------------------------------------------- konfigurasi
st.set_page_config(page_title="Dashboard E-Commerce Olist", page_icon="📦", layout="wide")

BLUE, ORANGE, GRAY, INK_2 = "#2a78d6", "#eb6834", "#b9b8b2", "#52514e"
DATA_PATH = Path(__file__).parent / "main_data.csv"

BUCKET_BINS = [-np.inf, -8, -1, 0, 3, 7, np.inf]
BUCKET_LABELS = ["Lebih cepat >7 hari", "Lebih cepat 1-7 hari", "Tepat di hari estimasi",
                 "Telat 1-3 hari", "Telat 4-7 hari", "Telat >7 hari"]
JARAK_BINS = [0, 100, 300, 600, 1000, 2000, np.inf]
JARAK_LABELS = ["< 100 km", "100-300 km", "300-600 km", "600-1.000 km", "1.000-2.000 km", "> 2.000 km"]
SEGMEN_URUTAN = ["Repeat Customer", "Big Spender (sekali beli)", "Pelanggan Baru", "Dorman / Berisiko Hilang"]


def fmt_juta(x: float) -> str:
    return f"R$ {x / 1e6:,.2f} jt"


def style(fig: go.Figure, height: int = 380) -> go.Figure:
    """Gaya grafik seragam: latar transparan, grid tipis, tanpa dekorasi berlebih."""
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        title=dict(x=0, xanchor="left", font=dict(size=15)),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1),
        hoverlabel=dict(font_size=12),
    )
    fig.update_xaxes(showline=True, linecolor="#c3c2b7", gridcolor="rgba(150,150,150,0.18)")
    fig.update_yaxes(showline=False, gridcolor="rgba(150,150,150,0.18)")
    return fig


# --------------------------------------------------------------------------- data
@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, parse_dates=["order_purchase_timestamp"])
    df["order_month"] = df["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp()
    df["kategori"] = df["product_category_name_english"].astype(str).str.replace("_", " ", regex=False)
    df["is_late"] = df["is_late"].astype(bool)
    df["delay_bucket"] = pd.cut(df["delay_days"], bins=BUCKET_BINS, labels=BUCKET_LABELS)
    df["jarak_kelompok"] = pd.cut(df["distance_km"], bins=JARAK_BINS, labels=JARAK_LABELS, right=False)
    df["customer_city"] = df["customer_city"].astype(str)
    return df


@st.cache_data
def hitung_pusat_state(df: pd.DataFrame) -> pd.DataFrame:
    """Titik tengah state = median koordinat pelanggan di state tersebut (dari data geolocation)."""
    return (df.dropna(subset=["customer_lat"]).groupby("customer_state")
            .agg(lat=("customer_lat", "median"), lon=("customer_lng", "median")))


def skor_kuantil(s: pd.Series, terbaik_kecil: bool) -> pd.Series:
    """Skor 1-4 berdasarkan kuantil (4 = terbaik)."""
    labels = [4, 3, 2, 1] if terbaik_kecil else [1, 2, 3, 4]
    try:
        return pd.qcut(s, 4, labels=labels).astype(int)
    except ValueError:  # data terlalu sedikit/banyak nilai kembar
        return pd.qcut(s.rank(method="first"), 4, labels=labels).astype(int)


def hitung_rfm(df: pd.DataFrame) -> pd.DataFrame:
    acuan = df["order_purchase_timestamp"].max().normalize() + pd.Timedelta(days=1)
    rfm = (df.groupby("customer_unique_id")
           .agg(last_purchase=("order_purchase_timestamp", "max"),
                frequency=("order_id", "nunique"),
                monetary=("price", "sum"))
           .reset_index())
    rfm["recency"] = (acuan - rfm["last_purchase"].dt.normalize()).dt.days
    rfm["r_score"] = skor_kuantil(rfm["recency"], terbaik_kecil=True)
    rfm["m_score"] = skor_kuantil(rfm["monetary"].rank(method="first"), terbaik_kecil=False)

    def segmen(r):
        if r["frequency"] >= 2:
            return "Repeat Customer"
        if r["m_score"] == 4:
            return "Big Spender (sekali beli)"
        if r["r_score"] >= 3:
            return "Pelanggan Baru"
        return "Dorman / Berisiko Hilang"

    rfm["segmen"] = rfm.apply(segmen, axis=1)
    return rfm


# --------------------------------------------------------------------------- sidebar
data = load_data()
tgl_min, tgl_max = data["order_purchase_timestamp"].min().date(), data["order_purchase_timestamp"].max().date()

with st.sidebar:
    st.title("📦 Filter")
    rentang = st.date_input("Rentang tanggal pembelian", value=(tgl_min, tgl_max),
                            min_value=tgl_min, max_value=tgl_max)
    semua_state = sorted(data["customer_state"].unique())
    pilih_state = st.multiselect("State pelanggan", semua_state, default=semua_state,
                                 help="Kosongkan/pilih sebagian untuk fokus ke wilayah tertentu.")
    st.caption("Sumber data: Brazilian E-Commerce Public Dataset by Olist. "
               "Hanya pesanan berstatus *delivered*, periode Jan 2017 - Agu 2018. Nilai uang dalam Real Brasil (R$).")

if not isinstance(rentang, (tuple, list)) or len(rentang) != 2:
    st.info("Pilih tanggal akhir pada filter rentang tanggal untuk melanjutkan.")
    st.stop()

mulai, akhir = pd.Timestamp(rentang[0]), pd.Timestamp(rentang[1]) + pd.Timedelta(days=1)
df = data[(data["order_purchase_timestamp"] >= mulai) & (data["order_purchase_timestamp"] < akhir)
          & (data["customer_state"].isin(pilih_state))]

st.title("Dashboard Analisis E-Commerce (Olist)")
st.caption(f"Periode: {rentang[0]:%d %b %Y} - {rentang[1]:%d %b %Y} | State terpilih: {len(pilih_state)} dari {len(semua_state)}")

if df.empty:
    st.warning("Tidak ada data untuk filter yang dipilih. Ubah rentang tanggal atau pilihan state.")
    st.stop()

order_df = df.drop_duplicates("order_id")

# --------------------------------------------------------------------------- KPI
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total revenue", fmt_juta(df["price"].sum()))
k2.metric("Jumlah pesanan", f"{order_df['order_id'].nunique():,}")
k3.metric("Pelanggan unik", f"{df['customer_unique_id'].nunique():,}")
k4.metric("Rata-rata review", f"{order_df['review_score'].mean():.2f} / 5")
k5.metric("Pesanan terlambat", f"{order_df['is_late'].mean() * 100:.1f}%")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Tren Penjualan", "🏷️ Kategori Produk", "🚚 Pengiriman & Review", "👥 Segmentasi RFM", "🗺️ Peta Geospasial"])

# --------------------------------------------------------------------------- TAB 1: tren
with tab1:
    st.subheader("Bagaimana tren pesanan dan revenue bulanan?")
    monthly = (df.groupby("order_month")
               .agg(total_orders=("order_id", "nunique"), revenue=("price", "sum"))
               .reset_index())
    monthly["mom_growth_pct"] = monthly["revenue"].pct_change() * 100

    i_rev, i_ord = monthly["revenue"].idxmax(), monthly["total_orders"].idxmax()

    fig = go.Figure(go.Scatter(
        x=monthly["order_month"], y=monthly["revenue"], mode="lines+markers",
        line=dict(color=BLUE, width=2.5), marker=dict(size=7, color=BLUE),
        hovertemplate="%{x|%b %Y}<br>Revenue: R$ %{y:,.0f}<extra></extra>", name="Revenue"))
    fig.add_trace(go.Scatter(
        x=[monthly.loc[i_rev, "order_month"]], y=[monthly.loc[i_rev, "revenue"]], mode="markers+text",
        marker=dict(size=12, color=ORANGE, line=dict(color="white", width=2)),
        text=[f"Puncak: {monthly.loc[i_rev, 'order_month']:%b %Y}<br>{fmt_juta(monthly.loc[i_rev, 'revenue'])}"],
        textposition="middle left", hoverinfo="skip", showlegend=False))
    fig.update_layout(title="Revenue bulanan (R$)", showlegend=False)
    fig.update_yaxes(range=[0, monthly["revenue"].max() * 1.15], tickformat=",.0f")
    st.plotly_chart(style(fig, 360), width="stretch")

    fig = go.Figure(go.Bar(
        x=monthly["order_month"], y=monthly["total_orders"],
        marker_color=[ORANGE if i == i_ord else BLUE for i in monthly.index],
        hovertemplate="%{x|%b %Y}<br>Pesanan: %{y:,}<extra></extra>"))
    fig.update_layout(title="Jumlah pesanan bulanan", showlegend=False)
    fig.update_yaxes(rangemode="tozero")
    st.plotly_chart(style(fig, 320), width="stretch")

    c1, c2, c3 = st.columns(3)
    c1.metric("Bulan revenue tertinggi", f"{monthly.loc[i_rev, 'order_month']:%b %Y}", fmt_juta(monthly.loc[i_rev, "revenue"]))
    if monthly["mom_growth_pct"].notna().any():
        j = monthly["mom_growth_pct"].idxmax()
        c2.metric("Pertumbuhan MoM tertinggi", f"{monthly.loc[j, 'order_month']:%b %Y}", f"{monthly.loc[j, 'mom_growth_pct']:+.1f}%")
        j = monthly["mom_growth_pct"].idxmin()
        c3.metric("Penurunan MoM terdalam", f"{monthly.loc[j, 'order_month']:%b %Y}", f"{monthly.loc[j, 'mom_growth_pct']:+.1f}%")
    st.caption("Catatan: bulan pertama/terakhir bisa belum penuh jika rentang tanggal dipotong di tengah bulan.")
    with st.expander("Lihat tabel data bulanan"):
        tabel = monthly.assign(bulan=monthly["order_month"].dt.strftime("%Y-%m"))[["bulan", "total_orders", "revenue", "mom_growth_pct"]]
        st.dataframe(tabel.round(2), hide_index=True, width="stretch")

# --------------------------------------------------------------------------- TAB 2: kategori
with tab2:
    st.subheader("Kategori produk apa yang menyumbang revenue terbesar, dan bagaimana review-nya?")
    n_top = st.slider("Jumlah kategori teratas", 5, 15, 10)

    cat_rev = (df.groupby("kategori")
               .agg(revenue=("price", "sum"), total_orders=("order_id", "nunique"))
               .reset_index())
    cat_rev_score = (df.dropna(subset=["review_score"])
                     .drop_duplicates(["order_id", "kategori"])
                     .groupby("kategori")["review_score"].agg(avg_review="mean", n_review="count").reset_index())
    cat = cat_rev.merge(cat_rev_score, on="kategori", how="left").sort_values("revenue", ascending=False)
    cat["share_pct"] = cat["revenue"] / cat["revenue"].sum() * 100
    top = cat.head(n_top).iloc[::-1]
    rata_review = order_df["review_score"].mean()

    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, column_widths=[0.58, 0.42], horizontal_spacing=0.03,
                        subplot_titles=("Revenue (R$ juta)", f"Rata-rata review (garis putus = rata-rata {rata_review:.2f})"))
    fig.add_trace(go.Bar(
        x=top["revenue"], y=top["kategori"], orientation="h", marker_color=BLUE,
        text=[f"{v / 1e6:.2f} jt" for v in top["revenue"]], textposition="outside", cliponaxis=False,
        customdata=top[["share_pct", "total_orders"]],
        hovertemplate="<b>%{y}</b><br>Revenue: R$ %{x:,.0f}<br>Kontribusi: %{customdata[0]:.1f}%<br>Pesanan: %{customdata[1]:,}<extra></extra>"),
        row=1, col=1)
    warna = [ORANGE if v < rata_review else BLUE for v in top["avg_review"]]
    fig.add_trace(go.Scatter(
        x=top["avg_review"], y=top["kategori"], mode="markers+text", marker=dict(size=13, color=warna, line=dict(color="white", width=1.5)),
        text=[f"{v:.2f}" for v in top["avg_review"]], textposition="top center",
        hovertemplate="<b>%{y}</b><br>Rata-rata review: %{x:.2f}<extra></extra>"), row=1, col=2)
    fig.add_vline(x=rata_review, line_dash="dash", line_color=GRAY, row=1, col=2)
    fig.update_xaxes(range=[0, top["revenue"].max() * 1.25], row=1, col=1)
    fig.update_xaxes(range=[3.4, 4.7], row=1, col=2)
    fig.update_layout(showlegend=False)
    fig.update_annotations(font_size=13)
    st.plotly_chart(style(fig, 90 + 42 * n_top), width="stretch")
    st.caption("🟠 Oranye = review di bawah rata-rata keseluruhan, 🔵 biru = sama/di atas. Sumbu review dimulai dari 3,4 agar selisih terlihat; batang revenue tetap mulai dari nol.")

    st.metric(f"Kontribusi {n_top} kategori teratas terhadap revenue", f"{cat.head(n_top)['share_pct'].sum():.1f}%")
    with st.expander("Lihat tabel seluruh kategori"):
        st.dataframe(cat.round(2), hide_index=True, width="stretch")

# --------------------------------------------------------------------------- TAB 3: pengiriman
with tab3:
    st.subheader("Seberapa besar keterlambatan menurunkan review, dan di mana paling sering terlambat?")
    ord_rev = order_df.dropna(subset=["review_score"])
    rv_late = ord_rev.groupby("is_late")["review_score"].mean()

    m1, m2, m3 = st.columns(3)
    m1.metric("Review - tepat waktu/lebih cepat", f"{rv_late.get(False, np.nan):.2f}")
    m2.metric("Review - terlambat", f"{rv_late.get(True, np.nan):.2f}")
    if True in rv_late.index and False in rv_late.index:
        m3.metric("Selisih", f"{rv_late[True] - rv_late[False]:+.2f} poin")

    c_left, c_right = st.columns([1.1, 1])
    with c_left:
        rb = (ord_rev.groupby("delay_bucket", observed=True)["review_score"].agg(avg_review="mean", n="count").reset_index())
        fig = go.Figure(go.Bar(
            x=rb["delay_bucket"].astype(str), y=rb["avg_review"],
            marker_color=[ORANGE if str(b).startswith("Telat") else BLUE for b in rb["delay_bucket"]],
            text=[f"{v:.2f}" for v in rb["avg_review"]], textposition="outside", cliponaxis=False,
            customdata=rb["n"], hovertemplate="<b>%{x}</b><br>Rata-rata review: %{y:.2f}<br>Pesanan: %{customdata:,}<extra></extra>"))
        fig.update_layout(title="Review score menurut ketepatan pengiriman", showlegend=False)
        fig.update_yaxes(range=[0, 5.3], title="Rata-rata review (1-5)")
        st.plotly_chart(style(fig, 420), width="stretch")
        st.caption("🔵 Tepat waktu / lebih cepat dari estimasi · 🟠 Terlambat")

    with c_right:
        min_order = st.number_input("Minimal pesanan per state", 1, 2000, 300, step=50,
                                    help="State dengan pesanan sedikit membuat persentase tidak stabil.")
        st_late = (order_df.groupby("customer_state")
                   .agg(total_orders=("order_id", "nunique"), late_rate=("is_late", lambda s: s.mean() * 100),
                        avg_review=("review_score", "mean")).reset_index())
        st_late = st_late[st_late["total_orders"] >= min_order].nlargest(10, "late_rate").iloc[::-1]
        nasional = order_df["is_late"].mean() * 100
        if st_late.empty:
            st.info("Tidak ada state yang memenuhi batas minimal pesanan.")
        else:
            fig = go.Figure(go.Bar(
                x=st_late["late_rate"], y=st_late["customer_state"], orientation="h", marker_color=ORANGE,
                text=[f"{v:.1f}%" for v in st_late["late_rate"]], textposition="outside", cliponaxis=False,
                customdata=st_late[["total_orders", "avg_review"]],
                hovertemplate="<b>%{y}</b><br>Terlambat: %{x:.1f}%<br>Pesanan: %{customdata[0]:,}<br>Rata-rata review: %{customdata[1]:.2f}<extra></extra>"))
            fig.add_vline(x=nasional, line_dash="dash", line_color=INK_2)
            fig.update_layout(title=f"10 state dengan % terlambat tertinggi (garis putus = rata-rata {nasional:.1f}%)", showlegend=False)
            fig.update_xaxes(range=[0, st_late["late_rate"].max() * 1.2], title="% pesanan terlambat")
            st.plotly_chart(style(fig, 380), width="stretch")

    st.markdown("#### Pengaruh jarak penjual-pelanggan")
    jr = df.dropna(subset=["distance_km"])
    if len(jr) < 30:
        st.info("Data terlalu sedikit untuk analisis jarak. Perluas filter.")
    else:
        jk = (jr.groupby("jarak_kelompok", observed=True)
              .agg(jumlah_item=("order_id", "count"), persen_terlambat=("is_late", lambda s: s.mean() * 100),
                   median_hari=("delivery_days", "median")).reset_index())
        fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.1,
                            subplot_titles=("% item terlambat", "Median lama pengiriman (hari)"))
        for col, kolom, fmt in ((1, "persen_terlambat", "{:.1f}%"), (2, "median_hari", "{:.1f}")):
            fig.add_trace(go.Bar(
                x=jk["jarak_kelompok"].astype(str), y=jk[kolom], marker_color=BLUE,
                text=[fmt.format(v) for v in jk[kolom]], textposition="outside", cliponaxis=False,
                customdata=jk["jumlah_item"],
                hovertemplate="<b>%{x}</b><br>%{y:.1f}<br>Item: %{customdata:,}<extra></extra>"), row=1, col=col)
            fig.update_yaxes(range=[0, jk[kolom].max() * 1.2], row=1, col=col)
        fig.update_layout(showlegend=False)
        fig.update_annotations(font_size=13)
        st.plotly_chart(style(fig, 360), width="stretch")
        st.caption("Jarak garis lurus (haversine) dari kode pos penjual ke kode pos pelanggan. Kelompok dengan item sedikit kurang stabil.")

    sama = df.assign(same_state=df["customer_state"] == df["seller_state"])
    ringkas = (sama.groupby("same_state")
               .agg(jumlah_item=("order_id", "count"), median_hari_kirim=("delivery_days", "median"),
                    persen_terlambat=("is_late", lambda s: s.mean() * 100), rata_ongkir=("freight_value", "mean"))
               .rename(index={True: "Satu state", False: "Antar-state"}).round(2))
    with st.expander("Perbandingan pengiriman satu state vs antar-state"):
        st.dataframe(ringkas, width="stretch")

# --------------------------------------------------------------------------- TAB 4: RFM
with tab4:
    st.subheader("Segmentasi pelanggan dengan RFM")
    st.markdown(
        "**Recency** = hari sejak pembelian terakhir, **Frequency** = jumlah pesanan, **Monetary** = total belanja barang. "
        "Skor R dan M dibagi per kuartil (4 = terbaik); karena hampir semua pelanggan hanya membeli sekali, "
        "segmen ditentukan dengan aturan: *Repeat Customer* (F ≥ 2), *Big Spender* (F = 1, skor M = 4), "
        "*Pelanggan Baru* (F = 1, skor R ≥ 3), sisanya *Dorman / Berisiko Hilang*.")

    if df["customer_unique_id"].nunique() < 8:
        st.info("Data terlalu sedikit untuk membuat segmentasi RFM. Perluas filter.")
    else:
        rfm = hitung_rfm(df)
        summ = (rfm.groupby("segmen")
                .agg(jumlah_pelanggan=("customer_unique_id", "count"), avg_recency=("recency", "mean"),
                     avg_frequency=("frequency", "mean"), avg_monetary=("monetary", "mean"), total_monetary=("monetary", "sum"))
                .reindex(SEGMEN_URUTAN).dropna(how="all"))
        summ["persen_pelanggan"] = summ["jumlah_pelanggan"] / summ["jumlah_pelanggan"].sum() * 100
        summ["persen_revenue"] = summ["total_monetary"] / summ["total_monetary"].sum() * 100
        rs = summ.iloc[::-1]

        fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.04,
                            subplot_titles=("% dari seluruh pelanggan", "% dari total revenue"))
        for col, kolom in ((1, "persen_pelanggan"), (2, "persen_revenue")):
            fig.add_trace(go.Bar(
                x=rs[kolom], y=rs.index, orientation="h", marker_color=BLUE,
                text=[f"{v:.1f}%" for v in rs[kolom]], textposition="outside", cliponaxis=False,
                customdata=rs[["jumlah_pelanggan", "avg_monetary", "avg_recency"]],
                hovertemplate="<b>%{y}</b><br>%{x:.1f}%<br>Pelanggan: %{customdata[0]:,}<br>Rata-rata belanja: R$ %{customdata[1]:,.0f}"
                              "<br>Rata-rata recency: %{customdata[2]:.0f} hari<extra></extra>"), row=1, col=col)
            fig.update_xaxes(range=[0, rs[kolom].max() * 1.25], row=1, col=col)
        fig.update_layout(showlegend=False)
        fig.update_annotations(font_size=13)
        st.plotly_chart(style(fig, 360), width="stretch")

        st.dataframe(summ.round(1), width="stretch")
        st.download_button("⬇️ Unduh data RFM per pelanggan (CSV)",
                           rfm.drop(columns=["last_purchase"]).to_csv(index=False).encode("utf-8"),
                           file_name="rfm_pelanggan.csv", mime="text/csv")

# --------------------------------------------------------------------------- TAB 5: peta
with tab5:
    st.subheader("Sebaran revenue dan keterlambatan pengiriman")
    level = st.radio("Level peta", ["State", "Kota"], horizontal=True)
    nasional = order_df["is_late"].mean() * 100
    LABEL_ATAS, LABEL_BAWAH = f"Terlambat > rata-rata ({nasional:.1f}%)", "Terlambat <= rata-rata"

    if level == "State":
        pusat = hitung_pusat_state(data)
        peta = (df.groupby("customer_state").agg(revenue=("price", "sum")).join(
            order_df.groupby("customer_state").agg(
                total_orders=("order_id", "nunique"), late_rate=("is_late", lambda s: s.mean() * 100),
                avg_review=("review_score", "mean"))).join(pusat).reset_index().rename(columns={"customer_state": "nama"}))
    else:
        min_pesanan = st.slider("Minimal pesanan per kota", 10, 1000, 200, step=10,
                                help="Kota dengan pesanan sedikit membuat persentase terlambat tidak stabil.")
        peta = (df.groupby(["customer_city", "customer_state"])
                .agg(revenue=("price", "sum"), total_orders=("order_id", "nunique"),
                     late_rate=("is_late", lambda s: s.mean() * 100), avg_review=("review_score", "mean"),
                     lat=("customer_lat", "median"), lon=("customer_lng", "median"))
                .reset_index())
        peta["nama"] = (peta["customer_city"].str.title().str.replace(" De ", " de ", regex=False)
                        + " (" + peta["customer_state"] + ")")
        peta = peta[peta["total_orders"] >= min_pesanan]

    peta = peta.dropna(subset=["lat", "lon"])
    if peta.empty:
        st.info("Tidak ada lokasi yang memenuhi filter. Turunkan batas minimal pesanan atau perluas filter.")
    else:
        peta["status"] = np.where(peta["late_rate"] > nasional, LABEL_ATAS, LABEL_BAWAH)
        peta["revenue_share"] = peta["revenue"] / df["price"].sum() * 100
        fig = px.scatter_map(
            peta, lat="lat", lon="lon", size="revenue", size_max=48 if level == "State" else 40, color="status",
            color_discrete_map={LABEL_ATAS: ORANGE, LABEL_BAWAH: BLUE},
            hover_name="nama", hover_data={"lat": False, "lon": False, "status": False, "revenue": ":,.0f",
                                           "total_orders": ":,", "late_rate": ":.1f", "avg_review": ":.2f"},
            zoom=3, center=dict(lat=-14.2, lon=-51.9), map_style="carto-positron")
        fig.update_traces(marker=dict(opacity=0.6))
        fig.update_layout(legend=dict(title=None, orientation="h", yanchor="bottom", y=0.01, xanchor="left", x=0.01,
                                      bgcolor="rgba(255,255,255,0.7)", font=dict(color="black")),
                          margin=dict(l=0, r=0, t=0, b=0), height=560)
        st.plotly_chart(fig, width="stretch")
        st.caption("Ukuran lingkaran = revenue; warna oranye = persentase terlambat di atas rata-rata nasional. "
                   "Koordinat berasal dari data geolocation (median koordinat pelanggan per state / per kota).")

        top5 = peta.nlargest(5, "revenue")
        label_top = "state" if level == "State" else "kota"
        st.metric(f"Kontribusi 5 {label_top} teratas terhadap revenue", f"{top5['revenue_share'].sum():.1f}%")
        st.caption("Teratas: " + ", ".join(top5["nama"]))
        with st.expander(f"Lihat tabel per {label_top}"):
            tabel = peta.drop(columns=["lat", "lon", "status"] + (["customer_city", "customer_state"] if level == "Kota" else []))
            st.dataframe(tabel.sort_values("revenue", ascending=False).round(2), hide_index=True, width="stretch")

st.caption("Proyek Analisis Data - Dicoding | Dataset: Brazilian E-Commerce Public Dataset by Olist")
