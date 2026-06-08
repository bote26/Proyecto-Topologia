"""Vista combinada: complejo Vietoris-Rips + huecos H1 sobre el mismo mapa."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import streamlit as st
import folium
from scipy.spatial import cKDTree
from streamlit_folium import st_folium

from utils.data_loader import NIVEL_COLOR, NIVELES, SECTORES, load_escuelas
from utils.tda import landmark_sample, top_h1_with_cocycles, compute_for_points
from utils.plotting import base_map, utm_to_latlon, add_holes_layer

st.set_page_config(
    page_title="Complejo + Huecos",
    page_icon="🧩",
    layout="wide",
)

# ── Caché: calcula TDA solo cuando cambia el subconjunto de puntos ─────────────
@st.cache_data(show_spinner=False)
def _compute_holes(pts_bytes: bytes, n_pts: int, thresh: int, max_n: int, top_k: int):
    """Calcula huecos H₁ a partir de un array de puntos serializado."""
    pts = np.frombuffer(pts_bytes, dtype=np.float64).reshape(n_pts, 2)
    r = compute_for_points(pts, thresh=thresh, max_n=max_n)
    if r is None:
        return []
    return top_h1_with_cocycles(r, k=top_k)

# ── Cabecera ──────────────────────────────────────────────────────────────────
st.title("🧩 Complejo Simplicial + Huecos de Cobertura")
st.markdown(
    "Visualiza simultáneamente la **estructura del complejo Vietoris-Rips** "
    "(vértices, aristas y triángulos) y los **huecos H₁ más persistentes** "
    "(círculos de cobertura) sobre el mismo mapa de CDMX. "
    "Los huecos se calculan **siempre con los datos filtrados** para que "
    "el complejo y los huecos sean consistentes entre sí."
)

df = load_escuelas()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Parámetros")

    st.subheader("Filtros de datos")
    niv = st.selectbox("Nivel educativo", ["todas", *NIVELES], index=2)
    sec = st.selectbox("Sector", ["ambos", *SECTORES])

    st.subheader("Complejo Vietoris-Rips")
    max_pts = st.slider(
        "Puntos máx (landmarks para el complejo)",
        50, 600, 200, 25,
        help="Submuestreo para dibujar el complejo. Más puntos = mapa más lento.",
    )
    eps = st.slider("ε — radio del complejo (m)", 0, 5000, 1200, 50)
    show_triangles = st.checkbox("Mostrar 2-símplex (triángulos)", True)
    show_edges = st.checkbox("Mostrar 1-símplex (aristas)", True)
    show_disks = st.checkbox("Mostrar discos Čech (radio ε/2)", False)
    show_vertices = st.checkbox("Mostrar vértices (escuelas)", True)

    st.subheader("Huecos H₁")
    top_k = st.slider("Top-K huecos a mostrar", 1, 10, 5)
    thresh_h = st.slider(
        "Umbral ε para persistencia (m)",
        500, 10000, 5000, 100,
        help="Radio máximo hasta el que se construye el complejo para la "
             "homología. No afecta el dibujo del complejo arriba.",
    )
    max_n_h = st.slider(
        "Submuestreo TDA (landmarks para huecos)",
        200, 2000, 600, 100,
        help="Cuántos puntos se usan para calcular la homología persistente. "
             "Más puntos = más preciso pero más lento.",
    )

# ── Filtrado de datos (fuente de verdad única) ────────────────────────────────
sub = df.copy()
if niv != "todas":
    sub = sub[sub["nivel"] == niv]
if sec != "ambos":
    sub = sub[sub["sector"] == sec]

n_sub = len(sub)
st.caption(
    f"**{n_sub:,}** escuelas con los filtros actuales "
    f"(nivel: *{niv}*, sector: *{sec}*)."
)

if n_sub < 3:
    st.warning("Necesito al menos 3 escuelas para construir el complejo.")
    st.stop()

# ── Color principal ───────────────────────────────────────────────────────────
color = NIVEL_COLOR.get(niv, "#2563eb")

# ── Construcción del complejo ─────────────────────────────────────────────────
X_all = sub[["x_utm", "y_utm"]].values
Xs = landmark_sample(X_all, max_n=max_pts)

edges, triangles = [], []
if eps > 0 and len(Xs) > 1:
    tree = cKDTree(Xs)
    edges = list(tree.query_pairs(r=eps))
    if len(Xs) <= 250 and show_triangles:
        edge_set = set(edges)
        n = len(Xs)
        for i, j in edges:
            for k in range(j + 1, n):
                if (i, k) in edge_set and (j, k) in edge_set:
                    triangles.append((i, j, k))

latlon = np.array([utm_to_latlon(x, y) for x, y in Xs])

# ── Huecos H₁ — siempre calculados con los datos filtrados ───────────────────
# La clave de caché incluye nivel + sector + parámetros TDA, por lo que solo
# recalcula cuando algo realmente cambia.
with st.spinner(f"Calculando huecos sobre {n_sub:,} escuelas filtradas…"):
    pts_bytes = X_all.astype(np.float64).tobytes()
    holes = _compute_holes(pts_bytes, n_sub, thresh_h, max_n_h, top_k)

# ── Mapa Folium ───────────────────────────────────────────────────────────────
m = base_map()

# — 2-símplex: triángulos —
if show_triangles and triangles:
    tri_layer = folium.FeatureGroup(name="2-símplex (triángulos)", show=True)
    for i, j, k in triangles:
        folium.Polygon(
            locations=[latlon[i], latlon[j], latlon[k]],
            color=color, fill=True, fill_color=color,
            fill_opacity=0.18, weight=0,
        ).add_to(tri_layer)
    tri_layer.add_to(m)

# — 1-símplex: aristas —
if show_edges and edges:
    edge_layer = folium.FeatureGroup(name="1-símplex (aristas)", show=True)
    for i, j in edges:
        folium.PolyLine(
            locations=[latlon[i], latlon[j]],
            color=color, weight=1.4, opacity=0.55,
        ).add_to(edge_layer)
    edge_layer.add_to(m)

# — Discos Čech —
if show_disks and eps > 0:
    disk_layer = folium.FeatureGroup(name="Discos Čech (ε/2)", show=True)
    for lat, lon in latlon:
        folium.Circle(
            location=[lat, lon], radius=eps / 2,
            color=color, fill=True, fill_color=color,
            fill_opacity=0.07, weight=0,
        ).add_to(disk_layer)
    disk_layer.add_to(m)

# — Vértices —
if show_vertices:
    vert_layer = folium.FeatureGroup(name="0-símplex (escuelas)", show=True)
    for lat, lon in latlon:
        folium.CircleMarker(
            location=[lat, lon], radius=4,
            color=color, fill=True, fill_color=color,
            fill_opacity=0.9, weight=1,
        ).add_to(vert_layer)
    vert_layer.add_to(m)

# — Huecos H₁ —
if holes:
    add_holes_layer(m, holes, color="#e11d48", label="Huecos H₁ persistentes")

folium.LayerControl(collapsed=False).add_to(m)

# ── Métricas rápidas ──────────────────────────────────────────────────────────
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Vértices |V|", len(Xs))
m2.metric("Aristas |E|", len(edges))
m3.metric("Triángulos |T|", len(triangles))
m4.metric("ε (m)", f"{eps:,}")
m5.metric("Huecos H₁", len(holes))

# ── Layout principal ──────────────────────────────────────────────────────────
col_map, col_info = st.columns([3, 2])

with col_map:
    st_folium(m, height=620, use_container_width=True, returned_objects=[])

with col_info:
    st.subheader("Huecos H₁ identificados")
    if holes:
        rows = []
        for h in holes:
            lat, lon = utm_to_latlon(*h["centroid_xy"])
            rows.append({
                "Rank": rows.__len__() + 1,
                "Nacimiento (m)": int(h["birth"]),
                "Muerte (m)": int(h["death"]),
                "Persistencia (m)": int(h["pers"]),
                "Vértices ciclo": h["n_verts"],
                "Lat": round(lat, 4),
                "Lon": round(lon, 4),
            })
        df_holes = pd.DataFrame(rows)
        st.dataframe(df_holes, use_container_width=True, hide_index=True)

        best = max(holes, key=lambda h: h["pers"])
        b_lat, b_lon = utm_to_latlon(*best["centroid_xy"])
        st.info(
            f"**Hueco más significativo**: persistencia "
            f"**{int(best['pers'])} m**, centroide en "
            f"({b_lat:.4f}, {b_lon:.4f})."
        )

        # Mini barplot de persistencias
        import plotly.express as px
        fig = px.bar(
            df_holes,
            x="Rank", y="Persistencia (m)",
            color="Persistencia (m)",
            color_continuous_scale="Reds",
            labels={"Rank": "Hueco #"},
            title="Persistencia por hueco H₁",
            height=260,
        )
        fig.update_layout(coloraxis_showscale=False, margin=dict(t=36, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No se encontraron huecos para la configuración actual.")

    with st.expander("📖 Cómo leer este mapa"):
        st.markdown(f"""
**Complejo Vietoris-Rips** (color {color}):
- **Puntos** = escuelas del subconjunto (landmark sample).
- **Aristas** = pares de escuelas con distancia ≤ ε.
- **Triángulos** = triples de escuelas mutuamente a distancia ≤ ε.

**Huecos H₁** (círculos rojos 🔴):
- Cada círculo marca el **centroide** de un ciclo 1-dimensional persistente.
- El radio del círculo es `persistencia / 2` (en metros).
- Un hueco grande indica una zona **rodeada de escuelas pero con déficit interno**
  de cobertura — candidata a nuevos planteles o redistribución de matrícula.

**Clave de lectura conjunta:**  
Cuando el complejo se torna denso (muchos triángulos) alrededor de un hueco rojo,
eso confirma que la zona está topológicamente "encerrada" por escuelas existentes.
Cuando los triángulos son escasos, el hueco puede deberse simplemente a baja densidad
escolar global.
""")