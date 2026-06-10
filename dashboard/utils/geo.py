"""Utilidades geográficas: interpretación de coordenadas UTM → alcaldía."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


_tree: cKDTree | None = None
_df_ref: pd.DataFrame | None = None


def _build_tree(df: pd.DataFrame) -> None:
    global _tree, _df_ref
    _df_ref = df.reset_index(drop=True)
    _tree = cKDTree(_df_ref[["x_utm", "y_utm"]].values)


def alcaldia_de_punto(cx_utm: float, cy_utm: float, df: pd.DataFrame,
                      k_neighbors: int = 10) -> str:
    """Devuelve la alcaldía más frecuente entre los k vecinos más cercanos del punto."""
    global _tree, _df_ref
    if _tree is None or _df_ref is None:
        _build_tree(df)
    _, idxs = _tree.query([cx_utm, cy_utm], k=min(k_neighbors, len(df)))
    alcaldias = _df_ref.iloc[idxs]["municipio"].value_counts()
    return str(alcaldias.index[0])


def enriquecer_huecos(holes: list[dict], df: pd.DataFrame) -> list[dict]:
    """Añade 'alcaldia' a cada hueco usando el centroide UTM."""
    global _tree, _df_ref
    if _tree is None or _df_ref is None:
        _build_tree(df)
    out = []
    for h in holes:
        cx, cy = h["centroid_xy"]
        alc = alcaldia_de_punto(cx, cy, df)
        out.append({**h, "alcaldia": alc})
    return out
