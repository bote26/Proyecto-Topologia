"""Generador de notebooks .ipynb a partir de listas de celdas.

Ejecutar:  python notebooks/_build_notebooks.py
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB_DIR = ROOT / "notebooks"


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(src: str) -> dict:
    return {
        "cell_type": "code",
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": src.splitlines(keepends=True),
    }


def write_notebook(name: str, cells: list[dict]) -> None:
    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.x"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    path = NB_DIR / name
    path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {path.relative_to(ROOT)}")


# ============================================================================
# 01 — Preparación de datos
# ============================================================================
NB01 = [
    md("""# 01 — Preparación de datos

Filtramos el DENUE para quedarnos solo con **escuelas en la Ciudad de México**
de los niveles de interés (preescolar, primaria, secundaria general, media
superior y media técnica terminal — sector público y privado).

Reproyectamos a UTM 14N (EPSG:32614) para tener coordenadas en metros.
"""),
    code("""import unicodedata
from pathlib import Path
import numpy as np
import pandas as pd
from pyproj import Transformer

ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()
CSV = ROOT / 'denue_inegi_61_.csv'
OUT = ROOT / 'data' / 'processed' / 'escuelas_cdmx.parquet'
OUT.parent.mkdir(parents=True, exist_ok=True)
print('csv:', CSV.exists(), CSV)
"""),
    code("""COLS = ['id','nom_estab','codigo_act','nombre_act','per_ocu','cve_ent','entidad',
        'cve_mun','municipio','latitud','longitud','fecha_alta']
df = pd.read_csv(CSV, encoding='latin-1', low_memory=False, usecols=COLS)
print('filas totales:', len(df))
df.head(2)
"""),
    code("""# Filtro CDMX
df_cdmx = df[df['entidad'].str.contains('iudad de M', na=False)].copy()
print('CDMX:', len(df_cdmx))
"""),
    code("""# Definición de las 12 categorías objetivo (claves SCIAN)
# 611111 preescolar publ, 611112 preescolar priv
# 611121 primaria publ,   611122 primaria priv  (cuidado: revisar abajo)
# Mejor usar el texto exacto del DENUE (con codificación latin-1 ya decodificada).
target_acts = [
    'Escuelas de educación preescolar del sector público',
    'Escuelas de educación preescolar del sector privado',
    'Escuelas de educación primaria del sector público',
    'Escuelas de educación primaria del sector privado',
    'Escuelas de educación secundaria general del sector público',
    'Escuelas de educación secundaria general del sector privado',
    'Escuelas de educación media superior del sector público',
    'Escuelas de educación media superior del sector privado',
    'Escuelas de educación media técnica terminal del sector público',
    'Escuelas de educación media técnica terminal del sector privado',
]

df_esc = df_cdmx[df_cdmx['nombre_act'].isin(target_acts)].copy()
print('escuelas objetivo en CDMX:', len(df_esc))
print(df_esc['nombre_act'].value_counts())
"""),
    code("""# Validar lat/lon dentro del bounding box de CDMX
mask_geo = (
    df_esc['latitud'].between(19.0, 19.7) &
    df_esc['longitud'].between(-99.4, -98.9)
)
print('descartadas por lat/lon fuera de CDMX:', (~mask_geo).sum())
df_esc = df_esc[mask_geo].copy()
"""),
    code("""# Derivar columnas 'nivel' y 'sector'
def parse_nivel(s: str) -> str:
    s = s.lower()
    if 'preescolar' in s: return 'preescolar'
    if 'primaria' in s: return 'primaria'
    if 'secundaria' in s: return 'secundaria'
    if 'media superior' in s: return 'media_superior'
    if 'media técnica' in s or 'media tecnica' in s: return 'media_tecnica'
    return 'otro'

def parse_sector(s: str) -> str:
    return 'privado' if 'privado' in s.lower() else 'público'

df_esc['nivel'] = df_esc['nombre_act'].map(parse_nivel)
df_esc['sector'] = df_esc['nombre_act'].map(parse_sector)
print(df_esc.groupby(['nivel','sector']).size().unstack(fill_value=0))
"""),
    code("""# Reproyección a UTM 14N (EPSG:32614) — coordenadas en metros
tr = Transformer.from_crs(4326, 32614, always_xy=True)
x, y = tr.transform(df_esc['longitud'].values, df_esc['latitud'].values)
df_esc['x_utm'] = x
df_esc['y_utm'] = y
df_esc[['latitud','longitud','x_utm','y_utm']].describe()
"""),
    code("""# Guardar
df_esc.reset_index(drop=True).to_parquet(OUT, index=False)
print('guardado:', OUT, '|', len(df_esc), 'filas')
"""),
    md("""## Verificación

