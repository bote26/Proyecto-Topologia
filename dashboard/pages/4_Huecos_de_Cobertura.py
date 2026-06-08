"""Huecos H1 persistentes proyectados sobre el mapa de CDMX."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from utils.data_loader import NIVEL_COLOR, NIVELES, SECTORES, load_escuelas
from utils.plotting import add_holes_layer, base_map, utm_to_latlon
from utils.tda import compute_for_points, top_h1_with_cocycles

st.set_page_config(page_title="Huecos de Cobertura", page_icon="🗺️", layout="wide")
st.title("🗺️ Huecos de cobertura escolar")

st.markdown(
    "Los **huecos H₁ más persistentes** representan zonas rodeadas por "
    "escuelas pero con un déficit interno de cobertura. Cada hueco se dibuja "
    "como un círculo centrado en el centroide del ciclo, con radio = "
    "persistencia / 2. Los huecos se calculan **siempre sobre los datos filtrados**."
)

df = load_escuelas()

# ── Caché por subconjunto de puntos ───────────────────────────────────────────
@st.cache_data(show_spinner=False)
def _compute_holes(pts_bytes: bytes, n_pts: int, thresh: int, max_n: int, top_k: int):
    pts = np.frombuffer(pts_bytes, dtype=np.float64).reshape(n_pts, 2)
    r = compute_for_points(pts, thresh=thresh, max_n=max_n)
    if r is None:
        return []
    return top_h1_with_cocycles(r, k=top_k)

with st.sidebar:
    st.header("Selección")
    niveles_disponibles = [*NIVELES, "todas"]
    seleccion = st.multiselect(
        "Niveles a mostrar", niveles_disponibles,
        default=["primaria", "secundaria"],
    )
    sector_sel = st.radio(
        "Sector", ["ambos", *SECTORES],
        index=0, horizontal=True,
    )
    thresh_h = st.slider("Umbral ε para persistencia (m)", 500, 10000, 5000, 100)
    max_n_h = st.slider(
        "Submuestreo TDA (landmarks)", 200, 2000, 800, 100,
        help="Más landmarks = más preciso pero más lento.",
    )
    top_k = st.slider("Top-K huecos por nivel", 1, 10, 5)
    show_schools = st.checkbox("Mostrar escuelas como puntos", False)

if not seleccion:
    st.info("Selecciona al menos un nivel.")
    st.stop()

m = base_map()
rows = []

for niv in seleccion:
    # ── Filtrar datos exactamente igual para huecos y puntos ──────────────────
    if niv == "todas":
        sub = df.copy()
    else:
        sub = df[df["nivel"] == niv]

    if sector_sel != "ambos":
        sub = sub[sub["sector"] == sector_sel]

    if len(sub) < 3:
        st.warning(f"Pocas escuelas para `{niv}` / `{sector_sel}` ({len(sub)}); se omite.")
        continue

    pts = sub[["x_utm", "y_utm"]].values.astype(np.float64)
    label_suffix = niv if sector_sel == "ambos" else f"{niv} · {sector_sel}"

    with st.spinner(f"Calculando huecos — {label_suffix} ({len(sub):,} escuelas)…"):
        holes = _compute_holes(pts.tobytes(), len(pts), thresh_h, max_n_h, top_k)

    if not holes:
        st.warning(f"Sin huecos detectados para `{label_suffix}`.")
        continue

    color = NIVEL_COLOR.get(niv, "black")
    add_holes_layer(m, holes, color=color, label=f"huecos — {label_suffix}")

    for h in holes:
        lat, lon = utm_to_latlon(*h["centroid_xy"])
        rows.append({
            "nivel": niv,
            "sector": sector_sel,
            "lat": lat, "lon": lon,
            "birth (m)": round(h["birth"], 0),
            "death (m)": round(h["death"], 0),
            "persistencia (m)": round(h["pers"], 0),
            "n_vértices": h["n_verts"],
        })

# ── Capa opcional de escuelas — respeta nivel Y sector ────────────────────────
if show_schools:
    import folium as _folium
    niveles_reales = [n for n in seleccion if n != "todas"]
    if "todas" in seleccion:
        df_pts = df.copy()
    else:
        df_pts = df[df["nivel"].isin(niveles_reales)]
    if sector_sel != "ambos":
        df_pts = df_pts[df_pts["sector"] == sector_sel]

    layer = _folium.FeatureGroup(name="escuelas (muestra)")
    for _, row in df_pts.sample(min(800, len(df_pts)), random_state=0).iterrows():
        _folium.CircleMarker(
            [row["latitud"], row["longitud"]], radius=2,
            color=NIVEL_COLOR.get(row["nivel"], "gray"),
            fill=True, fill_opacity=0.6, weight=0,
        ).add_to(layer)
    layer.add_to(m)

import folium
folium.LayerControl(collapsed=False).add_to(m)

col1, col2 = st.columns([3, 2])

with col1:
    st_folium(m, height=620, use_container_width=True, returned_objects=[])

with col2:
    st.subheader("Huecos identificados")
    if rows:
        df_rows = pd.DataFrame(rows).sort_values("persistencia (m)", ascending=False)
        st.dataframe(df_rows, use_container_width=True, hide_index=True)
        biggest = df_rows.iloc[0]
        st.info(
            f"**Hueco más significativo**: nivel `{biggest['nivel']}`, "
            f"~{int(biggest['persistencia (m)'])} m de persistencia, "
            f"centroide en ({biggest['lat']:.4f}, {biggest['lon']:.4f}). "
            "Indica una zona con déficit potencial de cobertura escolar "
            "que podría priorizarse para nuevos planteles o reasignación "
            "de matrícula."
        )
    else:
        st.info("No se detectaron huecos con la configuración actual.")