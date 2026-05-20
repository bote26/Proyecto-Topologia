"""Visualización del complejo Vietoris-Rips a medida que crece ε."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import plotly.graph_objects as go
import streamlit as st
from scipy.spatial import cKDTree

from utils.data_loader import NIVEL_COLOR, NIVELES, SECTORES, load_escuelas
from utils.tda import landmark_sample

st.set_page_config(page_title="Complejos Simpliciales", page_icon="🔵", layout="wide")
st.title("🔵 Complejos Simpliciales — animación de ε")

df = load_escuelas()

with st.sidebar:
    st.header("Selección")
    niv = st.selectbox("Nivel", ["todas", *NIVELES], index=2)
    sec = st.selectbox("Sector", ["ambos", *SECTORES])
    max_pts = st.slider("Puntos máx (submuestreo)", 50, 600, 250, 50,
                        help="Más puntos = más aristas y mapa más lento.")
    eps = st.slider("ε — radio (m)", 0, 4000, 800, 50)
    show_disks = st.checkbox("Mostrar discos de radio ε/2 (Čech)", True)

sub = df.copy()
if niv != "todas":
    sub = sub[sub["nivel"] == niv]
if sec != "ambos":
    sub = sub[sub["sector"] == sec]
st.caption(f"{len(sub):,} escuelas en la selección")

if len(sub) == 0:
    st.info("Sin datos para la selección actual.")
    st.stop()

X = sub[["x_utm", "y_utm"]].values
Xs = landmark_sample(X, max_n=max_pts)

# Aristas del Vietoris-Rips: pares (i, j) con dist(i, j) <= eps
edges = []
if eps > 0 and len(Xs) > 1:
    tree = cKDTree(Xs)
    pairs = tree.query_pairs(r=eps)
    edges = list(pairs)

# Triángulos (2-simplices) — sólo si pocos puntos para no congelar el browser
triangles = []
if len(Xs) <= 200 and eps > 0:
    edge_set = set(edges)
    n = len(Xs)
    for i, j in edges:
        for k in range(j + 1, n):
            if (i, k) in edge_set and (j, k) in edge_set:
                triangles.append((i, j, k))

color = NIVEL_COLOR.get(niv, "#444")

fig = go.Figure()

# 1) Discos (Čech)
if show_disks and eps > 0:
    theta = np.linspace(0, 2 * np.pi, 30)
    cx = np.cos(theta) * (eps / 2)
    cy = np.sin(theta) * (eps / 2)
    for x, y in Xs:
        fig.add_trace(go.Scatter(
            x=cx + x, y=cy + y, fill="toself", mode="lines",
            line=dict(color=color, width=0), opacity=0.10,
            hoverinfo="skip", showlegend=False,
        ))

# 2) Triángulos
for i, j, k in triangles:
    fig.add_trace(go.Scatter(
        x=[Xs[i, 0], Xs[j, 0], Xs[k, 0], Xs[i, 0]],
        y=[Xs[i, 1], Xs[j, 1], Xs[k, 1], Xs[i, 1]],
        fill="toself", mode="lines",
        line=dict(color=color, width=0), opacity=0.25,
        hoverinfo="skip", showlegend=False,
    ))

# 3) Aristas
if edges:
    ex, ey = [], []
    for i, j in edges:
        ex += [Xs[i, 0], Xs[j, 0], None]
        ey += [Xs[i, 1], Xs[j, 1], None]
    fig.add_trace(go.Scatter(
        x=ex, y=ey, mode="lines",
        line=dict(color=color, width=1.2), opacity=0.6,
        hoverinfo="skip", showlegend=False,
    ))

# 4) Vértices
fig.add_trace(go.Scatter(
    x=Xs[:, 0], y=Xs[:, 1], mode="markers",
    marker=dict(color=color, size=5), name="escuelas",
    hovertemplate="x=%{x:.0f}<br>y=%{y:.0f}<extra></extra>",
))

fig.update_layout(
    title=f"Vietoris-Rips a ε = {eps} m  ·  |V|={len(Xs)}  |E|={len(edges)}  |T|={len(triangles)}",
    xaxis=dict(scaleanchor="y", title="x UTM (m)"),
    yaxis=dict(title="y UTM (m)"),
    height=700, margin=dict(l=20, r=20, t=50, b=20),
    plot_bgcolor="white",
)
st.plotly_chart(fig, use_container_width=True)

with st.expander("¿Cómo se lee esto?"):
    st.markdown("""
- Cada punto es una escuela (en coordenadas UTM, metros).
- A radio ε aparecen aristas entre escuelas cuyas distancias son ≤ ε.
- Cuando 3 escuelas forman un triángulo cerrado, aparece la cara
  (2-símplex sombreado).
- Los discos de radio ε/2 (opcional) muestran la intuición del complejo
  de Čech: dos discos se intersectan ⇔ hay una arista en el complejo
  de Čech (que para puntos en el plano es muy parecido al Vietoris-Rips).
- Mueve el slider para ver cómo nacen y se cierran los **huecos**.
""")
