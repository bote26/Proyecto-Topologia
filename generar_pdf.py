"""
Script para generar documentación PDF completa del proyecto
Análisis Topológico de Escuelas en CDMX
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, white, grey
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.platypus.flowables import Flowable
import os

OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documentacion_proyecto.pdf")

# ─── Colores ─────────────────────────────────────────────────────────────────
AZUL_OSCURO   = HexColor("#1B3A5C")
AZUL_MEDIO    = HexColor("#2E6DA4")
AZUL_CLARO    = HexColor("#D6E8F7")
VERDE         = HexColor("#2ca02c")
NARANJA       = HexColor("#ff7f0e")
ROJO          = HexColor("#d62728")
PURPURA       = HexColor("#9467bd")
GRIS_CLARO    = HexColor("#F4F6F8")
GRIS_TABLA    = HexColor("#E8EEF4")
GRIS_BORDE    = HexColor("#C5CDD6")
NEGRO         = HexColor("#1A1A1A")

W, H = A4  # 595.27 x 841.89 pts


# ─── Estilos ─────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

TITLE = ParagraphStyle(
    "Title", fontName="Helvetica-Bold", fontSize=24,
    textColor=white, alignment=TA_CENTER, spaceAfter=6, leading=30
)
SUBTITLE = ParagraphStyle(
    "Subtitle", fontName="Helvetica", fontSize=13,
    textColor=white, alignment=TA_CENTER, spaceAfter=4, leading=18
)
H1 = ParagraphStyle(
    "H1", fontName="Helvetica-Bold", fontSize=16,
    textColor=white, alignment=TA_LEFT, spaceBefore=4, spaceAfter=4, leading=20
)
H2 = ParagraphStyle(
    "H2", fontName="Helvetica-Bold", fontSize=13,
    textColor=AZUL_OSCURO, spaceBefore=14, spaceAfter=6, leading=17
)
H3 = ParagraphStyle(
    "H3", fontName="Helvetica-Bold", fontSize=11,
    textColor=AZUL_MEDIO, spaceBefore=10, spaceAfter=4, leading=14
)
BODY = ParagraphStyle(
    "Body", fontName="Helvetica", fontSize=10,
    textColor=NEGRO, spaceBefore=3, spaceAfter=3, leading=14,
    alignment=TA_JUSTIFY
)
BODY_L = ParagraphStyle(
    "BodyL", fontName="Helvetica", fontSize=10,
    textColor=NEGRO, spaceBefore=2, spaceAfter=2, leading=14,
    alignment=TA_LEFT
)
CODE = ParagraphStyle(
    "Code", fontName="Courier", fontSize=8.5,
    textColor=HexColor("#1A3A1A"), backColor=HexColor("#F0F4F0"),
    spaceBefore=2, spaceAfter=2, leading=12,
    leftIndent=12, rightIndent=12,
    borderPad=6
)
BULLET = ParagraphStyle(
    "Bullet", fontName="Helvetica", fontSize=10,
    textColor=NEGRO, spaceBefore=2, spaceAfter=2, leading=14,
    leftIndent=18, bulletIndent=6
)
CAPTION = ParagraphStyle(
    "Caption", fontName="Helvetica-Oblique", fontSize=9,
    textColor=HexColor("#555555"), alignment=TA_CENTER, spaceAfter=4
)
META = ParagraphStyle(
    "Meta", fontName="Helvetica", fontSize=9,
    textColor=HexColor("#666666"), alignment=TA_CENTER, spaceAfter=2
)


# ─── Helpers ─────────────────────────────────────────────────────────────────
def sp(n=1):
    return Spacer(1, n * 0.35 * cm)


def hr(color=GRIS_BORDE, thickness=0.5):
    return HRFlowable(width="100%", thickness=thickness, color=color,
                      spaceAfter=4, spaceBefore=4)


def section_header(text, color=AZUL_OSCURO):
    """Banner coloreado de sección."""
    return Table(
        [[Paragraph(text, H1)]],
        colWidths=[W - 4 * cm],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), color),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (-1, -1), 14),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
            ("ROUNDEDCORNERS", [4]),
        ])
    )


def info_box(text, color=AZUL_CLARO, border=AZUL_MEDIO):
    """Caja de texto destacada."""
    return Table(
        [[Paragraph(text, BODY_L)]],
        colWidths=[W - 4 * cm],
        style=TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), color),
            ("BOX",           (0, 0), (-1, -1), 1.2, border),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (-1, -1), 12),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ])
    )


def simple_table(headers, rows, col_widths=None):
    """Tabla con encabezado azul y filas alternas."""
    data = [[Paragraph(str(h), ParagraphStyle(
        "TH", fontName="Helvetica-Bold", fontSize=9,
        textColor=white, alignment=TA_CENTER
    )) for h in headers]]
    for r in rows:
        data.append([Paragraph(str(c), ParagraphStyle(
            "TD", fontName="Helvetica", fontSize=9,
            textColor=NEGRO, alignment=TA_LEFT
        )) for c in r])

    n_cols = len(headers)
    if col_widths is None:
        col_widths = [(W - 4 * cm) / n_cols] * n_cols

    ts = TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), AZUL_OSCURO),
        ("TEXTCOLOR",     (0, 0), (-1, 0), white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID",          (0, 0), (-1, -1), 0.4, GRIS_BORDE),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 7),
    ])
    for i in range(1, len(data)):
        bg = GRIS_CLARO if i % 2 == 0 else white
        ts.add("BACKGROUND", (0, i), (-1, i), bg)

    return Table(data, colWidths=col_widths, style=ts, repeatRows=1)


def b(text):  return f"<b>{text}</b>"
def i(text):  return f"<i>{text}</i>"
def c(text):  return f"<font face='Courier' size=8>{text}</font>"
def colored(text, hex_color): return f"<font color='{hex_color}'>{text}</font>"


# ─── Construcción del PDF ────────────────────────────────────────────────────
def build_pdf():
    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.2*cm, bottomMargin=2.2*cm,
        title="Análisis Topológico de Escuelas en CDMX — Documentación",
        author="Proyecto Topología",
    )

    story = []

    # ══════════════════════════════════════════════════════════════════════════
    # PORTADA
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 1.5*cm))
    portada = Table(
        [
            [Paragraph("🏫 Análisis Topológico de", TITLE)],
            [Paragraph("Escuelas en CDMX", TITLE)],
            [Spacer(1, 0.4*cm)],
            [Paragraph("Documentación técnica completa del proyecto", SUBTITLE)],
            [Spacer(1, 0.3*cm)],
            [Paragraph("Dashboard interactivo · Homología Persistente · Análisis de Cobertura", SUBTITLE)],
        ],
        colWidths=[W - 4*cm],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), AZUL_OSCURO),
            ("TOPPADDING",    (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ("LEFTPADDING",   (0, 0), (-1, -1), 24),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 24),
            ("ROUNDEDCORNERS", [8]),
        ])
    )
    story.append(portada)
    story.append(sp(3))

    # Métricas de portada
    metricas = Table(
        [["5,587", "5", "16", "2"],
         ["Escuelas\nanalizadas", "Niveles\neducativos", "Alcaldías\ncubiertas", "Sectores\n(público/privado)"]],
        colWidths=[(W - 4*cm) / 4] * 4,
        style=TableStyle([
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, 0), 22),
            ("TEXTCOLOR",  (0, 0), (-1, 0), AZUL_MEDIO),
            ("FONTNAME",   (0, 1), (-1, 1), "Helvetica"),
            ("FONTSIZE",   (0, 1), (-1, 1), 9),
            ("TEXTCOLOR",  (0, 1), (-1, 1), HexColor("#555555")),
            ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("BACKGROUND", (0, 0), (-1, -1), GRIS_CLARO),
            ("BOX",        (0, 0), (-1, -1), 1, GRIS_BORDE),
            ("INNERGRID",  (0, 0), (-1, -1), 0.5, GRIS_BORDE),
        ])
    )
    story.append(metricas)
    story.append(sp(2))

    story.append(Paragraph(
        "Este documento describe en detalle cada componente del proyecto: datos de entrada, "
        "procesamiento, cálculos de homología persistente, visualizaciones del dashboard y "
        "metodología de identificación de zonas de déficit educativo.",
        BODY
    ))
    story.append(sp(1))
    story.append(Paragraph(b("Fuente de datos:") + " DENUE — Directorio Estadístico Nacional de Unidades Económicas (INEGI)", BODY_L))
    story.append(Paragraph(b("Tecnología principal:") + " Ripser (homología persistente), Streamlit (dashboard), Folium (mapas)", BODY_L))
    story.append(Paragraph(b("Rama matemática:") + " Análisis Topológico de Datos (TDA) — Homología persistente H₀ y H₁", BODY_L))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # 1. ESTRUCTURA DEL PROYECTO
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_header("1. Estructura del Proyecto"))
    story.append(sp())

    story.append(Paragraph("El proyecto está organizado en tres grandes áreas:", BODY))
    story.append(sp(0.5))

    arbol = [
        ("Proyecto-Topologia/", "Raíz"),
        ("  ├── denue_inegi_61_.csv", "Dataset crudo DENUE: 10,448 registros"),
        ("  ├── requirements.txt", "Dependencias Python (13 librerías)"),
        ("  ├── data/processed/", "Datos procesados y resultados TDA"),
        ("  │   ├── escuelas_cdmx.parquet", "5,587 escuelas filtradas y georreferenciadas"),
        ("  │   └── tda_results/", "6 pickles con diagramas de persistencia pre-calculados"),
        ("  │       ├── preescolar.pkl", "Resultados TDA nivel preescolar"),
        ("  │       ├── primaria.pkl", "Resultados TDA nivel primaria"),
        ("  │       ├── secundaria.pkl", "Resultados TDA nivel secundaria"),
        ("  │       ├── media_superior.pkl", "Resultados TDA nivel media superior"),
        ("  │       ├── media_tecnica.pkl", "Resultados TDA nivel media técnica"),
        ("  │       └── todas.pkl", "Resultados TDA con todos los niveles"),
        ("  ├── notebooks/", "Análisis exploratorio y cálculos paso a paso"),
        ("  │   ├── 01_data_prep.ipynb", "Preparación y limpieza de datos"),
        ("  │   ├── 02_eda.ipynb", "Análisis exploratorio y elección de parámetros"),
        ("  │   ├── 03_tda_persistencia.ipynb", "Cálculo de homología persistente"),
        ("  │   └── 04_interpretacion.ipynb", "Localización geográfica de huecos"),
        ("  └── dashboard/", "Aplicación web interactiva (Streamlit)"),
        ("      ├── app.py", "Portada con métricas globales"),
        ("      ├── pages/", "Páginas del dashboard"),
        ("      │   ├── 1_Panorama.py", "Mapa explorador con filtros"),
        ("      │   ├── 2_Complejos_Simpliciales.py", "Visualización del complejo Vietoris-Rips"),
        ("      │   ├── 3_Persistencia.py", "Diagramas de persistencia, barcodes, Betti"),
        ("      │   └── 4_Huecos_de_Cobertura.py", "Mapa de zonas con déficit educativo"),
        ("      └── utils/", "Módulos compartidos"),
        ("          ├── data_loader.py", "Carga de datos y caché"),
        ("          ├── tda.py", "Motor de cálculo TDA"),
        ("          └── plotting.py", "Funciones de visualización"),
    ]

    for ruta, desc in arbol:
        row_txt = (
            f"<font face='Courier' size='8' color='#1A3A1A'>{ruta}</font>"
            + ("  " if desc else "")
            + (f"<font face='Helvetica' size='8' color='#555555'>{desc}</font>" if desc else "")
        )
        story.append(Paragraph(row_txt, ParagraphStyle(
            "arbol", fontName="Courier", fontSize=8, leading=12,
            textColor=NEGRO, spaceBefore=1, spaceAfter=1,
            backColor=HexColor("#F8FAFB"), leftIndent=4
        )))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # 2. DATOS
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_header("2. Datos de Entrada y Procesados"))
    story.append(sp())

    story.append(Paragraph(b("2.1 Dataset crudo: denue_inegi_61_.csv"), H2))
    story.append(Paragraph(
        "Archivo CSV del Directorio Estadístico Nacional de Unidades Económicas (DENUE) del INEGI, "
        "acotado al subsector 61 (Servicios Educativos) de la Ciudad de México. "
        "Contiene 10,448 registros con información de establecimientos educativos de todos los niveles.",
        BODY
    ))
    story.append(sp(0.5))
    story.append(Paragraph(b("Columnas principales del CSV crudo:"), BODY))
    story.append(sp(0.3))
    story.append(simple_table(
        ["Campo", "Tipo", "Descripción"],
        [
            ["nom_estab", "texto", "Nombre del establecimiento"],
            ["codigo_act", "texto", "Clave SCIAN de 6 dígitos (categoría de actividad)"],
            ["nombre_act", "texto", "Descripción completa de la actividad económica"],
            ["per_ocu", "entero", "Personal ocupado en el establecimiento"],
            ["cve_ent", "texto", "Clave de entidad federativa (09 = CDMX)"],
            ["entidad", "texto", "Nombre de la entidad (Ciudad de México)"],
            ["municipio", "texto", "Alcaldía o municipio"],
            ["latitud", "decimal", "Latitud WGS84 (grados decimales)"],
            ["longitud", "decimal", "Longitud WGS84 (grados decimales)"],
            ["fecha_alta", "texto", "Fecha de registro en DENUE"],
        ],
        col_widths=[3.5*cm, 2.5*cm, 9*cm]
    ))

    story.append(sp())
    story.append(Paragraph(b("2.2 Categorías SCIAN incluidas"), H2))
    story.append(Paragraph(
        "De los 10,448 registros originales se filtran únicamente las 12 categorías "
        "correspondientes a educación básica y media. Cada categoría combina nivel educativo y sector.",
        BODY
    ))
    story.append(sp(0.3))
    story.append(simple_table(
        ["Código SCIAN", "Descripción", "Nivel asignado", "Sector"],
        [
            ["611111", "Escuelas de educación preescolar del sector público", "preescolar", "público"],
            ["611112", "Escuelas de educación preescolar del sector privado", "preescolar", "privado"],
            ["611121", "Escuelas de educación primaria del sector público", "primaria", "público"],
            ["611122", "Escuelas de educación primaria del sector privado", "primaria", "privado"],
            ["611131", "Escuelas de educación secundaria general del sector público", "secundaria", "público"],
            ["611132", "Escuelas de educación secundaria general del sector privado", "secundaria", "privado"],
            ["611141", "Escuelas de bachillerato general del sector público", "media_superior", "público"],
            ["611142", "Escuelas de bachillerato general del sector privado", "media_superior", "privado"],
            ["611151", "Escuelas del nivel medio superior técnico terminal del sector público", "media_tecnica", "público"],
            ["611152", "Escuelas del nivel medio superior técnico terminal del sector privado", "media_tecnica", "privado"],
            ["611161", "Escuelas de formación para el trabajo del sector público", "media_tecnica", "público"],
            ["611162", "Escuelas de formación para el trabajo del sector privado", "media_tecnica", "privado"],
        ],
        col_widths=[2.8*cm, 8*cm, 2.7*cm, 2.5*cm]
    ))

    story.append(sp())
    story.append(Paragraph(b("2.3 Dataset procesado: escuelas_cdmx.parquet"), H2))
    story.append(Paragraph(
        "Resultado del pipeline de preparación de datos. Formato Apache Parquet (binario comprimido). "
        "Contiene 5,587 escuelas con columnas derivadas de nivel educativo, sector y coordenadas métricas.",
        BODY
    ))
    story.append(sp(0.3))
    story.append(simple_table(
        ["Columna", "Tipo", "Rango / Valores", "Descripción"],
        [
            ["nivel", "texto", "preescolar, primaria, secundaria, media_superior, media_tecnica", "Nivel educativo (derivado)"],
            ["sector", "texto", "público, privado", "Sector educativo (derivado)"],
            ["latitud", "decimal", "[19.0, 19.7]", "Latitud en grados WGS84"],
            ["longitud", "decimal", "[-99.4, -98.9]", "Longitud en grados WGS84"],
            ["x_utm", "decimal", "~470,000 – 510,000 m", "Coordenada Este UTM zona 14N (EPSG:32614)"],
            ["y_utm", "decimal", "~2,120,000 – 2,170,000 m", "Coordenada Norte UTM zona 14N (EPSG:32614)"],
            ["municipio", "texto", "16 alcaldías", "Alcaldía de CDMX"],
        ],
        col_widths=[2.5*cm, 2*cm, 5*cm, 6.5*cm]
    ))

    story.append(sp(0.5))
    story.append(Paragraph(b("Distribución por nivel educativo:"), BODY))
    story.append(sp(0.3))
    story.append(simple_table(
        ["Nivel", "Escuelas", "% del total"],
        [
            ["Preescolar", "1,467", "26.3%"],
            ["Primaria", "2,154", "38.6%"],
            ["Secundaria", "1,135", "20.3%"],
            ["Media Superior", "641", "11.5%"],
            ["Media Técnica", "190", "3.4%"],
            ["TOTAL", "5,587", "100%"],
        ],
        col_widths=[5*cm, 4*cm, 7*cm]
    ))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # 3. NOTEBOOKS
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_header("3. Notebooks de Análisis"))
    story.append(sp())

    story.append(Paragraph(
        "El análisis se desarrolla secuencialmente en cuatro notebooks Jupyter. "
        "Cada uno produce artefactos que consume el siguiente, formando un pipeline completo.",
        BODY
    ))
    story.append(sp())

    # 3.1
    story.append(Paragraph("3.1  01_data_prep.ipynb — Preparación de Datos", H2))
    story.append(Paragraph(b("Objetivo:") + " Transformar el CSV crudo del DENUE en un dataset limpio y georreferenciado en metros.", BODY))
    story.append(sp(0.5))

    pasos_prep = [
        ("1", "Carga del CSV", "Lee denue_inegi_61_.csv con encoding latin-1. Detecta los 10,448 registros originales."),
        ("2", "Filtro geográfico",
         "Filtra por entidad = 'Ciudad de México'. Aplica bounding box: latitud ∈ [19.0, 19.7], longitud ∈ [-99.4, -98.9]. "
         "Descarta puntos fuera de CDMX."),
        ("3", "Filtro por categoría",
         "Conserva solo los 12 códigos SCIAN de educación básica y media (ver tabla sección 2.2). "
         "Resultado: 5,587 escuelas válidas."),
        ("4", "Derivación de nivel y sector",
         "Parsea el campo nombre_act para asignar nivel (preescolar/primaria/secundaria/media_superior/media_tecnica) "
         "y sector (público/privado) a cada registro."),
        ("5", "Reproyección UTM",
         "Convierte coordenadas WGS84 (grados) a UTM zona 14N (metros) usando pyproj.Transformer con EPSG:4326→EPSG:32614. "
         "Las nuevas columnas x_utm y y_utm expresan la posición en metros, necesario para que las distancias "
         "del análisis topológico sean métricamente correctas."),
        ("6", "Exportación",
         "Guarda el resultado en data/processed/escuelas_cdmx.parquet usando pyarrow. "
         "Formato Parquet elegido por velocidad de lectura y compresión eficiente."),
    ]
    story.append(simple_table(
        ["Paso", "Etapa", "Descripción"],
        pasos_prep,
        col_widths=[1*cm, 3.5*cm, 11.5*cm]
    ))
    story.append(sp())

    # 3.2
    story.append(Paragraph("3.2  02_eda.ipynb — Análisis Exploratorio", H2))
    story.append(Paragraph(b("Objetivo:") + " Entender la distribución espacial de las escuelas y elegir el parámetro umbral ε para el análisis topológico.", BODY))
    story.append(sp(0.5))

    story.append(Paragraph(b("Análisis realizados:"), BODY))
    story.append(sp(0.3))
    for txt in [
        "<b>Tablas de frecuencia:</b> Conteos cruzados nivel × sector y distribución por alcaldía. "
        "Revela que Iztapalapa (~600), Gustavo A. Madero (~550) y Cuauhtémoc (~450) concentran mayor cobertura.",
        "<b>Mapa exploratorio:</b> Folium MarkerCluster con muestra aleatoria de 2,000 escuelas. "
        "Cada punto tiene color según nivel educativo.",
        "<b>Distancias al k-ésimo vecino más cercano (kNN):</b> Calcula distancias al vecino 1, 5 y 10 "
        "para cada nivel usando sklearn.neighbors.NearestNeighbors. "
        "Genera histogramas interactivos con Plotly.",
        "<b>Selección de umbral ε:</b> Basada en los percentiles de distancias kNN. "
        "El percentil 90 del vecino k=10 está ~2,200 m, lo que sugiere ε = 2,500–3,000 m como escala "
        "de análisis razonable (radio de desplazamiento urbano a pie).",
    ]:
        story.append(Paragraph("• " + txt, BULLET))

    story.append(sp(0.5))
    story.append(simple_table(
        ["k-vecino", "Mediana", "Percentil 75", "Percentil 90"],
        [
            ["k=1", "~200 m", "~400 m", "~700 m"],
            ["k=5", "~400 m", "~800 m", "~1,500 m"],
            ["k=10", "~600 m", "~1,200 m", "~2,200 m"],
        ],
        col_widths=[3*cm, 4*cm, 4*cm, 5*cm]
    ))
    story.append(Paragraph("Distancias kNN aproximadas (promedio entre todos los niveles)", CAPTION))
    story.append(sp(0.5))
    story.append(info_box(
        "Conclusión del EDA: Se elige ε = 3,000 m como umbral máximo para el análisis Vietoris-Rips. "
        "Este valor conecta la mayoría de las escuelas en un mismo nivel y corresponde a ~35 minutos caminando, "
        "un radio de acceso razonable en contexto urbano de CDMX."
    ))
    story.append(sp())

    # 3.3
    story.append(Paragraph("3.3  03_tda_persistencia.ipynb — Homología Persistente", H2))
    story.append(Paragraph(
        b("Objetivo:") + " Calcular los diagramas de persistencia H₀ y H₁ para cada nivel educativo "
        "y guardar los resultados para uso en el dashboard.",
        BODY
    ))
    story.append(sp(0.5))

    story.append(Paragraph(b("Parámetros del cálculo:"), H3))
    story.append(simple_table(
        ["Parámetro", "Valor", "Significado"],
        [
            ["maxdim", "1", "Calcula hasta homología de dimensión 1 (H₀ y H₁). H₀ = componentes conexas, H₁ = 1-ciclos (huecos)."],
            ["thresh", "3,000 m", "Radio máximo ε. Ninguna arista del complejo supera esta distancia."],
            ["do_cocycles", "True", "Devuelve 1-cocadenas (cociclos) que permiten localizar geográficamente cada hueco H₁."],
            ["Submuestreo", "Ninguno", "En los notebooks se usa la totalidad de puntos por nivel (no se reduce)."],
        ],
        col_widths=[2.5*cm, 2.2*cm, 11.3*cm]
    ))

    story.append(sp(0.5))
    story.append(Paragraph(b("Proceso por cada nivel:"), BODY))
    for paso in [
        "Extrae coordenadas UTM (x_utm, y_utm) del parquet para el nivel.",
        "Llama a ripser(X, maxdim=1, thresh=3000, do_cocycles=True).",
        "Obtiene dgms = [H0_array, H1_array] donde cada fila es (birth, death).",
        "Guarda resultado como pickle en data/processed/tda_results/{nivel}.pkl.",
    ]:
        story.append(Paragraph(f"• {paso}", BULLET))

    story.append(sp(0.5))
    story.append(Paragraph(b("Visualizaciones generadas:"), BODY))
    story.append(sp(0.3))
    viz_data = [
        ["Scatter espacial (2×3 grid)", "Posición UTM de las escuelas por nivel. Muestra densidad geográfica."],
        ["Diagramas de persistencia (2×3 grid)", "H₀ en azul, H₁ en naranja. Puntos lejos de la diagonal = features persistentes."],
        ["Barcode H₁ (2×3 grid)", "Top-15 features por persistencia. Barra más larga = hueco más robusto."],
        ["Lifetime plot (2×3 grid)", "Ejes: birth vs. persistencia. Línea gris = 25% de máximo (umbral de ruido)."],
        ["Curvas de Betti", "β₀(ε) y β₁(ε) en función del radio. Muestra evolución de la topología."],
        ["Barras de máxima persistencia", "Comparación entre niveles: media técnica suele tener mayor persistencia (red más escasa)."],
    ]
    story.append(simple_table(["Visualización", "Descripción"], viz_data, col_widths=[5*cm, 11*cm]))

    story.append(sp(0.5))
    story.append(Paragraph(b("Resultados típicos del cálculo:"), BODY))
    story.append(sp(0.3))
    story.append(simple_table(
        ["Nivel", "N escuelas", "H₁ features aprox.", "Max. persistencia H₁"],
        [
            ["Preescolar", "1,467", "~50", "~1,200 m"],
            ["Primaria", "2,154", "~80", "~1,500 m"],
            ["Secundaria", "1,135", "~40", "~1,300 m"],
            ["Media Superior", "641", "~25", "~1,800 m"],
            ["Media Técnica", "190", "~8", "~2,500 m"],
            ["Todas", "5,587", "~300+", "~2,000 m"],
        ],
        col_widths=[3.5*cm, 2.5*cm, 4*cm, 6*cm]
    ))
    story.append(sp(0.3))
    story.append(Paragraph(
        i("Nota: A mayor escasez de red → mayor persistencia de los huecos → zonas de cobertura más grandes y robustas."),
        META
    ))

    story.append(sp())

    # 3.4
    story.append(Paragraph("3.4  04_interpretacion.ipynb — Localización Geográfica de Huecos", H2))
    story.append(Paragraph(
        b("Objetivo:") + " Proyectar los huecos topológicos detectados por H₁ sobre un mapa real de CDMX "
        "para identificar zonas con déficit de cobertura educativa.",
        BODY
    ))
    story.append(sp(0.5))

    story.append(Paragraph(b("Función principal — hole_centroids(r, top_k=5):"), H3))
    for paso in [
        "Extrae el diagrama H₁ del resultado de ripser.",
        "Ordena features por persistencia (death − birth) descendente.",
        "Para cada uno de los top-k features:",
        "    a) Obtiene el cociclo: lista de tuplas (i, j, valor) que forman el 1-ciclo.",
        "    b) Extrae vértices únicos: np.unique(coc[:, :2].ravel()).",
        "    c) Calcula centroide geométrico: X[verts].mean(axis=0) en coordenadas UTM.",
        "    d) Convierte centroide a lat/lon con utm_to_latlon() para Folium.",
        "Retorna lista de dicts con birth, death, persistencia, centroide UTM, n_vértices.",
    ]:
        story.append(Paragraph(f"{'  ' if paso.startswith('    ') else '• '}{paso.strip()}", BULLET))

    story.append(sp(0.5))
    story.append(Paragraph(b("Mapa de huecos (Folium):"), BODY))
    for txt in [
        "Un FeatureGroup por nivel educativo con LayerControl para mostrar/ocultar capas.",
        "Por cada hueco: círculo grande con radio = persistencia/2 metros (visualiza el tamaño del hueco).",
        "CircleMarker en el centroide del hueco con popup interactivo.",
        "Popup muestra: birth, death, persistencia (metros), número de vértices del cociclo.",
    ]:
        story.append(Paragraph(f"• {txt}", BULLET))

    story.append(sp(0.5))
    story.append(Paragraph(b("Comparación con DBSCAN:"), H3))
    story.append(info_box(
        "El notebook incluye una sección comparativa: se ejecuta DBSCAN (ε=500 m, min_samples=5) sobre "
        "las escuelas de nivel primaria. DBSCAN identifica agrupaciones densas de escuelas, pero NO detecta "
        "zonas de déficit rodeadas por escuelas. TDA (H₁) es complementario: identifica exactamente esas "
        "regiones con carencia aunque existan escuelas en los alrededores."
    ))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # 4. MÓDULOS PYTHON
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_header("4. Módulos Python del Dashboard"))
    story.append(sp())

    story.append(Paragraph(
        "El dashboard (dashboard/) está construido con Streamlit y se divide en módulos de utilidad "
        "compartidos (utils/) y páginas independientes (pages/).",
        BODY
    ))
    story.append(sp())

    # 4.1 data_loader
    story.append(Paragraph("4.1  dashboard/utils/data_loader.py — Carga de Datos y Caché", H2))
    story.append(Paragraph(
        "Centraliza la carga de datos y define las constantes de configuración usadas en todo el dashboard. "
        "Usa el sistema de caché de Streamlit para no releer archivos en cada interacción.",
        BODY
    ))
    story.append(sp(0.5))

    story.append(Paragraph(b("Constantes definidas:"), H3))
    story.append(simple_table(
        ["Constante", "Valor", "Uso"],
        [
            ["NIVELES", "['preescolar', 'primaria', 'secundaria', 'media_superior', 'media_tecnica']",
             "Lista canónica de niveles para iteración y filtros"],
            ["SECTORES", "['público', 'privado']", "Opciones de sector disponibles"],
            ["NIVEL_COLOR['preescolar']", "#2ca02c (verde)", "Color de marcador para preescolar"],
            ["NIVEL_COLOR['primaria']", "#1f77b4 (azul)", "Color de marcador para primaria"],
            ["NIVEL_COLOR['secundaria']", "#ff7f0e (naranja)", "Color de marcador para secundaria"],
            ["NIVEL_COLOR['media_superior']", "#d62728 (rojo)", "Color de marcador para media superior"],
            ["NIVEL_COLOR['media_tecnica']", "#9467bd (púrpura)", "Color de marcador para media técnica"],
        ],
        col_widths=[3.5*cm, 4.5*cm, 8*cm]
    ))

    story.append(sp(0.5))
    story.append(Paragraph(b("Funciones:"), H3))
    story.append(simple_table(
        ["Función", "Parámetros", "Retorna", "Descripción"],
        [
            ["load_escuelas()", "—", "DataFrame",
             "Lee escuelas_cdmx.parquet con @st.cache_data. Retorna las 5,587 escuelas."],
            ["load_tda(nivel)", "nivel: str", "dict o None",
             "Lee el pickle de resultados TDA para el nivel dado. Retorna None si no existe."],
            ["available_tda_levels()", "—", "list[str]",
             "Devuelve lista de niveles que tienen archivos .pkl pre-computados."],
        ],
        col_widths=[3.5*cm, 2.5*cm, 2.5*cm, 7.5*cm]
    ))

    story.append(sp())

    # 4.2 tda.py
    story.append(Paragraph("4.2  dashboard/utils/tda.py — Motor de Cálculo TDA", H2))
    story.append(Paragraph(
        "Contiene toda la lógica matemática del análisis topológico. "
        "Implementa submuestreo inteligente, cálculo de homología persistente con ripser, "
        "curvas de Betti y extracción de centroides de huecos mediante cociclos.",
        BODY
    ))
    story.append(sp(0.5))

    story.append(Paragraph(b("Función 1: landmark_sample(X, max_n=1500, seed=0)"), H3))
    story.append(Paragraph(
        "Reduce el número de puntos cuando N > max_n para hacer manejable el cálculo de Vietoris-Rips. "
        "El complejo Vietoris-Rips tiene complejidad cuadrática O(N²) en número de aristas y cúbica O(N³) "
        "en el caso general, lo que hace inviable procesar miles de puntos en tiempo real.",
        BODY
    ))
    story.append(sp(0.3))
    story.append(simple_table(
        ["Condición", "Acción", "Resultado"],
        [
            ["len(X) ≤ max_n", "Retorna X sin cambios", "Dataset completo, sin pérdida"],
            ["len(X) > max_n", "Aplica KMeans(n_clusters=max_n)", "max_n centroides representativos"],
        ],
        col_widths=[4*cm, 6*cm, 6*cm]
    ))

    story.append(sp(0.5))
    story.append(Paragraph(b("Función 2: compute_vr(X, thresh, max_n) — con @st.cache_resource"), H3))
    story.append(Paragraph(
        "Función principal de cálculo. Ejecuta el pipeline completo de homología persistente:",
        BODY
    ))
    story.append(sp(0.3))
    for paso in [
        "Submuestrea con landmark_sample(X, max_n).",
        "Llama a ripser(Xs, maxdim=1, thresh=thresh, do_cocycles=True).",
        "El parámetro maxdim=1 limita el cálculo a H₀ y H₁ (componentes y ciclos 1-dimensionales).",
        "El parámetro do_cocycles=True activa el cómputo de cocadenas para localización posterior.",
        "Retorna dict con los puntos submuestreados, diagramas dgms=[H0, H1], cociclos y parámetros.",
    ]:
        story.append(Paragraph(f"• {paso}", BULLET))

    story.append(sp(0.5))
    story.append(Paragraph(b("Función 3: betti_curves(dgms, eps_grid)"), H3))
    story.append(Paragraph(
        "Calcula las curvas de Betti β₀(ε) y β₁(ε) a lo largo de una grilla de valores de escala.",
        BODY
    ))
    story.append(sp(0.3))
    story.append(Paragraph(
        "Para cada valor ε en eps_grid, cuenta los features del diagrama que están 'vivos' en esa escala: "
        "un feature (birth, death) está vivo si birth ≤ ε < death. "
        "β₀ cuenta componentes conexas; β₁ cuenta 1-ciclos (huecos). "
        "Retorna array de forma (len(eps_grid), 2).",
        BODY
    ))

    story.append(sp(0.5))
    story.append(Paragraph(b("Función 4: top_h1_with_cocycles(r, k=5)"), H3))
    story.append(Paragraph(
        "Extrae los k huecos H₁ más persistentes y calcula su ubicación geográfica mediante los cociclos:",
        BODY
    ))
    story.append(sp(0.3))
    for paso in [
        "Ordena features H₁ por persistencia descendente (death − birth, tomando thresh si death=∞).",
        "Para cada uno de los top-k: extrae los índices de vértices del cociclo correspondiente.",
        "Calcula el centroide geométrico como promedio de coordenadas UTM de los vértices.",
        "Retorna lista de dicts con birth, death, persistencia, centroide UTM, coordenadas de vértices, n_vértices.",
    ]:
        story.append(Paragraph(f"• {paso}", BULLET))

    story.append(sp())

    # 4.3 plotting.py
    story.append(Paragraph("4.3  dashboard/utils/plotting.py — Visualizaciones", H2))
    story.append(Paragraph(
        "Proporciona todas las funciones de visualización usadas por las páginas del dashboard. "
        "Combina Plotly (gráficos estadísticos) y Folium (mapas geográficos).",
        BODY
    ))
    story.append(sp(0.5))

    story.append(Paragraph(b("Transformación de coordenadas:"), H3))
    story.append(Paragraph(
        "utm_to_latlon(x, y): Convierte coordenadas UTM zona 14N (EPSG:32614) a "
        "latitud/longitud WGS84 (EPSG:4326). Usa pyproj.Transformer con always_xy=True. "
        "Necesario porque Folium trabaja en grados, pero el análisis TDA en metros.",
        BODY
    ))
    story.append(sp(0.5))

    story.append(Paragraph(b("Gráficos Plotly:"), H3))
    story.append(simple_table(
        ["Función", "Descripción", "Ejes"],
        [
            ["persistence_diagram(dgms, thresh)",
             "Diagrama de persistencia clásico. Puntos H₀ en azul, H₁ en naranja. "
             "Línea diagonal gris = referencia (birth=death). Distancia a la diagonal = persistencia.",
             "X: birth (m), Y: death (m)"],
            ["barcode(dgms, thresh, dim=1)",
             "Barcode: una barra horizontal por feature H₁. Longitud = persistencia. "
             "Ordenadas de mayor a menor persistencia. Features con death=∞ se extienden hasta thresh.",
             "X: ε (m), Y: índice de feature"],
            ["betti_curve_fig(eps, betti)",
             "Dos líneas superpuestas: β₀(ε) en azul (eje Y izquierdo) y β₁(ε) en naranja "
             "(eje Y derecho). Muestra cómo evoluciona la topología al aumentar ε.",
             "X: ε (m), Y: número de Betti"],
        ],
        col_widths=[4.5*cm, 7.5*cm, 4*cm]
    ))

    story.append(sp(0.5))
    story.append(Paragraph(b("Mapas Folium:"), H3))
    story.append(simple_table(
        ["Función", "Descripción"],
        [
            ["base_map(zoom=11)", "Crea mapa Folium centrado en CDMX [19.4326, -99.1332] con tiles CartoDB Positron."],
            ["add_school_layer(m, df, sample_max=1500)",
             "Agrega capa MarkerCluster con CircleMarkers por escuela. Color según NIVEL_COLOR. "
             "Tooltip con nivel, sector y nombre del establecimiento."],
            ["add_holes_layer(m, holes, color, label)",
             "Agrega capa de huecos: círculo grande (radio = persistencia/2 en metros) "
             "y CircleMarker en centroide con popup de metadatos TDA."],
        ],
        col_widths=[5*cm, 11*cm]
    ))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # 5. PÁGINAS DEL DASHBOARD
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_header("5. Páginas del Dashboard Streamlit"))
    story.append(sp())

    story.append(Paragraph(
        "El dashboard se ejecuta con streamlit run dashboard/app.py y presenta cinco secciones navegables. "
        "Cada página combina controles interactivos en la barra lateral con visualizaciones en el área principal.",
        BODY
    ))
    story.append(sp())

    # Portada
    story.append(Paragraph("5.0  app.py — Portada Principal", H2))
    story.append(Paragraph(b("Propósito:") + " Vista de bienvenida con métricas globales del dataset.", BODY))
    story.append(sp(0.3))
    for txt in [
        "Cuatro métricas destacadas: total de escuelas (5,587), niveles (5), alcaldías (16), sectores (2).",
        "Tabla de conteos cruzados nivel × sector con totales por fila y columna.",
        "Tabla de categorías SCIAN incluidas con código, descripción, nivel asignado y sector.",
        "Leyenda de colores por nivel educativo (usada consistentemente en todo el dashboard).",
    ]:
        story.append(Paragraph(f"• {txt}", BULLET))
    story.append(sp())

    # Panorama
    story.append(Paragraph("5.1  1_Panorama.py — Exploración Geográfica", H2))
    story.append(Paragraph(b("Propósito:") + " Mapa interactivo filtrable para explorar la distribución espacial de las escuelas.", BODY))
    story.append(sp(0.3))

    story.append(Paragraph(b("Filtros (barra lateral):"), BODY))
    story.append(simple_table(
        ["Control", "Tipo", "Opciones"],
        [
            ["Nivel educativo", "Multiselect", "preescolar, primaria, secundaria, media_superior, media_tecnica"],
            ["Sector", "Multiselect", "público, privado"],
            ["Alcaldía", "Multiselect", "Las 16 alcaldías de CDMX"],
            ["Máx. puntos a dibujar", "Slider", "200 – 5,000 (default 1,500)"],
        ],
        col_widths=[4*cm, 2.5*cm, 9.5*cm]
    ))
    story.append(sp(0.3))
    story.append(Paragraph(b("Visualizaciones (columna principal 3/4 + columna derecha 1/4):"), BODY))
    for txt in [
        "Mapa Folium con MarkerCluster: los marcadores se agrupan automáticamente al hacer zoom out. "
        "Al hacer zoom in, se expanden mostrando cada escuela con su tooltip.",
        "Gráfico de barras horizontal: conteo de escuelas por nivel educativo con colores NIVEL_COLOR.",
        "Gráfico de barras horizontal: top-10 alcaldías por número de escuelas, ordenado descendente.",
    ]:
        story.append(Paragraph(f"• {txt}", BULLET))
    story.append(sp())

    # Complejos
    story.append(Paragraph("5.2  2_Complejos_Simpliciales.py — Visualización Vietoris-Rips", H2))
    story.append(Paragraph(
        b("Propósito:") + " Visualizar interactivamente la construcción del complejo Vietoris-Rips "
        "al variar el parámetro ε, mostrando vértices, aristas y triángulos sobre el mapa de CDMX.",
        BODY
    ))
    story.append(sp(0.3))

    story.append(Paragraph(b("¿Qué es un complejo Vietoris-Rips?"), H3))
    story.append(info_box(
        "Dado un conjunto de puntos (escuelas) y un radio ε:\n"
        "• Vértice (0-símplex): cada escuela es un punto.\n"
        "• Arista (1-símplex): se traza una línea entre dos escuelas si su distancia ≤ ε.\n"
        "• Triángulo (2-símplex): se rellena el triángulo formado por tres escuelas si todas "
        "  las distancias entre pares ≤ ε.\n"
        "El complejo captura la 'forma' de la nube de puntos a la escala ε."
    ))
    story.append(sp(0.3))

    story.append(Paragraph(b("Controles:"), BODY))
    story.append(simple_table(
        ["Control", "Rango", "Efecto"],
        [
            ["Nivel educativo", "Todas + 5 niveles", "Filtra qué escuelas se incluyen como vértices"],
            ["Sector", "Ambos, público, privado", "Filtra por tipo de gestión"],
            ["Puntos máx.", "50 – 600 (default 250)", "Submuestreo de vértices para rendimiento"],
            ["ε radio (metros)", "0 – 4,000 (default 800)", "Distancia máxima para conectar dos escuelas"],
            ["Mostrar discos de Čech", "Checkbox", "Dibuja círculos de radio ε/2 alrededor de cada vértice"],
        ],
        col_widths=[3.5*cm, 4*cm, 8.5*cm]
    ))
    story.append(sp(0.3))

    story.append(Paragraph(b("Construcción del complejo (algoritmo):"), BODY))
    for paso in [
        "Filtra escuelas por nivel y sector.",
        "Submuestrea con landmark_sample(X, max_pts).",
        "Construye aristas: scipy.spatial.cKDTree.query_pairs(r=ε) — devuelve todos los pares (i,j) con distancia ≤ ε.",
        "Construye triángulos (solo si n ≤ 200 vértices): para cada par de aristas (i,j) y (i,k) "
        "verifica si existe arista (j,k). Si existe, forma triángulo (i,j,k).",
        "Convierte coordenadas UTM → lat/lon para visualización en Folium.",
        "Dibuja capas: triángulos semitransparentes → aristas → discos Čech → vértices con LayerControl.",
    ]:
        story.append(Paragraph(f"• {paso}", BULLET))
    story.append(sp())

    # Persistencia
    story.append(Paragraph("5.3  3_Persistencia.py — Análisis de Persistencia", H2))
    story.append(Paragraph(
        b("Propósito:") + " Explorar los diagramas de persistencia, barcodes y curvas de Betti "
        "para cada nivel educativo, tanto en modo pre-computado (instantáneo) como recalculando con filtros personalizados.",
        BODY
    ))
    story.append(sp(0.3))

    story.append(Paragraph(b("Dos modos de operación:"), H3))
    story.append(simple_table(
        ["Modo", "Descripción", "Velocidad"],
        [
            ["Pre-computado por nivel",
             "Carga el pickle pre-calculado del nivel seleccionado (preescolar, primaria, secundaria, "
             "media_superior, media_tecnica, todas). Resultados instantáneos.",
             "Inmediata"],
            ["Recalcular con filtros",
             "Permite combinar niveles y sectores, ajustar umbral ε (500–5,000 m) y número de landmarks "
             "(200–2,000). Recalcula con ripser en tiempo real. Requiere mínimo 3 puntos.",
             "Segundos (según n)"],
        ],
        col_widths=[3.5*cm, 9*cm, 3.5*cm]
    ))
    story.append(sp(0.3))

    story.append(Paragraph(b("Métricas mostradas:"), BODY))
    for txt in [
        "H₀ features: número de componentes conexas detectadas.",
        "H₁ features: número de 1-ciclos (huecos topológicos) detectados.",
        "Hueco más persistente: max(death − birth) sobre todos los features H₁.",
        "Persistencia media H₁: promedio de persistencias de todos los huecos.",
    ]:
        story.append(Paragraph(f"• {txt}", BULLET))
    story.append(sp(0.3))

    story.append(Paragraph(b("Tres pestañas de visualización:"), BODY))
    story.append(simple_table(
        ["Pestaña", "Contenido", "Interpretación"],
        [
            ["Diagrama de persistencia",
             "Scatter plot con birth en X y death en Y. Línea diagonal gris = referencia.",
             "Puntos lejanos a la diagonal → features robustos (no son ruido)."],
            ["Barcode H₁",
             "Barras horizontales ordenadas por persistencia. Altura del panel escala con número de features.",
             "Barras largas = huecos topológicamente significativos."],
            ["Curvas de Betti",
             "β₀(ε) azul (eje Y izquierdo) y β₁(ε) naranja (eje Y derecho) en función de ε.",
             "Permite ver en qué escala surgen y desaparecen los huecos."],
        ],
        col_widths=[3.5*cm, 7*cm, 5.5*cm]
    ))
    story.append(sp())

    # Huecos
    story.append(Paragraph("5.4  4_Huecos_de_Cobertura.py — Mapa de Déficit Educativo", H2))
    story.append(Paragraph(
        b("Propósito:") + " Página central del análisis: localiza geográficamente los huecos H₁ "
        "más persistentes sobre el mapa de CDMX y presenta una tabla con coordenadas y metadatos "
        "para priorizar zonas de intervención.",
        BODY
    ))
    story.append(sp(0.3))

    story.append(Paragraph(b("Controles:"), BODY))
    story.append(simple_table(
        ["Control", "Tipo", "Descripción"],
        [
            ["Niveles a analizar", "Multiselect", "Selección múltiple de niveles; puede incluir 'todas' (default: primaria, secundaria)"],
            ["Sector", "Radio button", "Ambos (usa pre-computado) / público / privado (recalcula sobre subconjunto)"],
            ["Top-K huecos", "Slider 1–10", "Número de huecos a mostrar por nivel (default: 5)"],
            ["Mostrar escuelas", "Checkbox", "Si activo, superpone capa con 800 escuelas muestreadas del nivel"],
        ],
        col_widths=[3.5*cm, 3*cm, 9.5*cm]
    ))
    story.append(sp(0.3))

    story.append(Paragraph(b("Mapa interactivo:"), BODY))
    for txt in [
        "Base CDMX con tiles CartoDB Positron.",
        "Por cada nivel seleccionado: FeatureGroup con LayerControl para mostrar/ocultar.",
        "Por cada hueco: círculo con radio = persistencia/2 metros (proporcional al tamaño del hueco).",
        "CircleMarker en el centroide del hueco con popup: birth (m), death (m), persistencia (m), n_vértices.",
        "Si 'Mostrar escuelas' activo: capa adicional con MarkerCluster de escuelas del nivel.",
    ]:
        story.append(Paragraph(f"• {txt}", BULLET))
    story.append(sp(0.3))

    story.append(Paragraph(b("Tabla de resultados:"), BODY))
    story.append(Paragraph(
        "Columna derecha con DataFrame ordenado por persistencia descendente. "
        "Columnas: nivel, sector, latitud, longitud, birth (m), death (m), persistencia (m), n_vértices. "
        "La fila superior identifica el hueco más significativo de toda la selección "
        "y se destaca con una caja de información.",
        BODY
    ))
    story.append(sp(0.3))
    story.append(info_box(
        "Interpretación del déficit: un hueco H₁ persistente identifica una región geográfica "
        "rodeada por escuelas del nivel analizado, pero que internamente carece de cobertura. "
        "A mayor persistencia → mayor tamaño del déficit → mayor prioridad de intervención. "
        "La ubicación del centroide indica dónde abrir un nuevo plantel tendría mayor impacto."
    ))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # 6. FUNDAMENTOS MATEMÁTICOS
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_header("6. Fundamentos Matemáticos"))
    story.append(sp())

    story.append(Paragraph(b("6.1 Homología Persistente"), H2))
    story.append(Paragraph(
        "El Análisis Topológico de Datos (TDA) aplica herramientas de topología algebraica a nubes de puntos. "
        "La homología persistente mide cómo cambian las características topológicas de un espacio al variar "
        "un parámetro de escala ε.",
        BODY
    ))
    story.append(sp(0.5))

    story.append(Paragraph(b("Complejo Vietoris-Rips VR(X, ε):"), H3))
    story.append(Paragraph(
        "Dado un conjunto X de puntos (escuelas) y un radio ε ≥ 0, el complejo Vietoris-Rips es el complejo "
        "simplicial formado por todos los subconjuntos σ ⊆ X tales que la distancia entre cualquier par de "
        "puntos en σ sea ≤ ε. Al aumentar ε de 0 a ∞, se obtiene una filtración: "
        "VR(X, 0) ⊆ VR(X, ε₁) ⊆ VR(X, ε₂) ⊆ ⋯",
        BODY
    ))
    story.append(sp(0.5))

    story.append(Paragraph(b("Grupos de homología:"), H3))
    story.append(simple_table(
        ["Grupo", "Dimensión", "Significado topológico", "En el contexto de escuelas"],
        [
            ["H₀", "0", "Componentes conexas", "Grupos de escuelas mutuamente alcanzables a distancia ≤ ε"],
            ["H₁", "1", "1-ciclos (agujeros)", "Regiones rodeadas por escuelas pero sin cobertura interna"],
            ["H₂", "2", "2-ciclos (cavidades)", "No calculado en este proyecto (maxdim=1)"],
        ],
        col_widths=[1.5*cm, 2.2*cm, 4.5*cm, 7.8*cm]
    ))
    story.append(sp(0.5))

    story.append(Paragraph(b("Diagrama de persistencia:"), H3))
    story.append(Paragraph(
        "Cada feature topológico nace a un radio εᵦ (birth) y muere a un radio ε_d (death). "
        "El par (birth, death) se representa como un punto en el plano. La diagonal birth = death "
        "actúa como referencia: puntos cercanos a la diagonal tienen baja persistencia (ruido topológico); "
        "puntos lejanos tienen alta persistencia (estructura real de los datos).",
        BODY
    ))
    story.append(sp(0.3))
    story.append(Paragraph(
        "Persistencia de un feature: pers = death − birth. "
        "Para features con death = ∞ (nunca mueren dentro del umbral), se usa thresh como valor de muerte.",
        BODY
    ))
    story.append(sp(0.5))

    story.append(Paragraph(b("6.2 Números de Betti"), H2))
    story.append(Paragraph(
        "El k-ésimo número de Betti βₖ(ε) cuenta el número de features Hₖ vivos a la escala ε. "
        "Un feature (birth, death) está vivo en ε si birth ≤ ε < death.",
        BODY
    ))
    story.append(sp(0.3))
    story.append(simple_table(
        ["Número", "Descripción", "Interpretación en ε pequeño", "Interpretación en ε grande"],
        [
            ["β₀(ε)", "Componentes conexas", "Alto: cada escuela es un componente", "Decrece hasta 1 cuando toda la ciudad se conecta"],
            ["β₁(ε)", "Huecos 1-dimensionales", "0: no hay ciclos con pocas conexiones", "Sube al aparecer ciclos, luego baja al llenarse"],
        ],
        col_widths=[1.8*cm, 4*cm, 5.5*cm, 4.7*cm]
    ))
    story.append(sp(0.5))

    story.append(Paragraph(b("6.3 Cociclos y Localización"), H2))
    story.append(Paragraph(
        "La librería Ripser con do_cocycles=True devuelve, para cada feature H₁, una 1-cocadena: "
        "un conjunto de aristas (i, j) del complejo que 'detectan' el ciclo. "
        "Los vértices de estas aristas delimitan geométricamente la zona del hueco. "
        "El centroide de estos vértices da la ubicación geográfica del déficit de cobertura.",
        BODY
    ))
    story.append(sp(0.5))

    story.append(Paragraph(b("6.4 Relación con radio de cobertura urbana"), H2))
    story.append(Paragraph(
        "La elección de ε = 3,000 m como umbral de análisis se fundamenta en la escala humana: "
        "3 km equivalen aproximadamente a 35-40 minutos caminando, rango típico de desplazamiento "
        "en zonas urbanas de CDMX. Los huecos H₁ detectados a esta escala representan áreas donde "
        "ninguna escuela del nivel analizado está accesible en ese tiempo desde el interior del hueco.",
        BODY
    ))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # 7. DEPENDENCIAS
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_header("7. Dependencias y Librerías"))
    story.append(sp())

    story.append(simple_table(
        ["Librería", "Versión mín.", "Función en el proyecto"],
        [
            ["pandas", "≥ 2.0", "Procesamiento del CSV y parquet; filtros y agrupaciones en el dashboard"],
            ["numpy", "≥ 1.24", "Operaciones matriciales, cálculo de centroides, arreglos de coordenadas"],
            ["pyproj", "≥ 3.6", "Transformación de coordenadas WGS84 ↔ UTM 14N (EPSG:4326 ↔ EPSG:32614)"],
            ["shapely", "≥ 2.0", "Geometría vectorial (incluida por compatibilidad con folium/geopandas)"],
            ["scikit-learn", "≥ 1.3", "KMeans para submuestreo (landmark_sample); NearestNeighbors para kNN en EDA"],
            ["ripser", "≥ 0.6", "Cálculo del complejo Vietoris-Rips y homología persistente (motor central del TDA)"],
            ["persim", "≥ 0.3", "Métricas de distancia entre diagramas de persistencia (wasserstein, bottleneck)"],
            ["folium", "≥ 0.15", "Mapas interactivos HTML con OSM/CartoDB; MarkerCluster, FeatureGroup, LayerControl"],
            ["streamlit", "≥ 1.30", "Framework del dashboard web interactivo; cache, widgets, layout de páginas"],
            ["streamlit-folium", "≥ 0.18", "Integración de mapas Folium dentro del entorno Streamlit"],
            ["plotly", "≥ 5.20", "Diagramas de persistencia, barcodes, curvas de Betti y gráficos de barras"],
            ["pyarrow", "≥ 14", "Lectura y escritura del formato Parquet para el dataset procesado"],
            ["scipy", "implícita", "cKDTree para búsqueda eficiente de pares de puntos en Complejos Simpliciales"],
        ],
        col_widths=[3.5*cm, 2*cm, 10.5*cm]
    ))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # 8. PIPELINE COMPLETO
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_header("8. Pipeline Completo del Proyecto"))
    story.append(sp())

    pasos_pipeline = [
        ("ENTRADA", "denue_inegi_61_.csv", "Dataset crudo DENUE subsector 61 CDMX — 10,448 registros"),
        ("01_data_prep", "Notebook", "Filtra CDMX + 12 categorías SCIAN → reproyecta UTM → exporta parquet"),
        ("escuelas_cdmx.parquet", "Artefacto", "5,587 escuelas con coordenadas UTM y etiquetas nivel/sector"),
        ("02_eda", "Notebook", "Análisis distribucional + kNN distances → justifica ε = 3,000 m"),
        ("03_tda_persistencia", "Notebook", "ripser() por nivel → diagramas H₀/H₁ + visualizaciones matplotlib"),
        ("tda_results/*.pkl", "Artefacto", "6 pickles con dgms, cociclos y metadatos por nivel"),
        ("04_interpretacion", "Notebook", "hole_centroids() → proyección en Folium + comparación DBSCAN"),
        ("dashboard/app.py", "Dashboard", "Portada: métricas globales y tablas de categorías"),
        ("1_Panorama", "Dashboard", "Mapa explorador con filtros de nivel, sector, alcaldía"),
        ("2_Complejos_Simpliciales", "Dashboard", "Animación Vietoris-Rips interactiva con control de ε"),
        ("3_Persistencia", "Dashboard", "Diagrama, barcode, Betti — pre-computado o calculado en tiempo real"),
        ("4_Huecos_de_Cobertura", "Dashboard", "Mapa de déficit + tabla de zonas prioritarias con coordenadas"),
    ]

    for etapa, tipo, desc in pasos_pipeline:
        color_tipo = {
            "ENTRADA": HexColor("#8B4513"),
            "Notebook": AZUL_MEDIO,
            "Artefacto": VERDE,
            "Dashboard": HexColor("#7B2D8B"),
        }.get(tipo, AZUL_OSCURO)

        row = Table(
            [[
                Table([[Paragraph(tipo, ParagraphStyle("tip", fontName="Helvetica-Bold",
                        fontSize=8, textColor=white, alignment=TA_CENTER))]],
                      colWidths=[2.2*cm],
                      style=TableStyle([("BACKGROUND", (0,0), (-1,-1), color_tipo),
                                        ("TOPPADDING",(0,0),(-1,-1),4),
                                        ("BOTTOMPADDING",(0,0),(-1,-1),4)])),
                Paragraph(f"<b>{etapa}</b>", BODY_L),
                Paragraph(desc, BODY_L),
            ]],
            colWidths=[2.4*cm, 4.5*cm, 9.1*cm],
            style=TableStyle([
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                ("TOPPADDING", (0,0), (-1,-1), 4),
                ("BOTTOMPADDING", (0,0), (-1,-1), 4),
                ("LEFTPADDING", (0,0), (-1,-1), 6),
                ("BOX", (0,0), (-1,-1), 0.5, GRIS_BORDE),
                ("BACKGROUND", (0,0), (-1,-1), GRIS_CLARO),
            ])
        )
        story.append(row)
        story.append(Spacer(1, 2))

    story.append(sp())
    story.append(info_box(
        "El pipeline está diseñado para ser reproducible: los notebooks (01→04) pueden ejecutarse "
        "secuencialmente para re-generar todos los artefactos desde el CSV crudo. "
        "El dashboard consume los artefactos pre-generados para respuesta inmediata, "
        "pero también permite recalcular en tiempo real mediante los controles de la página 3 y 4."
    ))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # 9. RESUMEN Y CONCLUSIONES
    # ══════════════════════════════════════════════════════════════════════════
    story.append(section_header("9. Resumen y Aplicación"))
    story.append(sp())

    story.append(Paragraph(b("¿Qué resuelve este proyecto?"), H2))
    story.append(Paragraph(
        "El proyecto aplica homología persistente — una herramienta de topología algebraica — para identificar "
        "zonas geográficas con déficit de cobertura educativa en la Ciudad de México. A diferencia de métodos "
        "clásicos de clustering que detectan dónde hay densidad de escuelas, el análisis topológico detecta "
        "dónde NO hay cobertura aunque existan escuelas en los alrededores.",
        BODY
    ))
    story.append(sp(0.5))

    story.append(Paragraph(b("Ventaja sobre métodos tradicionales:"), H2))
    story.append(simple_table(
        ["Método", "Detecta", "No detecta"],
        [
            ["DBSCAN / K-means", "Agrupaciones densas de escuelas (zonas de alta cobertura)", "Regiones interiores vacías rodeadas por escuelas"],
            ["Buffer de distancia simple", "Áreas dentro de radio R de alguna escuela", "Topología global: si hay 'huecos' en la red"],
            ["TDA — Homología H₁", "Huecos topológicos persistentes en la red de escuelas", "Requiere interpretación adicional para política pública"],
        ],
        col_widths=[4*cm, 6.5*cm, 5.5*cm]
    ))
    story.append(sp(0.5))

    story.append(Paragraph(b("Uso esperado de los resultados:"), H2))
    for txt in [
        "Planificación urbana: identificar zonas prioritarias para apertura de nuevos planteles.",
        "Reasignación de matrícula: redirigir demanda hacia escuelas existentes en perímetro del hueco.",
        "Análisis comparativo entre niveles: los niveles con mayor persistencia (media técnica) "
        "tienen déficits más severos y justifican mayor atención de política pública.",
        "Extensibilidad: la misma metodología aplica a redes de hospitales, bibliotecas, farmacias, "
        "o cualquier servicio geolocalizable.",
    ]:
        story.append(Paragraph(f"• {txt}", BULLET))
    story.append(sp(0.5))

    story.append(Paragraph(b("Limitaciones:"), H2))
    for txt in [
        "Datos DENUE registran establecimientos económicos, no necesariamente escuelas activas o con capacidad.",
        "El umbral ε = 3,000 m es razonable pero arbitrario; análisis de sensibilidad con otros valores es recomendable.",
        "El submuestreo por KMeans (landmarks) puede desplazar ligeramente los centroides de los huecos.",
        "La persistencia máxima no equivale directamente al número de estudiantes sin acceso.",
    ]:
        story.append(Paragraph(f"• {txt}", BULLET))

    story.append(sp(2))
    story.append(hr(AZUL_MEDIO, 1.5))
    story.append(sp(0.5))
    story.append(Paragraph(
        "Documentación generada automáticamente desde el código fuente del proyecto.",
        META
    ))
    story.append(Paragraph(
        "Proyecto: Análisis Topológico de Escuelas en CDMX  |  Rama: Topología Computacional / TDA  |  "
        "Stack: Python · Ripser · Streamlit · Folium · Plotly",
        META
    ))

    # ─── Build ────────────────────────────────────────────────────────────────
    doc.build(story)
    print(f"PDF generado: {OUTPUT}")


if __name__ == "__main__":
    build_pdf()
