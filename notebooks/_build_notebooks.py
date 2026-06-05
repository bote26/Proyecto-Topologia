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
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

# Estilo de gráficos
plt.rcParams.update({
    'figure.dpi': 110,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.grid': True,
    'grid.alpha': 0.25,
    'font.size': 11,
})

ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()
TDA_DIR = ROOT / 'data' / 'processed' / 'tda_results'
TDA_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_parquet(ROOT / 'data' / 'processed' / 'escuelas_cdmx.parquet')
print(len(df), 'escuelas; niveles:', df['nivel'].unique())

# Paleta consistente con el dashboard
NIVEL_COLOR = {
    'preescolar':     '#2ca02c',
    'primaria':       '#1f77b4',
    'secundaria':     '#ff7f0e',
    'media_superior': '#d62728',
    'media_tecnica':  '#9467bd',
    'todas':          '#444444',
}
"""),
    code("""THRESH = 3000.0  # metros — radio de caminata interpretable
# Sin submuestreo: el complejo Vietoris-Rips se construye sobre TODAS las escuelas.
"""),
    code("""def compute_tda(X_metros: np.ndarray, thresh: float = THRESH):
    res = ripser(X_metros, maxdim=1, thresh=thresh, do_cocycles=True)
    return {
        'X': X_metros,
        'X_original_n': len(X_metros),
        'dgms': res['dgms'],
        'cocycles': res['cocycles'],
        'thresh': thresh,
    }

