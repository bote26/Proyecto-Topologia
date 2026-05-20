# Análisis topológico de escuelas en CDMX

Aplicación de **homología persistente** sobre la red de escuelas de la Ciudad
de México (DENUE 2025) para identificar zonas de cobertura, conectividad y
huecos persistentes en la red educativa.

Reto MA2007B — *Geometría y Topología para Ciencia de Datos*.

---

## Estructura

```
.
├── denue_inegi_61_.csv               # dataset DENUE (entrada)
├── data/processed/
│   ├── escuelas_cdmx.parquet         # filtrado limpio (lo genera 01)
│   └── tda_results/                  # pickles de persistencia (los genera 03)
├── notebooks/
│   ├── 01_data_prep.ipynb
│   ├── 02_eda.ipynb
│   ├── 03_tda_persistencia.ipynb
│   ├── 04_interpretacion.ipynb
│   └── _build_notebooks.py           # regenera los .ipynb desde código
├── dashboard/
│   ├── app.py                        # portada Streamlit
│   ├── pages/                        # páginas 1–4 (Panorama, Complejos,
│   │                                 #            Persistencia, Huecos)
│   └── utils/                        # data_loader, tda, plotting
├── requirements.txt
└── README.md
```

## Instalación

```powershell
pip install -r requirements.txt
```

## Pipeline

1. **Preparar datos** — ejecuta `notebooks/01_data_prep.ipynb`.
   Filtra DENUE para CDMX + escuelas (preescolar, primaria, secundaria
   general, media superior y media técnica terminal, ambos sectores),
   reproyecta a UTM 14N (EPSG:32614) y guarda `data/processed/escuelas_cdmx.parquet`.

2. **EDA** — `notebooks/02_eda.ipynb`. Conteos, mapas y distancias al
   k-ésimo vecino más cercano para escoger un umbral razonable del
   complejo Vietoris-Rips.

3. **TDA** — `notebooks/03_tda_persistencia.ipynb`. Calcula los diagramas
   de persistencia (H₀, H₁) por nivel con **Ripser** y los serializa en
   `data/processed/tda_results/*.pkl`. Submuestreo con KMeans landmarks
   cuando hay > 1500 puntos.

4. **Interpretación geográfica** — `notebooks/04_interpretacion.ipynb`.
   Localiza los huecos (features H₁ persistentes) sobre el mapa de CDMX.

> El parquet y los pickles ya están generados en `data/processed/`;
> los notebooks pueden re-ejecutarse desde cero en menos de 3 minutos.

## Dashboard

```powershell
streamlit run dashboard/app.py
```

Páginas:

| # | Página | Contenido |
|---|---|---|
| 1 | **📊 Panorama** | Mapa interactivo con filtros (nivel, sector, alcaldía) y conteos. |
| 2 | **🔵 Complejos Simpliciales** | Animación del complejo Vietoris-Rips a medida que crece ε; muestra discos de Čech, aristas y triángulos. |
| 3 | **📈 Persistencia** | Diagrama de persistencia, barcode H₁ y curvas de Betti. Modo *pre-computado* (instantáneo) o *recalcular* con filtros libres. |
| 4 | **🗺️ Huecos de Cobertura** | Centroides y radios de los huecos H₁ más persistentes — zonas con déficit potencial de cobertura escolar. |

## Decisiones metodológicas

- **Proyección:** UTM 14N (EPSG:32614) — las distancias del Vietoris-Rips
  se interpretan directamente en metros.
- **Umbral:** ε máx = 3000 m (radio de caminata urbano razonable).
- **Submuestreo:** KMeans landmarks (1500 puntos máximo) para mantener
  el costo computacional de Ripser O(N²) bajo control.
- **Librerías TDA:** `ripser` + `persim` (recomendado por el reto y
  rápido de instalar en Windows).
- **Localización de huecos:** centroide de los vértices que aparecen
  en la 1-cocadena devuelta por `ripser(..., do_cocycles=True)`.

## Datos

- Fuente: [DENUE — INEGI 2025](https://www.inegi.org.mx/app/mapa/denue/)
- Categorías SCIAN incluidas (12): preescolar/primaria/secundaria general/
  media superior/media técnica terminal × público/privado.
- Recorte geográfico: Ciudad de México (10,448 unidades económicas →
  5,587 tras filtros de categoría + bounding box).
