"""Comparativa: TDA (homología persistente) vs. clustering clásico (K-Means / DBSCAN)."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import folium
from streamlit_folium import st_folium
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import silhouette_score

from utils.data_loader import NIVEL_COLOR, load_escuelas, load_tda
from utils.filters import filter_df, render_global_filters, tda_key
from utils.tda import top_h1_with_cocycles
from utils.plotting import base_map, utm_to_latlon

st.set_page_config(page_title="TDA vs Clustering", page_icon=None, layout="wide")

PLOTLY_CONFIG = {
    "scrollZoom": True, "displayModeBar": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    "displaylogo": False,
}
LAYOUT_BASE = dict(
    plot_bgcolor="#FAFAFA", paper_bgcolor="white",
    font=dict(family="Arial", size=12, color="#1a1a2e"),
    margin=dict(l=10, r=10, t=50, b=10),
)
PALETTE_HEX = [
    "#1B4F72","#2E86C1","#117A65","#1E8449","#6C3483",
    "#935116","#7D6608","#922B21","#1A5276","#0E6655",
    "#4D5656","#212F3C","#145A32","#6E2F1A","#4A235A",
]
HOLE_COLORS = ["#C0392B","#E67E22","#1A5276","#117A65","#6C3483",
               "#7D6608","#2E86C1","#935116","#1E8449","#922B21"]

# ── Sidebar ───────────────────────────────────────────────────────────────────
niveles, sectores = render_global_filters()
with st.sidebar:
    max_pts     = st.slider("Puntos en mapa", 200, 1000, 500, 50,
                            help="Mismo valor para los tres métodos.")
    st.subheader("K-Means")
    k           = st.slider("Número de clústeres (k)", 2, 20, 8)
    st.subheader("DBSCAN")
    eps_db      = st.slider("Radio ε DBSCAN (m)", 200, 3000, 800, 100)
    min_samples = st.slider("Mínimo de puntos", 2, 30, 5)
    st.subheader("TDA")
    top_k       = st.slider("Huecos H₁ a mostrar", 1, 10, 5)

# ── Encabezado ────────────────────────────────────────────────────────────────
st.title("TDA vs. Clustering Clásico")
st.markdown(
    "El clustering clásico identifica **dónde están** los grupos. "
    "La homología persistente detecta **dónde faltan** — los huecos de cobertura "
    "invisibles para K-Means y DBSCAN."
)

# ── Datos ─────────────────────────────────────────────────────────────────────
df  = load_escuelas()
sub = filter_df(df, niveles, sectores)
if len(sub) < 10:
    st.error("Muy pocos puntos. Ajusta los filtros.")
    st.stop()

np.random.seed(42)
idx    = np.random.choice(len(sub), min(max_pts, len(sub)), replace=False)
sample = sub.iloc[idx].reset_index(drop=True)
X      = sample[["x_utm", "y_utm"]].values
n      = len(X)
st.caption(f"Muestra: **{n:,}** escuelas de un total de {len(sub):,}")

# ── Cálculos ──────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def run_kmeans(X_bytes, k):
    X  = np.frombuffer(X_bytes, dtype=np.float64).reshape(-1, 2)
    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
    sil = silhouette_score(X, km.labels_) if len(set(km.labels_)) > 1 else 0.0
    return km.labels_, km.cluster_centers_, float(sil)

@st.cache_data(show_spinner=False)
def run_dbscan(X_bytes, eps, min_s):
    X  = np.frombuffer(X_bytes, dtype=np.float64).reshape(-1, 2)
    db = DBSCAN(eps=eps, min_samples=min_s).fit(X)
    lbls = db.labels_
    nc   = len(set(lbls)) - (1 if -1 in lbls else 0)
    nn   = int((lbls == -1).sum())
    sil  = silhouette_score(X, lbls) if nc > 1 and nn < len(X)-1 else 0.0
    return lbls, nc, nn, float(sil)

X_bytes = X.astype(np.float64).tobytes()
with st.spinner("Calculando…"):
    km_labels, km_centers, km_sil = run_kmeans(X_bytes, k)
    db_labels, db_nc, db_noise, db_sil = run_dbscan(X_bytes, eps_db, min_samples)

r_tda = load_tda(tda_key(niveles))
if r_tda is not None:
    holes   = top_h1_with_cocycles(r_tda, k=top_k)
    n_h1    = len(r_tda["dgms"][1])
    d_all   = np.where(np.isfinite(r_tda["dgms"][1][:,1]),
                       r_tda["dgms"][1][:,1], r_tda["thresh"])
    max_pers = float((d_all - r_tda["dgms"][1][:,0]).max()) if n_h1 > 0 else 0.0
else:
    holes, n_h1, max_pers = [], 0, 0.0

lats   = sample["latitud"].to_numpy(dtype=np.float64)
lons   = sample["longitud"].to_numpy(dtype=np.float64)
levels = sample["nivel"].to_numpy(dtype=str)

# ── Tablas de zonas detectadas ────────────────────────────────────────────────
def km_cluster_table():
    rows = []
    for lbl in range(k):
        mask  = km_labels == lbl
        pts   = X[mask]
        clat, clon = utm_to_latlon(*km_centers[lbl])
        dists = np.linalg.norm(pts - km_centers[lbl], axis=1)
        rows.append({
            "Clúster": f"C{lbl}",
            "Escuelas": int(mask.sum()),
            "Radio medio (m)": int(dists.mean()),
            "Radio máx (m)": int(dists.max()),
            "Centroide lat": round(clat, 5),
            "Centroide lon": round(clon, 5),
            "Color": PALETTE_HEX[lbl % len(PALETTE_HEX)],
        })
    return pd.DataFrame(rows).sort_values("Escuelas", ascending=False)

def db_cluster_table():
    rows = []
    unique = [l for l in sorted(set(db_labels)) if l != -1]
    for lbl in unique:
        mask = db_labels == lbl
        pts  = X[mask]
        cx, cy = pts.mean(axis=0)
        clat, clon = utm_to_latlon(cx, cy)
        dists = np.linalg.norm(pts - np.array([cx, cy]), axis=1)
        rows.append({
            "Clúster": f"C{lbl}",
            "Escuelas": int(mask.sum()),
            "Radio medio (m)": int(dists.mean()),
            "Radio máx (m)": int(dists.max()),
            "Centroide lat": round(clat, 5),
            "Centroide lon": round(clon, 5),
        })
    return pd.DataFrame(rows).sort_values("Escuelas", ascending=False)

def tda_holes_table():
    rows = []
    for i, h in enumerate(holes):
        lat, lon = utm_to_latlon(*h["centroid_xy"])
        rows.append({
            "Hueco": f"H{i+1}",
            "Persistencia (m)": int(h["pers"]),
            "Nacimiento (m)": int(h["birth"]),
            "Muerte (m)": int(h["death"]),
            "Vértices": h["n_verts"],
            "Latitud": round(lat, 5),
            "Longitud": round(lon, 5),
            "Criticidad": "Alta" if h["pers"]>1500 else ("Media" if h["pers"]>700 else "Baja"),
        })
    return pd.DataFrame(rows)

# ── Constructores de mapa ─────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def build_km_map(lats, lons, labels_b, k, centers_b):
    labels  = np.frombuffer(labels_b, dtype=np.int32)
    centers = np.frombuffer(centers_b, dtype=np.float64).reshape(-1, 2)
    m = base_map(zoom=11)
    for lbl in range(k):
        col   = PALETTE_HEX[lbl % len(PALETTE_HEX)]
        layer = folium.FeatureGroup(name=f"Cluster {lbl}", show=True)
        mask  = labels == lbl
        for la, lo in zip(lats[mask], lons[mask]):
            folium.CircleMarker([la, lo], radius=5, color=col, fill=True,
                fill_color=col, fill_opacity=0.75, weight=0,
                tooltip=f"Cluster {lbl}").add_to(layer)
        layer.add_to(m)
    cl = folium.FeatureGroup(name="Centroides", show=True)
    for i, (cx, cy) in enumerate(centers):
        clat, clon = utm_to_latlon(cx, cy)
        folium.Marker([clat, clon], icon=folium.DivIcon(
            html=f"<div style='font-size:11px;font-weight:bold;"
                 f"background:{PALETTE_HEX[i%len(PALETTE_HEX)]};color:white;"
                 f"border-radius:50%;width:22px;height:22px;"
                 f"display:flex;align-items:center;justify-content:center;"
                 f"border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,.4)'>C{i}</div>",
            icon_size=(22,22), icon_anchor=(11,11)),
            tooltip=f"Centroide C{i}").add_to(cl)
    cl.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    return m

@st.cache_data(show_spinner=False)
def build_db_map(lats, lons, labels_b, _nc):
    labels = np.frombuffer(labels_b, dtype=np.int32)
    m      = base_map(zoom=11)
    noise  = folium.FeatureGroup(name="Sin clasificar", show=True)
    layers = {int(l): folium.FeatureGroup(name=f"Cluster {l}", show=True)
              for l in sorted(set(labels)) if l != -1}
    for la, lo, lb in zip(lats, lons, labels):
        if lb == -1:
            folium.CircleMarker([la, lo], radius=3, color="#AAA", fill=True,
                fill_color="#CCC", fill_opacity=0.5, weight=0,
                tooltip="Sin clasificar").add_to(noise)
        else:
            col = PALETTE_HEX[int(lb) % len(PALETTE_HEX)]
            folium.CircleMarker([la, lo], radius=5, color=col, fill=True,
                fill_color=col, fill_opacity=0.75, weight=0,
                tooltip=f"Cluster {lb}").add_to(layers[int(lb)])
    for ly in layers.values(): ly.add_to(m)
    noise.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    return m

@st.cache_data
def build_tda_map(lats, lons, _levels, holes_data):
    m  = base_map(zoom=11)
    sl = folium.FeatureGroup(name="Escuelas", show=True)
    for la, lo, nv in zip(lats, lons, _levels):
        col = NIVEL_COLOR.get(nv, "#888")
        folium.CircleMarker([la, lo], radius=3, color=col, fill=True,
            fill_color=col, fill_opacity=0.5, weight=0, tooltip=nv).add_to(sl)
    sl.add_to(m)
    for i, h in enumerate(holes_data):
        col  = HOLE_COLORS[i % len(HOLE_COLORS)]
        clat, clon = utm_to_latlon(*h["centroid_xy"])
        r    = max(h["pers"]/2, 200)
        hl   = folium.FeatureGroup(name=f"Hueco H{i+1} — {h['pers']:.0f} m", show=True)
        folium.Circle([clat, clon], radius=r, color=col, weight=2.5,
            fill=True, fill_color=col, fill_opacity=0.15,
            popup=folium.Popup(
                f"<b>Hueco H{i+1}</b><br>Persistencia: <b>{h['pers']:.0f} m</b><br>"
                f"Nacimiento: {h['birth']:.0f} m · Muerte: {h['death']:.0f} m<br>"
                f"Vértices: {h['n_verts']} · Radio: {r:.0f} m", max_width=220)
        ).add_to(hl)
        folium.CircleMarker([clat, clon], radius=7, color="white",
            fill=True, fill_color=col, fill_opacity=1, weight=2,
            tooltip=f"H{i+1} · {h['pers']:.0f} m").add_to(hl)
        folium.Marker([clat, clon], icon=folium.DivIcon(
            html=f"<div style='font-size:11px;font-weight:bold;color:{col};"
                 f"text-shadow:0 0 3px white;margin-top:-24px;"
                 f"margin-left:10px;white-space:nowrap'>H{i+1}</div>",
            icon_size=(30,20), icon_anchor=(0,0))).add_to(hl)
        hl.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    return m

# Construir mapas
km_lb = km_labels.astype(np.int32).tobytes()
db_lb = db_labels.astype(np.int32).tobytes()
km_cb = km_centers.astype(np.float64).tobytes()

with st.spinner("Construyendo mapas…"):
    m_km  = build_km_map(lats, lons, km_lb, k, km_cb)
    m_db  = build_db_map(lats, lons, db_lb, db_nc)
    m_tda = build_tda_map(lats, lons, levels,
                [{"centroid_xy":h["centroid_xy"],"pers":h["pers"],
                  "birth":h["birth"],"death":h["death"],"n_verts":h["n_verts"]}
                 for h in holes])

MAP_H = 520

# ═══════════════════════════════════════════════════════════════════════════
# KPIs — siempre visibles arriba
# ═══════════════════════════════════════════════════════════════════════════
st.divider()
col_km, col_db, col_tda = st.columns(3)

with col_km:
    st.markdown("<div style='border-left:4px solid #2E86C1;padding-left:12px'>"
                "<span style='font-size:12px;color:#666;text-transform:uppercase;"
                "letter-spacing:1px'>K-Means</span></div>", unsafe_allow_html=True)
    a, b = st.columns(2)
    a.metric("Clústeres", k)
    b.metric("Silhouette", f"{km_sil:.3f}")
    st.caption("Divide el espacio en k regiones. No detecta vacíos internos.")

with col_db:
    st.markdown("<div style='border-left:4px solid #117A65;padding-left:12px'>"
                "<span style='font-size:12px;color:#666;text-transform:uppercase;"
                "letter-spacing:1px'>DBSCAN</span></div>", unsafe_allow_html=True)
    a, b = st.columns(2)
    a.metric("Clústeres", db_nc)
    b.metric("Sin clasificar", f"{db_noise:,}")
    a2, b2 = st.columns(2)
    a2.metric("Silhouette", f"{db_sil:.3f}")
    b2.metric("% ruido", f"{db_noise/n*100:.1f}%")
    st.caption("Agrupa densidad local. Huecos topológicos invisibles.")

with col_tda:
    st.markdown("<div style='border-left:4px solid #C0392B;padding-left:12px'>"
                "<span style='font-size:12px;color:#666;text-transform:uppercase;"
                "letter-spacing:1px'>TDA — Homología Persistente</span></div>",
                unsafe_allow_html=True)
    a, b = st.columns(2)
    a.metric("Features H₁", n_h1)
    b.metric("Huecos top", len(holes))
    a2, b2 = st.columns(2)
    a2.metric("Mayor persistencia", f"{max_pers:.0f} m")
    b2.metric("Requiere k", "No")
    st.caption("Detecta huecos persistentes sin parámetros a priori.")

# ═══════════════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════════════
st.divider()
tab1, tab2, tab3, tab4 = st.tabs([
    "K-Means",
    "DBSCAN",
    "TDA — Huecos de cobertura",
    "Comparativa y conclusiones",
])

# ─── TAB 1: K-Means ──────────────────────────────────────────────────────────
with tab1:
    st.subheader("Mapa de clústeres — K-Means")
    st.caption(f"{k} clústeres coloreados · Centroides marcados · Capas toggleables")
    st_folium(m_km, height=MAP_H, use_container_width=True, returned_objects=[])
    st.info(
        f"K-Means dividió las {n:,} escuelas en **{k} regiones de Voronoi**. "
        "Cada punto pertenece al centroide más cercano. "
        "El problema: dentro de cada región puede haber colonias enteras sin escuelas."
    )

    st.subheader("Zonas detectadas por K-Means")
    df_km = km_cluster_table()

    col_t, col_c = st.columns([1, 1])
    with col_t:
        st.dataframe(df_km.drop(columns=["Color"]), use_container_width=True, hide_index=True)

    with col_c:
        fig_km_bar = go.Figure()
        fig_km_bar.add_trace(go.Bar(
            x=df_km["Clúster"],
            y=df_km["Escuelas"],
            marker=dict(color=df_km["Color"].tolist(), line=dict(color="white", width=1)),
            text=df_km["Escuelas"],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Escuelas: %{y}<extra></extra>",
        ))
        fig_km_bar.update_layout(
            **LAYOUT_BASE,
            title=dict(text="<b>Escuelas por clúster</b>", font=dict(size=13)),
            xaxis=dict(title="Clúster", showgrid=False),
            yaxis=dict(title="Escuelas", showgrid=True, gridcolor="#EFEFEF"),
            height=360, showlegend=False,
        )
        st.plotly_chart(fig_km_bar, use_container_width=True, config=PLOTLY_CONFIG)

    st.caption(
        "**Limitación:** K-Means solo informa cuántas escuelas hay en cada región "
        "y dónde está el centroide. No puede indicar si hay zonas sin cobertura "
        "dentro de cada clúster."
    )

# ─── TAB 2: DBSCAN ────────────────────────────────────────────────────────────
with tab2:
    st.subheader("Mapa de clústeres — DBSCAN")
    st.caption(f"{db_nc} clústeres · {db_noise} puntos sin clasificar (gris) · Capas toggleables")
    st_folium(m_db, height=MAP_H, use_container_width=True, returned_objects=[])
    st.info(
        f"DBSCAN encontró **{db_nc} grupos** densamente conectados y marcó "
        f"**{db_noise} puntos** ({db_noise/n*100:.1f}%) como ruido. "
        "Detecta mejor la forma real de los grupos, pero los huecos topológicos internos siguen invisibles."
    )

    st.subheader("Zonas detectadas por DBSCAN")
    df_db = db_cluster_table()

    if len(df_db) == 0:
        st.warning("DBSCAN no encontró clústeres con los parámetros actuales. Ajusta ε o min_samples.")
    else:
        col_t, col_c = st.columns([1, 1])
        with col_t:
            st.dataframe(df_db, use_container_width=True, hide_index=True)
            st.metric("Puntos sin clasificar (ruido)", f"{db_noise:,}",
                      delta=f"{db_noise/n*100:.1f}% del total", delta_color="inverse")

        with col_c:
            top_db = df_db.head(15)
            fig_db_bar = go.Figure()
            fig_db_bar.add_trace(go.Bar(
                x=top_db["Clúster"],
                y=top_db["Escuelas"],
                marker=dict(
                    color=[PALETTE_HEX[i % len(PALETTE_HEX)] for i in range(len(top_db))],
                    line=dict(color="white", width=1)
                ),
                text=top_db["Escuelas"],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>Escuelas: %{y}<extra></extra>",
            ))
            fig_db_bar.update_layout(
                **LAYOUT_BASE,
                title=dict(text="<b>Escuelas por clúster (top 15)</b>", font=dict(size=13)),
                xaxis=dict(title="Clúster", showgrid=False),
                yaxis=dict(title="Escuelas", showgrid=True, gridcolor="#EFEFEF"),
                height=360, showlegend=False,
            )
            st.plotly_chart(fig_db_bar, use_container_width=True, config=PLOTLY_CONFIG)

    st.caption(
        "**Limitación:** DBSCAN informa grupos densamente conectados y puntos aislados. "
        "No puede detectar un hueco topológico — una zona rodeada de escuelas pero vacía por dentro."
    )

# ─── TAB 3: TDA ───────────────────────────────────────────────────────────────
with tab3:
    st.subheader("Mapa de huecos H₁ — TDA")
    st.caption("Círculos = huecos persistentes · Radio ∝ persistencia · Clic en cada hueco para detalles")
    st_folium(m_tda, height=MAP_H, use_container_width=True, returned_objects=[])
    st.success(
        f"TDA identificó **{n_h1} features H₁**. Los **{len(holes)} más persistentes** "
        f"(mayor persistencia: **{max_pers:.0f} m**) son zonas rodeadas de escuelas "
        "pero con déficit interno de cobertura — completamente invisibles para K-Means y DBSCAN."
    )

    if holes:
        st.subheader("Huecos de cobertura detectados por TDA")
        st.caption("Invisibles para K-Means y DBSCAN.")
        df_tda = tda_holes_table()

        col_t, col_c = st.columns([1, 1])
        with col_t:
            def style_crit(val):
                if val == "Alta":  return "color:#922B21;font-weight:600"
                if val == "Media": return "color:#7D6608;font-weight:600"
                return "color:#1A5276;font-weight:600"
            st.dataframe(
                df_tda.style.map(style_crit, subset=["Criticidad"]),
                use_container_width=True, hide_index=True,
            )

        with col_c:
            crit_colors = ["#C0392B" if r=="Alta" else "#E67E22" if r=="Media"
                           else "#2E86C1" for r in df_tda["Criticidad"]]
            fig_tda_bar = go.Figure()
            fig_tda_bar.add_trace(go.Bar(
                x=df_tda["Hueco"],
                y=df_tda["Persistencia (m)"],
                marker=dict(color=crit_colors, line=dict(color="white", width=1.5)),
                text=[f"{v} m" for v in df_tda["Persistencia (m)"]],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>Persistencia: %{y} m<extra></extra>",
            ))
            fig_tda_bar.update_layout(
                **LAYOUT_BASE,
                title=dict(
                    text="<b>Persistencia por hueco H₁</b>"
                         "<br><sup style='color:#888'>Rojo=Alta · Naranja=Media · Azul=Baja</sup>",
                    font=dict(size=13)),
                xaxis=dict(title="Hueco", showgrid=False),
                yaxis=dict(title="Persistencia (m)", showgrid=True, gridcolor="#EFEFEF"),
                height=360, showlegend=False,
            )
            st.plotly_chart(fig_tda_bar, use_container_width=True, config=PLOTLY_CONFIG)
    else:
        st.info("No hay resultados TDA pre-computados para la selección actual.")

# ─── TAB 4: COMPARATIVA Y CONCLUSIONES ───────────────────────────────────────
with tab4:
    st.subheader("¿Qué detecta cada método?")

    capabilities = {
        "Capacidad analítica": [
            "Zonas de alta concentración",
            "Número de grupos automático",
            "Forma arbitraria de los grupos",
            "Huecos de cobertura internos",
            "Sin parámetro k obligatorio",
            "Robusto a outliers",
            "Invariante a escala espacial",
            "Interpretación geográfica directa",
        ],
        "K-Means":  ["Sí","No — requiere k","No — solo bolas","No","No","No","No","Sí"],
        "DBSCAN":   ["Sí","Sí","Sí","No","Sí","Sí","No","Parcial"],
        "TDA / H₁": ["Parcial","N/A","N/A","Sí","Sí","Sí","Sí","Sí"],
    }
    df_cap = pd.DataFrame(capabilities)

    def color_cell(val):
        v = str(val)
        if v == "Sí":      return "background-color:#D6EAF8;color:#1A5276;font-weight:600"
        if v.startswith("No"): return "background-color:#FDEDEC;color:#922B21"
        if v in ("Parcial","N/A"): return "background-color:#FEF9E7;color:#7D6608"
        return "color:#333"

    st.dataframe(
        df_cap.style.map(color_cell, subset=["K-Means","DBSCAN","TDA / H₁"]),
        use_container_width=True, hide_index=True,
    )

    st.divider()
    st.subheader("Comparativa visual de resultados")

    col_l, col_r = st.columns(2)

    # Gráfica 1: zonas/hallazgos detectados por cada método
    with col_l:
        methods  = ["K-Means", "DBSCAN", "TDA"]
        detected = [k, db_nc, len(holes)]
        colors   = ["#2E86C1", "#117A65", "#C0392B"]
        labels   = [f"{k} clústeres", f"{db_nc} clústeres", f"{len(holes)} huecos H₁"]

        fig_comp = go.Figure()
        fig_comp.add_trace(go.Bar(
            x=methods, y=detected,
            marker=dict(color=colors, line=dict(color="white", width=2)),
            text=labels,
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Zonas detectadas: %{y}<extra></extra>",
        ))
        fig_comp.update_layout(
            **LAYOUT_BASE,
            title=dict(text="<b>Zonas / hallazgos detectados por método</b>",
                       font=dict(size=13)),
            xaxis=dict(showgrid=False),
            yaxis=dict(title="Cantidad", showgrid=True, gridcolor="#EFEFEF"),
            height=360, showlegend=False,
        )
        st.plotly_chart(fig_comp, use_container_width=True, config=PLOTLY_CONFIG)

    # Gráfica 2: score de capacidades (Sí=1, Parcial=0.5, No=0)
    with col_r:
        score_map = {"Sí": 1.0, "Parcial": 0.5, "N/A": 0.5}
        def score(vals):
            return sum(score_map.get(v, 0.0) for v in vals)

        km_vals  = capabilities["K-Means"]
        db_vals  = capabilities["DBSCAN"]
        tda_vals = capabilities["TDA / H₁"]
        scores   = [score(km_vals), score(db_vals), score(tda_vals)]

        fig_score = go.Figure()
        fig_score.add_trace(go.Bar(
            x=["K-Means", "DBSCAN", "TDA / H₁"],
            y=scores,
            marker=dict(color=["#2E86C1","#117A65","#C0392B"],
                        line=dict(color="white", width=2)),
            text=[f"{s:.1f} / 8" for s in scores],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Score: %{y:.1f}/8<extra></extra>",
        ))
        fig_score.update_layout(
            **LAYOUT_BASE,
            title=dict(
                text="<b>Score de capacidades analíticas</b>"
                     "<br><sup style='color:#888'>Sí=1 · Parcial/N/A=0.5 · No=0</sup>",
                font=dict(size=13)),
            xaxis=dict(showgrid=False),
            yaxis=dict(title="Score (sobre 8)", range=[0, 9],
                       showgrid=True, gridcolor="#EFEFEF"),
            height=360, showlegend=False,
        )
        st.plotly_chart(fig_score, use_container_width=True, config=PLOTLY_CONFIG)

    # Gráfica 3: radar de capacidades
    st.subheader("Perfil de capacidades por método")
    categories = [
        "Concentración", "Grupos automático", "Forma arbitraria",
        "Huecos internos", "Sin k", "Robusto ruido", "Escala espacial", "Geo-interpretable"
    ]
    def to_scores(vals):
        return [score_map.get(v, 0.0) for v in vals]

    fig_radar = go.Figure()
    for label, vals, color in [
        ("K-Means",  km_vals,  "#2E86C1"),
        ("DBSCAN",   db_vals,  "#117A65"),
        ("TDA / H₁", tda_vals, "#C0392B"),
    ]:
        sc = to_scores(vals) + [to_scores(vals)[0]]
        cats = categories + [categories[0]]
        fig_radar.add_trace(go.Scatterpolar(
            r=sc, theta=cats, fill="toself",
            name=label,
            line=dict(color=color, width=2),
            fillcolor=color,
            opacity=0.18,
        ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1],
                                   tickvals=[0, 0.5, 1],
                                   ticktext=["No", "Parcial", "Sí"])),
        showlegend=True,
        legend=dict(orientation="h", y=-0.15),
        paper_bgcolor="white",
        height=480,
        margin=dict(l=60, r=60, t=40, b=60),
        title=dict(text="<b>Radar de capacidades analíticas</b>", font=dict(size=13)),
    )
    st.plotly_chart(fig_radar, use_container_width=True, config=PLOTLY_CONFIG)

    st.divider()
    st.subheader("Conclusión")
    st.markdown(f"""
**K-Means** encontró **{k} grupos** de escuelas en CDMX.
Útil para entender la distribución general, pero no puede responder
*"¿dónde debería construirse la siguiente escuela?"* — no ve los vacíos internos.

**DBSCAN** identificó **{db_nc} clústeres** densamente conectados y marcó
**{db_noise} puntos** ({db_noise/n*100:.1f}%) como ruido.
Mejora la detección de forma, pero los huecos topológicos siguen siendo
invisibles porque DBSCAN analiza densidad local, no estructura global.

**TDA** detectó **{n_h1} features H₁**, de las cuales los **{len(holes)} más persistentes**
corresponden a zonas donde las escuelas forman un perímetro pero el interior queda
desatendido. El hueco más crítico tiene **{max_pers:.0f} m de persistencia** —
una zona de ~{max_pers/2:.0f} m de radio sin cobertura incluso conectando
todas las escuelas circundantes.

---
> **El conteo dice cuántas hay.
> El clustering dice dónde están agrupadas.
> TDA dice dónde faltan — y esa es la pregunta que importa en política pública.**
""")