# Calcular por nivel (sobre todas las escuelas del nivel, sin submuestrear)
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
    md("""## 1. Distribución espacial de las escuelas

Antes de mirar los diagramas, vale la pena ver dónde están los puntos. Los
huecos H₁ que aparezcan más adelante deben corresponder visualmente a
regiones rodeadas por puntos pero vacías por dentro.
"""),
    code("""# Scatter espacial por nivel — coordenadas UTM en km para legibilidad
ORDEN = ['preescolar','primaria','secundaria','media_superior','media_tecnica','todas']
fig, axes = plt.subplots(2, 3, figsize=(15, 9), sharex=True, sharey=True)
for ax, name in zip(axes.flat, ORDEN):
    if name == 'todas':
        sub = df
    else:
        sub = df[df['nivel'] == name]
    color = NIVEL_COLOR[name]
    ax.scatter(sub['x_utm']/1000, sub['y_utm']/1000,
               s=4, c=color, alpha=0.45, edgecolors='none')
    ax.set_title(f'{name}  ·  n={len(sub):,}', fontsize=11)
    ax.set_aspect('equal')
    ax.set_xlabel('x UTM (km)')
    ax.set_ylabel('y UTM (km)')
fig.suptitle('Escuelas de CDMX por nivel educativo', y=1.01, fontsize=13)
plt.tight_layout()
plt.show()
"""),
    md("""## 2. Diagramas de persistencia

Cada punto del diagrama es una **feature topológica**. El eje X es la escala
ε en que la feature *nace*, el eje Y la escala en que *muere*. Las features
lejos de la diagonal son las que persisten más — son las relevantes.
"""),
    code("""# Diagramas de persistencia mejorados — H0 y H1 superpuestos por nivel
def plot_pd(ax, dgms, thresh, title, color_h1='#d62728'):
    # diagonal
    ax.plot([0, thresh], [0, thresh], '--', color='gray', lw=1, alpha=0.6)
    ax.fill_between([0, thresh], [0, thresh], thresh,
                    color='gray', alpha=0.04)
    # H0
    h0 = dgms[0].copy()
    h0[~np.isfinite(h0[:,1]), 1] = thresh
    ax.scatter(h0[:,0], h0[:,1], s=18, c='#1f77b4',
               alpha=0.55, edgecolors='none', label=f'H₀ (n={len(dgms[0])})')
    # H1
    h1 = dgms[1].copy()
    inf_mask = ~np.isfinite(h1[:,1])
    h1[inf_mask, 1] = thresh
    # Tamaño proporcional a persistencia (más persistente => más grande)
    pers1 = h1[:,1] - h1[:,0]
    sizes = 25 + 120 * (pers1 / max(pers1.max(), 1))
    ax.scatter(h1[~inf_mask,0], h1[~inf_mask,1],
               s=sizes[~inf_mask], c=color_h1, alpha=0.75,
               edgecolors='black', linewidths=0.4,
               label=f'H₁ (n={len(dgms[1])})')
    # H1 con muerte infinita: marcamos como triángulo en el techo
    if inf_mask.any():
        ax.scatter(h1[inf_mask,0], h1[inf_mask,1],
                   s=sizes[inf_mask], c=color_h1, marker='^',
                   edgecolors='black', linewidths=0.4, alpha=0.9,
                   label='H₁ (muerte = ∞)')
    ax.set_title(title)
    ax.set_xlabel('birth ε (m)')
    ax.set_ylabel('death ε (m)')
    ax.set_xlim(-50, thresh*1.02)
    ax.set_ylim(-50, thresh*1.06)
    ax.legend(loc='lower right', fontsize=8, framealpha=0.9)

fig, axes = plt.subplots(2, 3, figsize=(16, 10))
for ax, name in zip(axes.flat, ORDEN):
    r = results[name]
    plot_pd(ax, r['dgms'], r['thresh'],
            f"{name}  (n={r['X_original_n']:,})",
            color_h1=NIVEL_COLOR[name])
fig.suptitle('Diagramas de persistencia — tamaño ∝ persistencia',
             y=1.01, fontsize=13)
plt.tight_layout()
plt.show()
"""),
    md("""## 3. Barcode H₁ — vida de los huecos

Cada barra horizontal es un hueco. Va desde su `birth` hasta su `death`.
Barras largas = huecos persistentes (estructura topológica robusta);
barras cortas = ruido.
"""),
    code("""# Barcode H1 por nivel (top-15 más persistentes)
def plot_barcode(ax, dgm1, thresh, title, color):
    if len(dgm1) == 0:
        ax.text(0.5, 0.5, '(sin H₁)', ha='center', va='center',
                transform=ax.transAxes, color='gray')
        ax.set_title(title); ax.set_yticks([]); return
    h1 = dgm1.copy()
    inf_mask = ~np.isfinite(h1[:,1])
    h1[inf_mask, 1] = thresh
    pers = h1[:,1] - h1[:,0]
    order = np.argsort(-pers)[:15]
    h1 = h1[order]; inf_mask = inf_mask[order]
    y = np.arange(len(h1))
    for i, ((b, d), is_inf) in enumerate(zip(h1, inf_mask)):
        ax.hlines(y[i], b, d, colors=color, lw=3,
                  alpha=0.85 if not is_inf else 0.55)
        if is_inf:
            ax.plot(d, y[i], marker='>', color=color, markersize=7)
    ax.set_yticks([])
    ax.set_xlabel('ε (m)')
    ax.set_xlim(0, thresh*1.02)
    ax.set_title(title)
    ax.invert_yaxis()

fig, axes = plt.subplots(2, 3, figsize=(16, 9))
for ax, name in zip(axes.flat, ORDEN):
    r = results[name]
    plot_barcode(ax, r['dgms'][1], r['thresh'],
                 f'{name}  ·  top-15 H₁', NIVEL_COLOR[name])
fig.suptitle('Barcode de huecos H₁ (las barras más largas = huecos más persistentes)',
             y=1.01, fontsize=13)
plt.tight_layout()
plt.show()
"""),
    md("""## 4. Persistencia vs nacimiento (lifetime plot)

Otra manera útil de mirar lo mismo: en el eje Y graficamos la **persistencia**
(`death − birth`). Los puntos altos son los huecos más significativos. Una
banda horizontal de “ruido” aparece pegada a y ≈ 0.
"""),
    code("""# Lifetime plot — un panel por nivel
fig, axes = plt.subplots(2, 3, figsize=(16, 9), sharey=True)
for ax, name in zip(axes.flat, ORDEN):
    r = results[name]; thresh = r['thresh']
    h1 = r['dgms'][1]
    if len(h1) == 0:
        ax.text(0.5, 0.5, '(sin H₁)', ha='center', va='center',
                transform=ax.transAxes, color='gray')
        ax.set_title(name); continue
    deaths = np.where(np.isfinite(h1[:,1]), h1[:,1], thresh)
    pers = deaths - h1[:,0]
    # umbral de ruido: 25% del máximo (heurística visual)
    cutoff = 0.25 * pers.max()
    ax.scatter(h1[:,0], pers, s=18, c=NIVEL_COLOR[name],
               alpha=0.7, edgecolors='none')
    ax.axhline(cutoff, ls='--', color='gray', lw=0.8)
    ax.text(thresh*0.98, cutoff, '  ruido →', ha='right', va='bottom',
            fontsize=8, color='gray')
    ax.set_xlabel('birth ε (m)')
    ax.set_title(f'{name}  ·  máx persistencia = {pers.max():.0f} m')
axes[0,0].set_ylabel('persistencia (m)')
axes[1,0].set_ylabel('persistencia (m)')
fig.suptitle('Lifetime plot — persistencia vs nacimiento',
             y=1.01, fontsize=13)
plt.tight_layout()
plt.show()
"""),
    md("""## 5. Top features H₁ — los huecos más significativos

Tabla con los 5 huecos más persistentes por nivel. La columna `persistencia`
es lo que mide qué tan robusto es el hueco a perturbaciones del umbral ε.
"""),
    code("""def top_h1_df(r, k=5):
    h1 = r['dgms'][1]
    if len(h1) == 0:
        return pd.DataFrame()
    deaths = np.where(np.isfinite(h1[:,1]), h1[:,1], r['thresh'])
    pers = deaths - h1[:,0]
    order = np.argsort(-pers)[:k]
    return pd.DataFrame({
        'birth_m': np.round(h1[order, 0], 1),
        'death_m': np.round(deaths[order], 1),
        'persistencia_m': np.round(pers[order], 1),
        'muerte_inf': ~np.isfinite(h1[order, 1]),
    })

tablas = []
for name in ORDEN:
    t = top_h1_df(results[name], k=5)
    if t.empty: continue
    t.insert(0, 'nivel', name)
    tablas.append(t)
top_h1_all = pd.concat(tablas, ignore_index=True)
top_h1_all
"""),
    code("""# Gráfico de barras: máxima persistencia H1 por nivel
maxpers = []
for name in ORDEN:
    h1 = results[name]['dgms'][1]
    thresh = results[name]['thresh']
    if len(h1) == 0:
        maxpers.append(0); continue
    deaths = np.where(np.isfinite(h1[:,1]), h1[:,1], thresh)
    maxpers.append((deaths - h1[:,0]).max())

fig, ax = plt.subplots(figsize=(9, 4.5))
bars = ax.bar(ORDEN, maxpers, color=[NIVEL_COLOR[n] for n in ORDEN],
              edgecolor='black', linewidth=0.4)
for bar, v in zip(bars, maxpers):
    ax.text(bar.get_x()+bar.get_width()/2, v+30,
            f'{v:.0f} m', ha='center', fontsize=9)
ax.set_ylabel('Persistencia máxima H₁ (m)')
ax.set_title('Tamaño del hueco más grande por nivel — proxy del déficit de cobertura')
ax.tick_params(axis='x', rotation=20)
plt.tight_layout()
plt.show()
"""),
    md("""## 6. Curvas de Betti β₀(ε) y β₁(ε)

- **β₀(ε)** = número de componentes conexas vivas a escala ε. Empieza igual
  al número de escuelas y baja a 1 cuando todo se conecta.
- **β₁(ε)** = número de huecos vivos. Sube, llega a un pico, y baja cuando
  los huecos se cubren.

El pico de β₁ indica a qué escala la red de cobertura tiene **más huecos
simultáneos** — un umbral natural de análisis.
"""),
    code("""def betti_curves(dgms, eps_range, thresh):
    betti = np.zeros((len(eps_range), 2), dtype=int)
    for i, eps in enumerate(eps_range):
        for dim in (0, 1):
            d = dgms[dim]
            if len(d) == 0: continue
            deaths = np.where(np.isfinite(d[:,1]), d[:,1], thresh + 1)
            alive = (d[:,0] <= eps) & (deaths > eps)
            betti[i, dim] = int(alive.sum())
    return betti

eps = np.linspace(0, THRESH, 300)

# Comparativa de β1 entre todos los niveles
fig, axes = plt.subplots(1, 2, figsize=(15, 5))

# Panel izquierdo: β0 normalizado (log scale)
for name in ORDEN:
    r = results[name]
    bc = betti_curves(r['dgms'], eps, r['thresh'])
    axes[0].plot(eps, bc[:, 0], color=NIVEL_COLOR[name], lw=1.8,
                 label=f'{name}')
axes[0].set_yscale('log')
axes[0].set_xlabel('ε (m)')
axes[0].set_ylabel('β₀(ε)  (escala log)')
axes[0].set_title('β₀ — componentes conexas')
axes[0].legend(fontsize=9, loc='upper right')

# Panel derecho: β1
for name in ORDEN:
    r = results[name]
    bc = betti_curves(r['dgms'], eps, r['thresh'])
    peak = eps[bc[:, 1].argmax()]
    peak_val = bc[:, 1].max()
    axes[1].plot(eps, bc[:, 1], color=NIVEL_COLOR[name], lw=2,
                 label=f'{name} (pico {peak_val} @ {peak:.0f} m)')
axes[1].set_xlabel('ε (m)')
axes[1].set_ylabel('β₁(ε)')
axes[1].set_title('β₁ — huecos simultáneos')
axes[1].legend(fontsize=8, loc='upper right')

plt.tight_layout()
plt.show()
"""),
    md("""## Interpretación

- **Diagramas y barcode** muestran que la mayoría de niveles tienen varios
  huecos con persistencia > 1 km — son zonas urbanas rodeadas pero sin
  escuela cercana de ese tipo.
- **β₀(ε)** decrece hasta 1 cuando el grafo se vuelve conexo: esa ε estima
  cuánto hay que caminar entre escuelas vecinas del mismo nivel.
- **β₁(ε)** alcanza un pico y luego decae: ese pico dice cuántos huecos
  simultáneos persisten en la red.
- El nivel con mayor persistencia H₁ máxima es el más vulnerable a
  reubicación de matrícula — se explora geográficamente en el notebook 04.
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
