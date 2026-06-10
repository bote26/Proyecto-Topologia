"""Entrada principal del dashboard — página de inicio ejecutiva."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.data_loader import load_escuelas, load_tda, NIVEL_COLOR
from utils.filters import filter_df, render_global_filters, tda_key
from utils.tda import top_h1_with_cocycles
from utils.geo import enriquecer_huecos
from utils.plotting import utm_to_latlon


# ── Helper: nivel más ausente cerca de un centroide ──────────────────────────
def _nivel_mas_ausente(centroid_xy: np.ndarray, df_full: pd.DataFrame) -> tuple[str, int]:
    """Devuelve (nivel, distancia_m) del nivel educativo más lejano al centroide."""
    from scipy.spatial import cKDTree
    max_dist, nivel_out = -1.0, "—"
    for niv, grp in df_full.groupby("nivel"):
        pts = grp[["x_utm", "y_utm"]].values
        if len(pts) == 0:
            continue
        dist = float(cKDTree(pts).query(centroid_xy, k=1)[0])
        if dist > max_dist:
            max_dist, nivel_out = dist, niv
    return nivel_out, int(max_dist)

st.set_page_config(
    page_title="TDA — Escuelas CDMX",
    page_icon=None,
    layout="wide",
)

niveles, sectores = render_global_filters()

df  = load_escuelas()
dff = filter_df(df, niveles, sectores)

# Cargar TDA según niveles seleccionados
_tda_key = tda_key(niveles)
r_todas = load_tda(_tda_key)
top_holes = []
max_pers  = 0.0
n_h1_total = 0
if r_todas is not None:
    _holes    = top_h1_with_cocycles(r_todas, k=10)
    top_holes = enriquecer_huecos(_holes, df)
    n_h1_total = len(r_todas["dgms"][1])
    if n_h1_total > 0:
        d = np.where(np.isfinite(r_todas["dgms"][1][:,1]),
                     r_todas["dgms"][1][:,1], r_todas["thresh"])
        max_pers = float((d - r_todas["dgms"][1][:,0]).max())

# ── Encabezado principal ──────────────────────────────────────────────────────
st.markdown(
    "<h1 style='margin-bottom:4px'>Análisis topológico de escuelas — CDMX</h1>"
    "<p style='color:#666;font-size:15px;margin-top:0'>Reto MA2007B · "
    "Geometría y Topología para Ciencia de Datos · DENUE 2025 (INEGI)</p>",
    unsafe_allow_html=True,
)

# ── Hallazgo principal ────────────────────────────────────────────────────────
if top_holes:
    h1  = top_holes[0]
    alc = h1.get("alcaldia", "CDMX")
    st.markdown(
        f"<div style='background:#1B4F72;color:white;border-radius:8px;"
        f"padding:18px 24px;margin-bottom:20px'>"
        f"<span style='font-size:13px;text-transform:uppercase;letter-spacing:1px;"
        f"opacity:0.8'>Hallazgo principal</span><br>"
        f"<span style='font-size:22px;font-weight:700'>"
        f"El hueco de cobertura más crítico tiene {max_pers:.0f} m de persistencia "
        f"y se localiza en <u>{alc}</u>.</span><br>"
        f"<span style='font-size:14px;opacity:0.85;margin-top:6px;display:block'>"
        f"Una zona de ~{max_pers/2:.0f} m de radio sin acceso escolar "
        f"incluso conectando todas las escuelas circundantes. "
        f"K-Means y DBSCAN no detectan este déficit.</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

# ── KPIs ─────────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Escuelas analizadas",  f"{len(dff):,}")
c2.metric("Alcaldías cubiertas",  dff["municipio"].nunique())
c3.metric("Niveles seleccionados", dff["nivel"].nunique())
c4.metric("Huecos H₁ detectados", f"{n_h1_total:,}" if r_todas else "—", help="Calculado sobre todos los niveles y sectores")
c5.metric("Mayor persistencia",   f"{max_pers:.0f} m" if max_pers else "—", help="Calculado sobre todos los niveles y sectores")

st.caption(f"Escuelas, alcaldías y niveles responden a todos los filtros. Huecos H\u2081 y persistencia calculados sobre: {_tda_key}.")

st.divider()

# ── Contenido principal ───────────────────────────────────────────────────────
col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader("Distribución de escuelas por nivel y alcaldía")
    st.caption("Responde a los filtros del sidebar.")
    top_alc = (
        dff.groupby(["municipio", "nivel"])
           .size()
           .reset_index(name="n")
    )
    top10 = dff["municipio"].value_counts().head(10).index.tolist()
    top_alc = top_alc[top_alc["municipio"].isin(top10)]

    fig_dist = px.bar(
        top_alc.sort_values("n", ascending=False),
        x="municipio", y="n", color="nivel",
        color_discrete_map=NIVEL_COLOR,
        labels={"municipio": "Alcaldía", "n": "Escuelas", "nivel": "Nivel"},
    )
    fig_dist.update_layout(
        plot_bgcolor="#FAFAFA", paper_bgcolor="white",
        height=360, margin=dict(l=10, r=10, t=10, b=80),
        legend=dict(orientation="h", y=-0.3),
        xaxis_tickangle=-35,
    )
    st.plotly_chart(fig_dist, use_container_width=True,
                    config={"displaylogo": False, "scrollZoom": True})

with col_right:
    st.subheader("Top 3 huecos más críticos")
    HOLE_COLORS = ["#C0392B","#E67E22","#1A5276","#117A65","#6C3483",
                   "#7D6608","#2E86C1","#935116","#1E8449","#922B21"]
    crit_color  = {"Alta": "#C0392B", "Media": "#E67E22", "Baja": "#2E86C1"}
    if top_holes:
        for i, h in enumerate(top_holes[:3]):
            alc  = h.get("alcaldia", "—")
            crit = "Alta" if h["pers"] > 1500 else ("Media" if h["pers"] > 700 else "Baja")
            st.markdown(
                f"<div style='border-left:4px solid {HOLE_COLORS[i]};"
                f"border:1px solid #e0e0e0;border-radius:8px;"
                f"padding:12px 16px;margin-bottom:10px'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center'>"
                f"<span style='font-weight:700;font-size:15px'>Hueco H{i+1}</span>"
                f"<span style='background:{crit_color[crit]};color:white;border-radius:4px;"
                f"padding:2px 10px;font-size:12px;font-weight:600'>{crit}</span>"
                f"</div>"
                f"<div style='color:#333;margin-top:6px;font-size:13px'>"
                f"<b>Alcaldía:</b> {alc}<br>"
                f"<b>Persistencia:</b> {h['pers']:.0f} m &nbsp;·&nbsp; "
                f"<b>Radio:</b> ~{h['pers']/2:.0f} m<br>"
                f"<b>Vértices del ciclo:</b> {h['n_verts']}"
                f"</div></div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("Cargando datos TDA…")

    st.subheader("Escuelas por sector")
    sec_counts = dff["sector"].value_counts().reset_index()
    sec_counts.columns = ["sector", "n"]
    fig_sec = px.pie(
        sec_counts, names="sector", values="n",
        color="sector",
        color_discrete_map={"público": "#1B4F72", "privado": "#2E86C1"},
        hole=0.4,
    )
    fig_sec.update_traces(textinfo="percent+label", textfont_size=13)
    fig_sec.update_layout(
        height=230, margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="white",
        showlegend=False,
    )
    st.plotly_chart(fig_sec, use_container_width=True,
                    config={"displaylogo": False})

st.divider()

# ── Escuelas por alcaldía ─────────────────────────────────────────────────────
st.subheader("Análisis por alcaldía")

# Preparar datos — todas las alcaldías ordenadas por total
alc_total = dff["municipio"].value_counts().reset_index()
alc_total.columns = ["municipio", "total"]
alc_order = alc_total["municipio"].tolist()

# Sector por alcaldía
alc_sector = (
    dff.groupby(["municipio", "sector"])
       .size()
       .reset_index(name="n")
)
alc_sector["municipio"] = pd.Categorical(
    alc_sector["municipio"], categories=alc_order, ordered=True
)
alc_sector = alc_sector.sort_values("municipio")

# Nivel por alcaldía
alc_nivel = (
    dff.groupby(["municipio", "nivel"])
       .size()
       .reset_index(name="n")
)
alc_nivel["municipio"] = pd.Categorical(
    alc_nivel["municipio"], categories=alc_order, ordered=True
)
alc_nivel = alc_nivel.sort_values("municipio")

ch1, ch2 = st.columns(2)

with ch1:
    st.markdown("**Público vs Privado por alcaldía**")
    fig_sec_alc = px.bar(
        alc_sector,
        x="n", y="municipio", color="sector",
        orientation="h",
        color_discrete_map={"público": "#1B4F72", "privado": "#2E86C1"},
        labels={"n": "Escuelas", "municipio": "", "sector": "Sector"},
        text_auto=True,
    )
    fig_sec_alc.update_traces(textfont_size=10, textposition="inside")
    fig_sec_alc.update_layout(
        plot_bgcolor="#FAFAFA", paper_bgcolor="white",
        height=420, margin=dict(l=10, r=20, t=10, b=30),
        legend=dict(orientation="h", y=-0.08, title=None),
        xaxis=dict(title="Escuelas", showgrid=True, gridcolor="#EFEFEF"),
        yaxis=dict(autorange="reversed"),
        barmode="stack",
    )
    st.plotly_chart(fig_sec_alc, use_container_width=True,
                    config={"displaylogo": False, "scrollZoom": True})

with ch2:
    st.markdown("**Nivel educativo por alcaldía**")
    fig_niv_alc = px.bar(
        alc_nivel,
        x="n", y="municipio", color="nivel",
        orientation="h",
        color_discrete_map=NIVEL_COLOR,
        labels={"n": "Escuelas", "municipio": "", "nivel": "Nivel"},
        text_auto=True,
    )
    fig_niv_alc.update_traces(textfont_size=9, textposition="inside")
    fig_niv_alc.update_layout(
        plot_bgcolor="#FAFAFA", paper_bgcolor="white",
        height=420, margin=dict(l=10, r=20, t=10, b=30),
        legend=dict(orientation="h", y=-0.08, title=None),
        xaxis=dict(title="Escuelas", showgrid=True, gridcolor="#EFEFEF"),
        yaxis=dict(autorange="reversed"),
        barmode="stack",
    )
    st.plotly_chart(fig_niv_alc, use_container_width=True,
                    config={"displaylogo": False, "scrollZoom": True})

st.divider()

# ── Análisis extendido de huecos H₁ ──────────────────────────────────────────
st.subheader("Análisis de huecos de cobertura — Top 10")
st.caption(f"Nivel analizado: {_tda_key}. Para filtros combinados ve a la pestaña Huecos de Cobertura.")

if top_holes:
    # Construir DataFrame de huecos
    holes_rows = []
    for i, h in enumerate(top_holes):
        lat, lon = utm_to_latlon(*h["centroid_xy"])
        crit = "Alta" if h["pers"] > 1500 else ("Media" if h["pers"] > 700 else "Baja")
        niv_aus, dist_aus = _nivel_mas_ausente(h["centroid_xy"], df)
        holes_rows.append({
            "Hueco":            f"H{i+1}",
            "Alcaldía":         h.get("alcaldia", "—"),
            "Nivel más ausente": niv_aus,
            "Dist. al nivel (m)": dist_aus,
            "Persistencia (m)": int(h["pers"]),
            "Radio aprox (m)":  int(h["pers"] / 2),
            "Birth (m)":        int(h["birth"]),
            "Death (m)":        int(h["death"]),
            "Vértices":         h["n_verts"],
            "Latitud":          round(lat, 5),
            "Longitud":         round(lon, 5),
            "Criticidad":       crit,
        })
    df_h = pd.DataFrame(holes_rows)

    # ── Fila de métricas rápidas ──────────────────────────────────────────────
    hm1, hm2, hm3, hm4 = st.columns(4)
    hm1.metric("Huecos en top 10", len(df_h))
    hm2.metric("Alcaldías afectadas", df_h["Alcaldía"].nunique())
    hm3.metric("Persistencia promedio", f"{df_h['Persistencia (m)'].mean():.0f} m")
    hm4.metric("Radio promedio", f"{df_h['Radio aprox (m)'].mean():.0f} m")

    # ── Tabla + gráficas ──────────────────────────────────────────────────────
    col_tab, col_charts = st.columns([1, 2])

    with col_tab:
        def _crit_style(val):
            if val == "Alta":  return "color:#922B21;font-weight:600"
            if val == "Media": return "color:#7D6608;font-weight:600"
            return "color:#1A5276;font-weight:600"
        st.dataframe(
            df_h[["Hueco","Alcaldía","Nivel más ausente","Dist. al nivel (m)","Persistencia (m)","Radio aprox (m)","Criticidad"]]
               .style.map(_crit_style, subset=["Criticidad"]),
            use_container_width=True, hide_index=True, height=390,
        )

    with col_charts:
        # Gráfica 1: barras de persistencia
        bar_colors = ["#C0392B" if c=="Alta" else "#E67E22" if c=="Media"
                      else "#2E86C1" for c in df_h["Criticidad"]]
        fig_hbar = go.Figure()
        fig_hbar.add_trace(go.Bar(
            x=df_h["Hueco"], y=df_h["Persistencia (m)"],
            marker=dict(color=bar_colors, line=dict(color="white", width=1.5)),
            text=[f"{v} m" for v in df_h["Persistencia (m)"]],
            textposition="outside",
            hovertemplate="<b>%{x}</b> — %{y} m<extra></extra>",
        ))
        fig_hbar.update_layout(
            plot_bgcolor="#FAFAFA", paper_bgcolor="white",
            font=dict(family="Arial", size=11),
            title=dict(text="<b>Persistencia por hueco</b>"
                            "<br><sup style='color:#888'>Rojo=Alta · Naranja=Media · Azul=Baja</sup>",
                       font=dict(size=12)),
            xaxis=dict(showgrid=False),
            yaxis=dict(title="Persistencia (m)", showgrid=True, gridcolor="#EFEFEF"),
            margin=dict(l=10, r=10, t=50, b=10),
            height=185, showlegend=False,
        )
        st.plotly_chart(fig_hbar, use_container_width=True,
                        config={"displaylogo": False, "scrollZoom": True})

        # Gráfica 2: birth vs death (mini diagrama de persistencia)
        fig_bd = go.Figure()
        max_val = df_h["Death (m)"].max() * 1.05
        fig_bd.add_trace(go.Scatter(
            x=[0, max_val], y=[0, max_val], mode="lines",
            line=dict(color="#BBBBBB", dash="dot", width=1),
            hoverinfo="skip", showlegend=False,
        ))
        fig_bd.add_trace(go.Scatter(
            x=df_h["Birth (m)"], y=df_h["Death (m)"],
            mode="markers+text",
            marker=dict(size=14, color=bar_colors,
                        line=dict(color="white", width=2)),
            text=df_h["Hueco"],
            textposition="top center",
            textfont=dict(size=10),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Birth: %{x} m<br>Death: %{y} m<br>"
                "Persistencia: %{customdata} m<extra></extra>"
            ),
            customdata=df_h["Persistencia (m)"],
            showlegend=False,
        ))
        fig_bd.update_layout(
            plot_bgcolor="#FAFAFA", paper_bgcolor="white",
            font=dict(family="Arial", size=11),
            title=dict(text="<b>Diagrama Birth–Death</b>"
                            "<br><sup style='color:#888'>Más alejado de la diagonal = más persistente</sup>",
                       font=dict(size=12)),
            xaxis=dict(title="Birth (m)", showgrid=True, gridcolor="#EFEFEF"),
            yaxis=dict(title="Death (m)", showgrid=True, gridcolor="#EFEFEF"),
            margin=dict(l=10, r=10, t=50, b=10),
            height=185,
        )
        st.plotly_chart(fig_bd, use_container_width=True,
                        config={"displaylogo": False, "scrollZoom": True})

    # ── Persistencia acumulada por alcaldía ───────────────────────────────────
    st.markdown("**Persistencia acumulada por alcaldía** — indica dónde se concentra el déficit de cobertura")
    alc_pers = (
        df_h.groupby("Alcaldía")
            .agg(huecos=("Hueco","count"),
                 pers_total=("Persistencia (m)","sum"),
                 pers_max=("Persistencia (m)","max"))
            .reset_index()
            .sort_values("pers_total", ascending=False)
    )
    c_left, c_right = st.columns([1, 2])
    with c_left:
        st.dataframe(alc_pers.rename(columns={
            "huecos": "Huecos", "pers_total": "Pers. total (m)", "pers_max": "Pers. máx (m)"
        }), use_container_width=True, hide_index=True)

    with c_right:
        fig_alc = go.Figure()
        fig_alc.add_trace(go.Bar(
            x=alc_pers["Alcaldía"], y=alc_pers["pers_total"],
            marker=dict(color="#1B4F72", line=dict(color="white", width=1.5)),
            text=[f"{v:,} m" for v in alc_pers["pers_total"]],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Persistencia total: %{y:,} m<extra></extra>",
        ))
        fig_alc.add_trace(go.Scatter(
            x=alc_pers["Alcaldía"], y=alc_pers["pers_max"],
            mode="markers",
            marker=dict(size=10, color="#C0392B", symbol="diamond"),
            name="Máx. individual",
            hovertemplate="<b>%{x}</b><br>Hueco máximo: %{y:,} m<extra></extra>",
        ))
        fig_alc.update_layout(
            plot_bgcolor="#FAFAFA", paper_bgcolor="white",
            font=dict(family="Arial", size=11),
            title=dict(text="<b>Persistencia acumulada y máxima por alcaldía</b>",
                       font=dict(size=12)),
            xaxis=dict(showgrid=False, tickangle=-25),
            yaxis=dict(title="Persistencia (m)", showgrid=True, gridcolor="#EFEFEF"),
            margin=dict(l=10, r=10, t=45, b=60),
            height=280, showlegend=True,
            legend=dict(orientation="h", y=-0.35),
        )
        st.plotly_chart(fig_alc, use_container_width=True,
                        config={"displaylogo": False, "scrollZoom": True})
else:
    st.info("No hay datos TDA disponibles.")

st.divider()

# ── Navegación ────────────────────────────────────────────────────────────────
st.subheader("Navegación")
n1, n2, n3, n4, n5 = st.columns(5)
for col, icon, title, desc in [
    (n1, "1", "Panorama",            "Mapa interactivo con filtros por alcaldía y nivel."),
    (n2, "2", "Complejos Simpliciales", "Animación VR y Čech a medida que crece ε."),
    (n3, "3", "Persistencia",         "Diagramas, barcode y curvas de Betti."),
    (n4, "4", "Huecos de Cobertura",  "Huecos H₁ en el mapa + sugerencia de inversión."),
    (n5, "5", "TDA vs Clustering",    "Comparativa con K-Means y DBSCAN."),
]:
    col.markdown(
        f"<div style='border:1px solid #e0e0e0;border-radius:8px;"
        f"padding:14px;text-align:center;height:110px'>"
        f"<div style='font-size:22px;font-weight:700;color:#1B4F72'>{icon}</div>"
        f"<div style='font-weight:600;font-size:13px;margin:4px 0'>{title}</div>"
        f"<div style='font-size:11px;color:#666'>{desc}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

with st.expander("Leyenda de colores por nivel"):
    for nv, c in NIVEL_COLOR.items():
        st.markdown(
            f"<span style='display:inline-block;width:12px;height:12px;"
            f"background:{c};border-radius:2px;margin-right:6px'></span>**{nv}**",
            unsafe_allow_html=True,
        )