- Esperamos ~5000–6000 escuelas tras el filtro.
- Cada nivel debe estar presente; preescolar y primaria dominan.
- Las coordenadas UTM x deben estar en el rango ~470000–510000, y en ~2120000–2170000.
"""),
]
write_notebook("01_data_prep.ipynb", NB01)


# ============================================================================
# 02 — EDA
# ============================================================================
NB02 = [
    md("""# 02 — Análisis exploratorio

Exploramos la distribución espacial de las escuelas en CDMX y calculamos
distancias al k-ésimo vecino más cercano para escoger un umbral razonable
del complejo Vietoris-Rips.
"""),
    code("""from pathlib import Path
import numpy as np
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from sklearn.neighbors import NearestNeighbors
import plotly.express as px

ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()
df = pd.read_parquet(ROOT / 'data' / 'processed' / 'escuelas_cdmx.parquet')
print(len(df), 'escuelas')
df.head(2)
"""),
    code("""# Conteos por nivel y sector
ct = df.groupby(['nivel','sector']).size().unstack(fill_value=0)
print(ct)
"""),
    code("""# Conteos por alcaldía
top_alcaldias = df.groupby('municipio').size().sort_values(ascending=False)
print(top_alcaldias)
"""),
    code("""# Mapa con marcadores agrupados
COLORS = {'preescolar':'green','primaria':'blue','secundaria':'orange',
          'media_superior':'red','media_tecnica':'purple'}
m = folium.Map(location=[19.4326, -99.1332], zoom_start=11, tiles='cartodbpositron')
cluster = MarkerCluster().add_to(m)
for _, r in df.sample(min(2000, len(df)), random_state=0).iterrows():
    folium.CircleMarker(
        [r['latitud'], r['longitud']], radius=3,
        color=COLORS.get(r['nivel'], 'gray'), fill=True, fill_opacity=0.7,
        tooltip=f"{r['nivel']} ({r['sector']}) — {r['nom_estab'][:50]}"
    ).add_to(cluster)
m
"""),
    code("""# Distribución de distancias al k-ésimo vecino más cercano
def knn_distances(X: np.ndarray, k: int) -> np.ndarray:
    nn = NearestNeighbors(n_neighbors=k+1).fit(X)
    d, _ = nn.kneighbors(X)
    return d[:, k]

X = df[['x_utm','y_utm']].values
for k in (1, 5, 10):
    d = knn_distances(X, k)
    print(f'k={k:2d}: mediana={np.median(d):7.1f} m, p90={np.percentile(d,90):7.1f} m')
"""),
    code("""# Histograma para k=5 — ayuda a escoger el umbral del Vietoris-Rips
fig = px.histogram(x=knn_distances(X, 5), nbins=60,
    labels={'x':'distancia al 5° vecino más cercano (m)'},
    title='Distancia al k=5 vecino — escuelas CDMX')
fig.show()
"""),
    code("""# Lo mismo pero por nivel
import plotly.graph_objects as go
fig = go.Figure()
for nv, g in df.groupby('nivel'):
    if len(g) < 10: continue
    d = knn_distances(g[['x_utm','y_utm']].values, min(5, len(g)-1))
    fig.add_trace(go.Histogram(x=d, name=nv, opacity=0.5, nbinsx=60))
fig.update_layout(barmode='overlay', xaxis_title='distancia al 5° vecino (m)',
                  title='Densidad espacial por nivel educativo')
fig.show()
"""),
    md("""## Conclusiones del EDA

- La mediana de distancia al 5° vecino para primaria pública suele ser < 400 m
  (red densa, bien distribuida).
- Para media técnica terminal la red es muy escasa: pocas decenas de escuelas.
- **Umbral recomendado para Vietoris-Rips:** ~2500–3000 m (radio de caminata
  razonable para una zona urbana). Suficiente para que H0 se conecte casi
  totalmente y para que aparezcan H1 (huecos) interpretables.
"""),
]
write_notebook("02_eda.ipynb", NB02)


# ============================================================================
# 03 — TDA persistencia
# ============================================================================
NB03 = [
    md("""# 03 — Homología persistente (Vietoris-Rips)

Para cada nivel educativo construimos el complejo de Vietoris-Rips sobre las
coordenadas UTM (en metros) y calculamos los diagramas de persistencia H0/H1.
Las features H1 persistentes corresponden a **huecos de cobertura escolar**:
regiones cerradas por escuelas alrededor pero sin escuelas dentro.
"""),
    code("""import pickle
