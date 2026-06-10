"""Filtros globales compartidos entre todas las páginas vía st.session_state."""
from __future__ import annotations
import streamlit as st
from .data_loader import NIVELES, SECTORES

NIVEL_KEY  = "global_nivel"
SECTOR_KEY = "global_sector"


def _init():
    # Inicializar o resetear si hay valores inválidos (e.g. "publico" sin acento)
    if NIVEL_KEY not in st.session_state or not all(
            v in NIVELES for v in st.session_state[NIVEL_KEY]):
        st.session_state[NIVEL_KEY] = NIVELES[:]
    if SECTOR_KEY not in st.session_state or not all(
            v in SECTORES for v in st.session_state[SECTOR_KEY]):
        st.session_state[SECTOR_KEY] = SECTORES[:]


def render_global_filters() -> tuple[list[str], list[str]]:
    """Renderiza filtros globales con multiselect. Devuelve (niveles, sectores)."""
    _init()
    st.sidebar.markdown("**Filtros globales**")
    st.sidebar.caption("Se aplican en todas las páginas.")

    niveles = st.sidebar.multiselect(
        "Nivel educativo",
        NIVELES,
        key=NIVEL_KEY,
        default=st.session_state[NIVEL_KEY],
    )
    sectores = st.sidebar.multiselect(
        "Sector",
        SECTORES,
        key=SECTOR_KEY,
        default=st.session_state[SECTOR_KEY],
    )

    # Evitar selección vacía
    if not niveles:
        niveles = NIVELES[:]
        st.sidebar.warning("Selecciona al menos un nivel.")
    if not sectores:
        sectores = SECTORES[:]
        st.sidebar.warning("Selecciona al menos un sector.")

    st.sidebar.divider()
    return niveles, sectores


def filter_df(df, niveles: list[str], sectores: list[str]):
    """Filtra el DataFrame por los niveles y sectores seleccionados."""
    return df[df["nivel"].isin(niveles) & df["sector"].isin(sectores)].copy()


def tda_key(niveles: list[str]) -> str:
    """Devuelve la clave del pkl TDA a cargar según los niveles seleccionados."""
    if len(niveles) == 1:
        return niveles[0]
    return "todas"
