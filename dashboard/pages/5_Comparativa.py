"""Comparativa visual: complejo simplicial + huecos H1 en el mismo mapa geográfico."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import folium
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy.spatial import cKDTree
from streamlit_folium import st_folium

from utils.data_loader import NIVEL_COLOR, NIVELES, load_escuelas, load_tda
from utils.plotting import base_map, utm_to_latlon
from utils.tda import betti_curves, top_h1_with_cocycles

st.set_page_config(page_title="Comparativa", page_icon="🔗", layout="wide")
st.title("🔗 Comparativa visual: complejo simplicial + huecos de cobertura")

st.caption(
    "Un solo mapa con tres capas superpuestas: escuelas, aristas del complejo "
    "Vietoris-Rips al radio elegido, y los ciclos H₁ detectados como huecos de cobertura."
)

NIVELES_DISP = ["preescolar", "primaria", "secundaria",
                "media_superior", "media_tecnica", "todas"]

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Selección")
    niv = st.selectbox("Nivel", NIVELES_DISP, index=1)
    eps = st.slider("ε — radio del complejo (m)", 0, 4000, 800, 50,
                    help="Mismo slider que en la página Complejos Simpliciales.")
    top_k = st.slider("Top-K huecos H₁", 1, 10, 5)

    st.divider()
    st.subheader("Capas del mapa")
    show_schools = st.checkbox("Escuelas (puntos)", value=True)
    show_edges   = st.checkbox("Aristas del complejo VR", value=True)
    show_cycles  = st.checkbox("Ciclos H₁ detectados", value=True)
    show_holes   = st.checkbox("Círculos de hueco (radio = persistencia/2)", value=True)

    MAX_EDGES = st.slider("Máx. aristas a dibujar", 500, 8000, 3000, 500,
                          help="Limita cuántas aristas VR se pintan (las más cortas primero).")

# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------
df = load_escuelas()
r  = load_tda(niv)

if r is None:
    st.warning(f"No hay datos TDA para '{niv}'.")
    st.stop()

X      = r["X"]          # puntos UTM submuestreados
dgms   = r["dgms"]
thresh = r["thresh"]
cocycles_raw = r.get("cocycles", [])

color  = NIVEL_COLOR.get(niv, "#444444")
holes  = top_h1_with_cocycles(r, k=top_k)

# Métricas rápidas ----------------------------------------------------------
tree  = cKDTree(X)
pairs = list(tree.query_pairs(r=float(eps)))
n_edges = len(pairs)

# Betti en ε actual
eps_grid = np.linspace(10, thresh, 100)
betti    = betti_curves(dgms, eps_grid)
ref_idx  = int(np.argmin(np.abs(eps_grid - eps)))
b0_ref, b1_ref = int(betti[ref_idx, 0]), int(betti[ref_idx, 1])
holes_alive = [h for h in holes if h["birth"] <= eps <= h["death"]]

c1, c2, c3, c4 = st.columns(4)
c1.metric("β₀ (componentes)", b0_ref)
c2.metric("β₁ (huecos activos)", b1_ref)
c3.metric("|E| aristas", f"{n_edges:,}")
c4.metric("Huecos activos (top-K)", len(holes_alive))

# ---------------------------------------------------------------------------
# Construcción del mapa
# ---------------------------------------------------------------------------
m = base_map(zoom=11)

# --- Capa 1: escuelas -------------------------------------------------------
if show_schools:
    sub = df if niv == "todas" else df[df["nivel"] == niv]
    sample = sub.sample(min(1000, len(sub)), random_state=0)
    school_layer = folium.FeatureGroup(name="Escuelas", show=True)
    for _, row in sample.iterrows():
        folium.CircleMarker(
            [row["latitud"], row["longitud"]],
            radius=3, color=color, fill=True, fill_opacity=0.65, weight=0,
            tooltip=f"{row['nivel']} · {row['sector']}",
        ).add_to(school_layer)
    school_layer.add_to(m)

# --- Capa 2: aristas del complejo VR ----------------------------------------
if show_edges and eps > 0:
    edge_layer = folium.FeatureGroup(name=f"Complejo VR ε={eps} m", show=True)

    draw_pairs = pairs
    if n_edges > MAX_EDGES:
        # ordenar por longitud y tomar las más cortas
        lengths = np.array([
            np.linalg.norm(X[i] - X[j]) for i, j in pairs
        ])
        order = np.argsort(lengths)[:MAX_EDGES]
        draw_pairs = [pairs[k] for k in order]
        st.caption(
            f"Se muestran las {MAX_EDGES:,} aristas más cortas de {n_edges:,} totales. "
            "Sube el límite en el sidebar para ver más."
        )

    for i, j in draw_pairs:
        la, lo = utm_to_latlon(X[i, 0], X[i, 1])
        lb, mob = utm_to_latlon(X[j, 0], X[j, 1])
        folium.PolyLine(
            [[la, lo], [lb, mob]],
            color=color, weight=1.2, opacity=0.35,
        ).add_to(edge_layer)

    edge_layer.add_to(m)

# --- Capa 3: ciclos H₁ (aristas del representante del ciclo) ---------------
if show_cycles and len(cocycles_raw) > 1:
    dgm1 = dgms[1]
    deaths = np.where(np.isfinite(dgm1[:, 1]), dgm1[:, 1], thresh)
    pers   = deaths - dgm1[:, 0]
    order  = np.argsort(-pers)[:top_k]

    HOLE_COLORS = ["#e41a1c", "#377eb8", "#ff7f00",
                   "#4daf4a", "#984ea3", "#a65628",
                   "#f781bf", "#999999", "#8dd3c7", "#fb8072"]

    cycle_layer = folium.FeatureGroup(name="Ciclos H₁ (representantes)", show=True)
    for rank, idx in enumerate(order):
        if idx >= len(cocycles_raw[1]):
            continue
        coc = cocycles_raw[1][idx]          # (n_aristas, 3): [i, j, coeff]
        if len(coc) == 0:
            continue
        hcolor = HOLE_COLORS[rank % len(HOLE_COLORS)]
        alive  = dgm1[idx, 0] <= eps <= deaths[idx]
        opacity = 0.9 if alive else 0.3
        weight  = 3.5 if alive else 1.5

        for edge in coc[:, :2].astype(int):
            vi, vj = int(edge[0]), int(edge[1])
            if vi >= len(X) or vj >= len(X):
                continue
            la, lo  = utm_to_latlon(X[vi, 0], X[vi, 1])
            lb, mob = utm_to_latlon(X[vj, 0], X[vj, 1])
            folium.PolyLine(
                [[la, lo], [lb, mob]],
                color=hcolor, weight=weight, opacity=opacity,
                tooltip=f"Ciclo H₁ #{rank+1} · pers={pers[idx]:.0f} m · "
                        f"{'ACTIVO' if alive else 'inactivo'} en ε={eps}m",
            ).add_to(cycle_layer)

    cycle_layer.add_to(m)

# --- Capa 4: círculos de hueco (radio = persistencia / 2) ------------------
if show_holes and holes:
    hole_layer = folium.FeatureGroup(name="Huecos H₁ (círculos)", show=True)
    HOLE_COLORS = ["#e41a1c", "#377eb8", "#ff7f00",
                   "#4daf4a", "#984ea3", "#a65628",
                   "#f781bf", "#999999", "#8dd3c7", "#fb8072"]
    for rank, h in enumerate(holes):
        lat, lon = utm_to_latlon(*h["centroid_xy"])
        hcolor   = HOLE_COLORS[rank % len(HOLE_COLORS)]
        alive    = h["birth"] <= eps <= h["death"]
        folium.Circle(
            [lat, lon],
            radius=max(h["pers"] / 2, 100),
            color=hcolor,
            fill=True,
            fill_opacity=0.18 if alive else 0.06,
            weight=2.5 if alive else 1,
            dash_array=None if alive else "6 4",
            popup=folium.Popup(
                f"<b>Hueco #{rank+1}</b><br>"
                f"birth: {h['birth']:.0f} m<br>"
                f"death: {h['death']:.0f} m<br>"
                f"persistencia: {h['pers']:.0f} m<br>"
                f"vértices del ciclo: {h['n_verts']}<br>"
                f"<b>{'ACTIVO en ε actual' if alive else 'inactivo en ε actual'}</b>",
                max_width=220,
            ),
        ).add_to(hole_layer)
        folium.CircleMarker(
            [lat, lon], radius=5, color=hcolor, fill=True, fill_opacity=0.9,
            tooltip=f"#{rank+1} pers={h['pers']:.0f}m",
        ).add_to(hole_layer)
    hole_layer.add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
map_col, info_col = st.columns([3, 1])

with map_col:
    st_folium(m, height=640, use_container_width=True, returned_objects=[])

with info_col:
    st.subheader("Leyenda")
    st.markdown(
        f"<span style='color:{color}'>●</span> **Escuelas** — {niv}",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<span style='color:{color}; opacity:0.4'>─</span> **Aristas VR** a ε = {eps} m",
        unsafe_allow_html=True,
    )

    HOLE_COLORS_LEG = ["#e41a1c", "#377eb8", "#ff7f00",
                       "#4daf4a", "#984ea3", "#a65628",
                       "#f781bf", "#999999", "#8dd3c7", "#fb8072"]
    for rank, h in enumerate(holes):
        alive = h["birth"] <= eps <= h["death"]
        hc = HOLE_COLORS_LEG[rank % len(HOLE_COLORS_LEG)]
        badge = "⬤ activo" if alive else "○ inactivo"
        st.markdown(
            f"<span style='color:{hc}'>{badge}</span> "
            f"**Hueco #{rank+1}** — {h['pers']:.0f} m",
            unsafe_allow_html=True,
        )

    st.divider()
    st.caption(
        "Los **ciclos coloreados** son los representantes topológicos de cada "
        "hueco H₁. El **círculo** muestra el área de cobertura deficiente "
        "(radio = persistencia/2). En ε actual, los huecos activos aparecen "
        "sólidos; los inactivos, punteados y transparentes."
    )

# ---------------------------------------------------------------------------
# Barcode compacto debajo del mapa
# ---------------------------------------------------------------------------
st.subheader("Barcode H₁ — ventana de vida de cada hueco")

if holes:
    fig = go.Figure()
    for rank, h in enumerate(holes):
        alive = h["birth"] <= eps <= h["death"]
        hc = HOLE_COLORS_LEG[rank % len(HOLE_COLORS_LEG)]
        fig.add_trace(go.Scatter(
            x=[h["birth"], h["death"]], y=[rank, rank],
            mode="lines",
            line=dict(color=hc, width=8 if alive else 4),
            opacity=1.0 if alive else 0.35,
            showlegend=False,
            hovertemplate=(
                f"Hueco #{rank+1}<br>"
                f"birth: {h['birth']:.0f} m · death: {h['death']:.0f} m<br>"
                f"persistencia: {h['pers']:.0f} m<extra></extra>"
            ),
        ))
        fig.add_trace(go.Scatter(
            x=[h["birth"]], y=[rank], mode="markers",
            marker=dict(color=hc, size=9, symbol="circle"),
            showlegend=False, hoverinfo="skip",
        ))

    fig.add_vline(x=eps, line=dict(color="gray", dash="dash", width=2),
                  annotation_text=f"ε = {eps} m", annotation_position="top right")
    fig.update_yaxes(
        tickmode="array",
        tickvals=list(range(len(holes))),
        ticktext=[f"#{i+1}  {h['pers']:.0f} m" for i, h in enumerate(holes)],
    )
    fig.update_xaxes(title_text="ε — radio (m)")
    fig.update_layout(
        height=60 + len(holes) * 38,
        margin=dict(l=10, r=20, t=10, b=30),
        plot_bgcolor="white",
        hovermode="y unified",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Barras sólidas = huecos activos en el ε seleccionado. "
        "Al subir ε, el complejo VR se densifica y los huecos aparecen "
        "(nacen) y luego se rellenan con triángulos (mueren)."
    )