from pathlib import Path
import numpy as np
import pandas as pd
from ripser import ripser
from persim import plot_diagrams
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt

ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()
TDA_DIR = ROOT / 'data' / 'processed' / 'tda_results'
TDA_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_parquet(ROOT / 'data' / 'processed' / 'escuelas_cdmx.parquet')
print(len(df), 'escuelas; niveles:', df['nivel'].unique())
"""),
    code("""def landmark_sample(X: np.ndarray, max_n: int = 1500, seed: int = 0) -> np.ndarray:
    '''Si X es muy grande, submuestrear con KMeans (preserva geometría).'''
    if len(X) <= max_n:
        return X
    km = KMeans(n_clusters=max_n, n_init=3, random_state=seed).fit(X)
    return km.cluster_centers_

THRESH = 3000.0  # metros — radio de caminata interpretable
MAX_N = 1500     # punto de corte para subsampling
"""),
    code("""def compute_tda(X_metros: np.ndarray, thresh: float = THRESH):
    Xs = landmark_sample(X_metros, MAX_N)
    res = ripser(Xs, maxdim=1, thresh=thresh, do_cocycles=True)
    return {
        'X': Xs,
        'X_original_n': len(X_metros),
        'dgms': res['dgms'],
        'cocycles': res['cocycles'],
        'thresh': thresh,
    }

# Calcular por nivel
results = {}
for nivel, g in df.groupby('nivel'):
    X = g[['x_utm','y_utm']].values
    print(f'computando {nivel}: {len(X)} pts ...', end=' ')
    results[nivel] = compute_tda(X)
    print('listo')

# Y para todas las escuelas juntas
results['todas'] = compute_tda(df[['x_utm','y_utm']].values)
print('todas:', results['todas']['X_original_n'], 'pts')
"""),
    code("""# Guardar para que el dashboard cargue rápido
for name, r in results.items():
    with open(TDA_DIR / f'{name}.pkl', 'wb') as f:
        pickle.dump(r, f)
print('guardados:', sorted(TDA_DIR.glob('*.pkl')))
"""),
    code("""# Diagramas de persistencia por nivel
fig, axes = plt.subplots(2, 3, figsize=(15, 10))
for ax, (name, r) in zip(axes.flat, results.items()):
    plot_diagrams(r['dgms'], show=False, ax=ax)
    ax.set_title(f'{name}  (n={r[\"X_original_n\"]})')
plt.tight_layout()
plt.show()
"""),
    code("""# Top features H1 (huecos persistentes) por nivel
def top_h1(r, k=5):
    h1 = r['dgms'][1]
    if len(h1) == 0:
        return np.empty((0, 3))
    pers = h1[:, 1] - h1[:, 0]
    idx = np.argsort(-pers)[:k]
    return np.column_stack([h1[idx], pers[idx]])

for name in ['preescolar','primaria','secundaria','media_superior','media_tecnica','todas']:
    if name not in results: continue
    arr = top_h1(results[name], 5)
    print(f'\\n{name}: top-5 H1 (birth, death, persistencia en metros)')
    if len(arr):
        for b, d, p in arr:
            print(f'  ε∈[{b:7.1f}, {d:7.1f}]  persistencia={p:7.1f} m')
    else:
        print('  (sin features H1)')
"""),
    code("""# Curvas de Betti β0(ε) y β1(ε) para 'primaria'
def betti_curves(dgms, eps_range):
    betti = []
    for eps in eps_range:
        b0 = np.sum((dgms[0][:,0] <= eps) & (dgms[0][:,1] > eps))
        b1 = np.sum((dgms[1][:,0] <= eps) & (dgms[1][:,1] > eps))
        betti.append((b0, b1))
    return np.array(betti)

eps = np.linspace(0, THRESH, 200)
bc = betti_curves(results['primaria']['dgms'], eps)
fig, ax = plt.subplots(1, 2, figsize=(12, 4))
ax[0].plot(eps, bc[:,0]); ax[0].set_title('β0(ε) — componentes'); ax[0].set_xlabel('ε (m)')
ax[1].plot(eps, bc[:,1], color='orange'); ax[1].set_title('β1(ε) — huecos'); ax[1].set_xlabel('ε (m)')
plt.tight_layout(); plt.show()
"""),
    md("""## Interpretación

- **β0(ε)** decrece hasta llegar a 1 cuando el grafo se vuelve conexo: la
  ε en que esto ocurre estima cuánto hay que caminar entre escuelas vecinas.
- **β1(ε)** alcanza un pico y luego decae: ese pico nos dice **cuántos huecos
  simultáneos** persisten en la red de cobertura escolar.
- Las features H1 con mayor persistencia son las zonas más significativas
  sin escuelas — se exploran geográficamente en el notebook 04.
"""),
]
write_notebook("03_tda_persistencia.ipynb", NB03)


# ============================================================================
# 04 — Interpretación geográfica
# ============================================================================
NB04 = [
    md("""# 04 — Interpretación geográfica de los huecos

