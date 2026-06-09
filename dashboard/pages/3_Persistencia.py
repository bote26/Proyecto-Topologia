"""Diagramas de persistencia, barcode y curvas de Betti."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import streamlit as st

from utils.data_loader import NIVELES, SECTORES, load_escuelas
from utils.plotting import barcode, betti_curve_fig, persistence_diagram
from utils.tda import betti_curves, compute_for_points

st.set_page_config(page_title="Persistencia", page_icon="📈", layout="wide")
st.title("📈 Homología persistente")

df = load_escuelas()

# ── Caché: recalcula solo cuando cambian los puntos o parámetros TDA ──────────
@st.cache_data(show_spinner=False)
def _compute(pts_bytes: bytes, n_pts: int, thresh: int, max_n: int):
    pts = np.frombuffer(pts_bytes, dtype=np.float64).reshape(n_pts, 2)
    return compute_for_points(pts, thresh=thresh, max_n=max_n)

with st.sidebar:
    st.header("Filtros")
    nivs = st.multiselect("Niveles", NIVELES, default=["primaria"])
    secs = st.multiselect("Sectores", SECTORES, default=SECTORES)
    thresh = st.slider("Umbral ε (m)", 500, 5000, 3000, 100)
    max_n = st.slider("Submuestreo (landmarks)", 200, 2000, 800, 100)

    sub = df[df["nivel"].isin(nivs) & df["sector"].isin(secs)]
    st.caption(f"**{len(sub):,}** escuelas seleccionadas")

if len(nivs) == 0 or len(secs) == 0:
    st.info("Selecciona al menos un nivel y un sector.")
    st.stop()
if len(sub) < 3:
    st.error("Necesito al menos 3 escuelas con los filtros actuales.")
    st.stop()

label = "+".join(nivs) + " · " + "+".join(secs)

with st.spinner("Calculando Vietoris-Rips…"):
    pts = sub[["x_utm", "y_utm"]].values.astype(np.float64)
    r = _compute(pts.tobytes(), len(pts), thresh, max_n)

if r is None:
    st.error("El cálculo no produjo resultados. Intenta aumentar el umbral ε o el submuestreo.")
    st.stop()

dgms = r["dgms"]
thresh = r["thresh"]
st.markdown(f"**{label}** — n original = {r['X_original_n']:,}, "
            f"submuestreado a {len(r['X'])}, umbral = {thresh:.0f} m")

c1, c2, c3, c4 = st.columns(4)
c1.metric("H₀ features", len(dgms[0]))
c2.metric("H₁ features", len(dgms[1]))
if len(dgms[1]):
    deaths = np.where(np.isfinite(dgms[1][:, 1]), dgms[1][:, 1], thresh)
    pers = deaths - dgms[1][:, 0]
    c3.metric("Hueco más persistente", f"{pers.max():.0f} m")
    c4.metric("Persistencia media (H₁)", f"{pers.mean():.0f} m")

tab1, tab2, tab3 = st.tabs(["Diagrama", "Barcode H₁", "Curvas de Betti"])
with tab1:
    st.plotly_chart(persistence_diagram(dgms, thresh), use_container_width=True)
with tab2:
    st.plotly_chart(barcode(dgms, thresh, dim=1), use_container_width=True)
with tab3:
    eps = np.linspace(0, thresh, 200)
    bc = betti_curves(dgms, eps)
    st.plotly_chart(betti_curve_fig(eps, bc), use_container_width=True)

with st.expander("¿Cómo interpretar el diagrama?"):
    st.markdown("""
- Cada punto es una **feature topológica**: H₀ son componentes conectadas,
  H₁ son huecos (1-ciclos).
- Eje X = ε en que **nace** la feature, eje Y = ε en que **muere**.
- Puntos lejos de la diagonal = features persistentes (ruido más cerca).
- En H₁ una feature con `death - birth = 1.2 km` indica un **hueco de
  ~1.2 km de diámetro** en la red de cobertura escolar.
""")