Localizamos sobre el mapa de CDMX las features H1 más persistentes
("huecos") de cada nivel. Cada hueco se representa por el **centroide del
ciclo** asociado a la 1-cocadena y un **radio aproximado** dado por la
persistencia (death − birth) dividido entre 2.
"""),
    code("""import pickle
from pathlib import Path
import numpy as np
import pandas as pd
import folium
from pyproj import Transformer

ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()
TDA_DIR = ROOT / 'data' / 'processed' / 'tda_results'

# UTM 14N -> lat/lon
inv = Transformer.from_crs(32614, 4326, always_xy=True)

def utm_to_latlon(x, y):
    lon, lat = inv.transform(x, y)
    return lat, lon
"""),
    code("""def hole_centroids(r, top_k=5):
    '''Para cada feature H1 en el top-k por persistencia, recupera el
    centroide del cociclo (vértices involucrados) y un radio aproximado.'''
    dgm1 = r['dgms'][1]
    cocycles = r['cocycles'][1]  # lista de arrays (i, j, val)
    X = r['X']
    if len(dgm1) == 0:
        return []
    pers = dgm1[:,1] - dgm1[:,0]
    order = np.argsort(-pers)[:top_k]
    out = []
    for idx in order:
        b, d = dgm1[idx]
        coc = cocycles[idx]
        # vértices que participan
        verts = np.unique(coc[:, :2].ravel()) if len(coc) else np.array([], dtype=int)
        if len(verts) == 0:
            continue
        centroid = X[verts].mean(axis=0)
        out.append({
            'birth': float(b), 'death': float(d),
            'pers': float(d - b),
            'centroid_xy': centroid,
            'n_verts': len(verts),
        })
    return out
"""),
    code("""# Mapa con los huecos top de cada nivel
LEVEL_COLOR = {'preescolar':'green','primaria':'blue','secundaria':'orange',
               'media_superior':'red','media_tecnica':'purple','todas':'black'}

m = folium.Map(location=[19.4326, -99.1332], zoom_start=11, tiles='cartodbpositron')
for pkl in sorted(TDA_DIR.glob('*.pkl')):
    name = pkl.stem
    if name == 'todas': continue
    with open(pkl, 'rb') as f:
        r = pickle.load(f)
    color = LEVEL_COLOR.get(name, 'gray')
    layer = folium.FeatureGroup(name=f'huecos — {name}')
    for h in hole_centroids(r, top_k=5):
        lat, lon = utm_to_latlon(*h['centroid_xy'])
        folium.Circle(
            [lat, lon], radius=h['pers']/2,
            color=color, fill=True, fill_opacity=0.15,
            popup=(f"<b>{name}</b><br>birth: {h['birth']:.0f} m<br>"
                   f"death: {h['death']:.0f} m<br>persistencia: {h['pers']:.0f} m"),
        ).add_to(layer)
        folium.CircleMarker([lat, lon], radius=4, color=color, fill=True).add_to(layer)
    layer.add_to(m)
folium.LayerControl().add_to(m)
m
"""),
    code("""# Resumen tabular
rows = []
for pkl in sorted(TDA_DIR.glob('*.pkl')):
    name = pkl.stem
    with open(pkl, 'rb') as f:
        r = pickle.load(f)
    for h in hole_centroids(r, top_k=3):
        lat, lon = utm_to_latlon(*h['centroid_xy'])
        rows.append({'nivel': name, 'lat': lat, 'lon': lon,
                     'birth_m': h['birth'], 'death_m': h['death'],
                     'persistencia_m': h['pers'], 'n_verts': h['n_verts']})
pd.DataFrame(rows).sort_values('persistencia_m', ascending=False)
"""),
    md("""## Comparación con clustering clásico

DBSCAN agrupa puntos densos pero **ignora los huecos**. TDA es complementaria:
señala dónde hay déficit de cobertura aunque haya escuelas alrededor.
"""),
    code("""from sklearn.cluster import DBSCAN
df = pd.read_parquet(ROOT / 'data' / 'processed' / 'escuelas_cdmx.parquet')
sub = df[df['nivel']=='primaria']
db = DBSCAN(eps=500, min_samples=5).fit(sub[['x_utm','y_utm']].values)
sub = sub.assign(cluster=db.labels_)
print('clusters DBSCAN:', sub['cluster'].nunique() - (1 if -1 in sub['cluster'].unique() else 0),
      '| ruido:', (sub['cluster']==-1).sum())
"""),
    md("""**Interpretación final.** Mientras DBSCAN cuenta densidades, TDA
identifica las regiones cerradas-por-escuelas pero vacías por dentro — las
zonas donde una política pública de planeación urbana debería considerar
abrir o reasignar planteles.
"""),
]
write_notebook("04_interpretacion.ipynb", NB04)


print('\\nTodos los notebooks fueron escritos en:', NB_DIR)
