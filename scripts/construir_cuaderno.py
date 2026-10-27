"""Genera el cuaderno Colab del análisis San Carlos (clima + cultivo)."""
import sys
import nbformat as nbf

celdas = []


def md(t):
    celdas.append(nbf.v4.new_markdown_cell(t.strip("\n")))


def code(t):
    celdas.append(nbf.v4.new_code_cell(t.strip("\n")))


md(r"""
# Clima y cultivo de caucho en el lote **San Carlos** (Meta, Orinoquía)
### Variables climáticas, validación con la estación IDEAM La Palomera y relación con la fenología y las enfermedades foliares (2016–2020)

**Lote:** San Carlos — 4°11'15.52" N, 72°32'14.55" O
**Cultivo:** *Hevea brasiliensis*, clones FX 3864, IAN 873 y RRIM 600 (8 repeticiones × 4 árboles por clon)
**Datos de cultivo:** `Fenologia_base Orinoquia.xlsx` (hojas FENOLOGIA, NECROMASA, IMAGENES)
**Ventana de interés:** enero–abril (defoliación invernal → refoliación → maduración de la hoja)

---

## ¿Qué hace este cuaderno?

| Parte | Pregunta que responde |
|---|---|
| 0. Configuración | Rutas, coordenadas, umbrales. **Lo único que hay que editar.** |
| 1. Descarga de datos | Obtiene ERA5-Land (T, HR horaria), ERA5 (lluvia, radiación, ETo), CHIRPS (lluvia diaria) y la estación automática IDEAM **La Palomera** (HR, T y lluvia). |
| 2. Estación La Palomera | Control de calidad y paso de datos horarios a diarios. |
| 3. Validación ene–abr | ¿Se pueden correlacionar los datos de La Palomera con CHIRPS y ERA5-Land de enero a abril? ¿A qué escala (diaria, 8 días, mensual)? |
| 4. Corrección de la HR | ERA5-Land subestima la humedad nocturna; se corrige con La Palomera (mapeo de cuantiles). |
| 5. Base climática diaria del lote | Serie 2011–2025 con indicadores de riesgo para SALB y Antracnosis/CLF, medias móviles y periodos de 8 días. |
| 6. ¿Cambia el clima cada 8 días? | Prueba si los periodos de 8 días (la frecuencia de muestreo del cultivo) son distintos entre sí. |
| 7. Datos del cultivo | Incidencia y severidad de enfermedades, estados de hoja, necromasa y LAI por clon y fecha. |
| 8. Relación clima–enfermedad | Correlaciones con ventanas de clima previas a cada evaluación y un modelo estadístico (GEE). |
| 9. Clima, caída de hojas y dosel | Necromasa y LAI frente al clima. |
| 10. Exportar | Un Excel con todas las tablas (hoja LEEME) y las figuras en PNG de 300 dpi. |

## Cómo usarlo en Google Colab
1. En su Google Drive debe estar la carpeta del proyecto (por ejemplo `MyDrive/tapiero/`) con el archivo `Fenologia_base Orinoquia.xlsx` en la raíz.
2. Abra este cuaderno en Colab (*Archivo → Abrir cuaderno → Google Drive*).
3. En la celda **0.2** cambie `RUTA_DRIVE` si su carpeta tiene otro nombre.
4. *Entorno de ejecución → Ejecutar todas*. La primera vez tarda ~5–15 min (descargas de ERA5-Land, CHIRPS y La Palomera). Después los datos quedan guardados en `san_carlos/datos_crudos/` y todo corre en ~2 min.

> Las celdas de **texto** explican el *por qué*; los **comentarios** (`#`) dentro del código explican el *cómo*, línea por línea.
""")

md(r"""
---
# 0. Configuración

## 0.1 Librerías
Todas las librerías usadas (pandas, numpy, requests, scipy, statsmodels, matplotlib, openpyxl) ya vienen instaladas en Google Colab, así que no hay que instalar nada.
""")

code(r"""
import sys, subprocess

EN_COLAB = "google.colab" in sys.modules   # True si estamos dentro de Google Colab

# --- Librerías estándar ---
import io, json, math, time, warnings
from pathlib import Path

# --- Librerías científicas ---
import numpy as np                     # cálculo numérico
import pandas as pd                    # tablas (DataFrames) y series de tiempo
import requests                        # descargas por internet (APIs)
from scipy import stats                # pruebas estadísticas (Spearman, Kruskal-Wallis...)
import statsmodels.api as sm           # modelos estadísticos (GEE)
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests   # corrección por comparaciones múltiples
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

warnings.filterwarnings("ignore")      # oculta avisos menores para que la salida sea legible
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 40)
print("Librerías cargadas. ¿Colab?", EN_COLAB)
""")

md(r"""
## 0.2 Rutas y parámetros  ✏️ *(edite aquí)*

- `RUTA_DRIVE`: carpeta del proyecto en su Drive. Dentro debe estar `Fenologia_base Orinoquia.xlsx`.
- Si ya existe la carpeta `climate/datos_crudos/palomera/` del trabajo anterior, se reutiliza la HR horaria de La Palomera para no descargarla de nuevo.
- Todo lo que produce el cuaderno se guarda en `san_carlos/` dentro de esa carpeta.

**Coordenadas.** Se convierten de grados-minutos-segundos a grados decimales: `g + m/60 + s/3600` (negativo para el Oeste).

**Umbrales epidemiológicos** (los mismos del trabajo anterior de la carpeta `climate`, tomados de la literatura):

| Enfermedad | Día favorable si… | Referencias |
|---|---|---|
| Mal Suramericano de las Hojas (SALB, *Pseudocercospora ulei*) | ≥ 10 h con HR ≥ 90 % **y** T media entre 20 y 28 °C | Holliday 1970; Gasparotto et al. 1997; Guyot et al. 2014 |
| Antracnosis / *Colletotrichum* Leaf Fall (CLF) | (≥ 12 h con HR ≥ 90 % **o** lluvia ≥ 1 mm) **y** T media entre 24 y 30 °C | Jayasinghe et al. 1997; Saha et al. 2002; Cao et al. 2019 |

Las horas con HR ≥ 90 % se usan como aproximación de las **horas de hoja mojada**, porque no hay sensores de mojadura.
""")

code(r"""
# ---------------------------------------------------------------- RUTAS
if EN_COLAB:
    from google.colab import drive
    drive.mount("/content/drive")                       # pide permiso para leer su Drive
    RUTA_DRIVE = Path("/content/drive/MyDrive/tapiero")  # <-- ✏️ CAMBIE si su carpeta se llama distinto
else:
    # Ejecución local: el cuaderno está en <proyecto>/san_carlos/
    RUTA_DRIVE = Path.cwd().parent if Path.cwd().name == "san_carlos" else Path.cwd()

ARCHIVO_CULTIVO = RUTA_DRIVE / "Fenologia_base Orinoquia.xlsx"
SALIDA   = RUTA_DRIVE / "san_carlos"            # carpeta de trabajo de este análisis
CRUDOS   = SALIDA / "datos_crudos"              # descargas (se guardan para no repetirlas)
RESULT   = SALIDA / "resultados"                # Excel
FIGS     = RESULT / "figuras"                   # figuras PNG
PREVIO_PALOMERA = RUTA_DRIVE / "climate" / "datos_crudos" / "palomera" / "ideam_aut_horario.csv"
for c in (CRUDOS / "sancarlos", CRUDOS / "palomera", FIGS):
    c.mkdir(parents=True, exist_ok=True)
assert ARCHIVO_CULTIVO.exists(), f"No encuentro {ARCHIVO_CULTIVO}. Revise RUTA_DRIVE."

# ---------------------------------------------------------------- SITIOS
def gms_a_decimal(g, m, s, hemisferio):
    # Grados-minutos-segundos -> grados decimales. Sur y Oeste son negativos.
    v = g + m / 60 + s / 3600
    return -v if hemisferio in ("S", "O", "W") else v

LOTE = dict(nombre="Lote San Carlos", lat=gms_a_decimal(4, 11, 15.52, "N"),
            lon=gms_a_decimal(72, 32, 14.55, "O"))
PALOMERA = dict(nombre="La Palomera AUT [35185010]", codigo="0035185010",
                lat=4.260321, lon=-72.564525)
PUNTOS = {"sancarlos": LOTE, "palomera": PALOMERA}   # se descargan productos en ambos puntos

# ---------------------------------------------------------------- PERIODOS
PERIODO = ("2011-01-01", "2025-12-31")      # serie climática (climatología de 15 años)
VENTANA_MESES = [1, 2, 3, 4]                # ventana de interés: enero-abril
PASO_DIAS = 8                               # longitud de los periodos (frecuencia de muestreo del cultivo)
MESES = {1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun", 7: "Jul", 8: "Ago",
         9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"}

# ---------------------------------------------------------------- UMBRALES
HR_UMBRAL = 90                                             # % HR para considerar "hoja mojada"
SALB = dict(horas_min=10, t_min=20.0, t_max=28.0)
CLF  = dict(horas_min=12, t_min=24.0, t_max=30.0, lluvia_mm=1.0)
LLUVIA_DIA_MM = 1.0                                        # día lluvioso
MIN_HORAS_DIA = 22                                         # horas válidas mínimas para calcular un día

# ---------------------------------------------------------------- COLORES (fijos por entidad)
COL_CLON = {"FX 3864": "#2a78d6", "IAN 873": "#eb6834", "RRIM 600": "#1baf7a"}
COL_FUENTE = {"La Palomera (obs.)": "#2b2b2b", "ERA5-Land": "#2a78d6",
              "ERA5-Land corregido": "#eb6834", "CHIRPS": "#1baf7a", "ERA5": "#6250d6"}
plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 300, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6e6e6",
                     "grid.linewidth": 0.6, "lines.linewidth": 1.6, "font.size": 9.5,
                     "axes.titlesize": 10.5, "axes.titleweight": "bold", "legend.frameon": False})

def guardar(fig, nombre):
    # Guarda la figura en PNG (300 dpi) dentro de resultados/figuras
    fig.savefig(FIGS / f"{nombre}.png", bbox_inches="tight")
    plt.show()

print(f"Lote San Carlos: {LOTE['lat']:.5f}, {LOTE['lon']:.5f}")
print("Resultados en:", SALIDA)
""")

md(r"""
## 0.3 Distancia lote – estación
La distancia en línea recta sobre la esfera terrestre se calcula con la fórmula de *haversine*. Si la estación está cerca (< 10–15 km en terreno plano), su clima representa bien al lote.
""")

code(r"""
def distancia_km(lat1, lon1, lat2, lon2):
    # Fórmula de haversine: distancia sobre una esfera de radio 6371 km
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))

DIST_PAL = distancia_km(LOTE["lat"], LOTE["lon"], PALOMERA["lat"], PALOMERA["lon"])
print(f"Distancia lote San Carlos – La Palomera: {DIST_PAL:.1f} km")
""")

md(r"""
---
# 1. Descarga de datos climáticos

| Fuente | Qué es | Resolución | Variables usadas |
|---|---|---|---|
| **ERA5-Land** (ECMWF/Copernicus, vía API Open-Meteo) | Reanálisis: modelo + observaciones | 9 km, horaria | T, HR, punto de rocío |
| **ERA5** (vía Open-Meteo) | Reanálisis global | 25 km, diaria | Lluvia, radiación solar, evapotranspiración de referencia (ETo FAO-56) |

*Nota:* Open-Meteo no publica la lluvia de ERA5-Land, por eso la lluvia del reanálisis viene de ERA5 (25 km).
| **CHIRPS v2.0** (UCSB-CHC) | Lluvia satelital calibrada con pluviómetros | 5 km, diaria | Lluvia |
| **IDEAM La Palomera AUT** (datos.gov.co) | Estación automática | puntual, cada 10 min | HR, T, lluvia |

Cada descarga se guarda en `san_carlos/datos_crudos/`. Si el archivo ya existe **no se vuelve a descargar** (así se ahorra tiempo y se puede trabajar sin internet).

## 1.1 ERA5-Land horario y ERA5 diario (Open-Meteo)
La API *archive* de Open-Meteo entrega el reanálisis para un punto. `models=era5_land` fuerza la versión de 9 km. Las horas se piden en hora local (`America/Bogota`) para que el "día" coincida con el de la estación.
""")

code(r"""
URL_OM = "https://archive-api.open-meteo.com/v1/archive"

def open_meteo(lat, lon, params, ruta):
    # Descarga (o lee si ya existe) una serie de Open-Meteo y la guarda como CSV
    if ruta.exists():
        return pd.read_csv(ruta, index_col=0, parse_dates=True)
    base = dict(latitude=lat, longitude=lon, start_date=PERIODO[0], end_date=PERIODO[1],
                timezone="America/Bogota")
    for intento in range(5):                              # reintentos si la API está ocupada
        r = requests.get(URL_OM, params={**base, **params}, timeout=300)
        if r.status_code == 200:
            break
        time.sleep(20 * (intento + 1))
    r.raise_for_status()
    js = r.json()
    clave = "hourly" if "hourly" in params else "daily"
    d = pd.DataFrame(js[clave]).rename(columns={"time": "fecha"})
    d["fecha"] = pd.to_datetime(d["fecha"])
    d = d.set_index("fecha")
    print(f"   descargado {ruta.name}: celda {js['latitude']:.2f}, {js['longitude']:.2f} | {len(d)} filas")
    d.to_csv(ruta)
    return d

era5h, era5d = {}, {}
for k, p in PUNTOS.items():
    era5h[k] = open_meteo(p["lat"], p["lon"],
                          dict(hourly="temperature_2m,relative_humidity_2m,dew_point_2m",
                               models="era5_land"),
                          CRUDOS / k / "era5land_horario.csv")
    era5h[k].columns = ["t", "hr", "td"]                   # nombres cortos
    era5d[k] = open_meteo(p["lat"], p["lon"],
                          dict(daily="shortwave_radiation_sum,et0_fao_evapotranspiration,precipitation_sum", models="era5"),
                          CRUDOS / k / "era5_rad_etp.csv")
    era5d[k].columns = ["rad", "etp", "prec"]               # MJ/m²/día, mm/día, mm/día
print({k: (v.index.min().date(), v.index.max().date()) for k, v in era5h.items()})
""")

md(r"""
## 1.2 CHIRPS diario (vía ClimateSERV, NASA-USAID SERVIR)
CHIRPS v2.0 se obtiene de la API pública **ClimateSERV**, que calcula la serie diaria de un polígono directamente en el servidor. Se usa un cuadrado de ~500 m alrededor de cada punto, que queda dentro de un solo píxel CHIRPS de 5 km, así que el valor es el del píxel.

> ¿Por qué no se baja directamente del servidor de UCSB? Ese servidor bloquea la IP (sistema anti-abuso *CrowdSec*) cuando recibe miles de peticiones seguidas, como pasó al preparar este cuaderno. ClimateSERV da **exactamente los mismos valores** (se verificó con la serie de Taluma del trabajo anterior: r = 1.0, diferencia máxima 0 mm en 730 días) y solo necesita unas pocas peticiones.

Pasos de la API: (1) `submitDataRequest` envía el pedido y devuelve un identificador; (2) `getDataRequestProgress` informa el avance (0–100 %); (3) `getDataFromRequest` entrega los datos. Se pide por bloques de 5 años.
""")

code(r"""
URL_CS = "https://climateserv.servirglobal.net/api/"

def chirps_climateserv(lat, lon, inicio, fin, medio_lado=0.0024):
    # Serie diaria CHIRPS (datatype=0) promediada en un cuadrado alrededor del punto (operationtype=5 = promedio)
    h = medio_lado
    geom = json.dumps({"type": "Polygon", "coordinates": [[[lon - h, lat - h], [lon + h, lat - h], [lon + h, lat + h],
                                                           [lon - h, lat + h], [lon - h, lat - h]]]})
    q = dict(datatype=0, begintime=inicio.strftime("%m/%d/%Y"), endtime=fin.strftime("%m/%d/%Y"),
             intervaltype=0, operationtype=5, geometry=geom)
    ident = requests.get(URL_CS + "submitDataRequest/", params=q, timeout=120).json()[0]
    for _ in range(400):                                   # espera hasta ~20 min
        avance = requests.get(URL_CS + "getDataRequestProgress/", params={"id": ident}, timeout=60).json()[0]
        if avance >= 100: break
        if avance < 0: raise RuntimeError("ClimateSERV devolvió un error")
        time.sleep(3)
    datos = requests.get(URL_CS + "getDataFromRequest/", params={"id": ident}, timeout=300).json()["data"]
    s = pd.Series({pd.to_datetime(x["date"], format="%m/%d/%Y"): x["value"]["avg"] for x in datos}, dtype=float)
    return s.where(s >= 0)                                 # valores negativos = sin dato

def descargar_chirps():
    ruta = CRUDOS / "chirps_diario.csv"
    if ruta.exists():
        return pd.read_csv(ruta, index_col=0, parse_dates=True).astype(float)
    t0, t1 = pd.Timestamp(PERIODO[0]), pd.Timestamp(PERIODO[1])
    bloques = [(a, min(a + pd.DateOffset(years=5) - pd.Timedelta(days=1), t1))
               for a in pd.date_range(t0, t1, freq="5YS")]
    tabla = {}
    for k, p in PUNTOS.items():
        partes = []
        for a, b in bloques:
            partes.append(chirps_climateserv(p["lat"], p["lon"], a, b))
            print(f"   CHIRPS {k}: {a.date()} → {b.date()} listo")
        tabla[k] = pd.concat(partes).sort_index()
    df = pd.DataFrame(tabla).rename_axis("fecha")
    df.to_csv(ruta)
    return df

chirps = descargar_chirps()
print(chirps.describe().round(2))
""")

md(r"""
## 1.3 Estación automática IDEAM La Palomera (datos.gov.co)
El IDEAM publica en datos.gov.co las observaciones de sus estaciones automáticas cada 10 minutos (API *Socrata*):

| Variable | Conjunto de datos | Agregación horaria |
|---|---|---|
| Humedad del aire a 2 m | `uext-mhny` | promedio |
| Temperatura del aire a 2 m | `sbwg-7ju4` | promedio |
| Precipitación | `s54a-sgyg` | **suma** |

La HR y T horarias ya se descargaron en el trabajo anterior (`climate/datos_crudos/palomera/`); si existen, se copian. La lluvia se descarga aquí.
""")

code(r"""
URL_SOC = "https://www.datos.gov.co/resource/{ds}.csv"
DS_IDEAM = {"hr": "uext-mhny", "t": "sbwg-7ju4", "prec": "s54a-sgyg"}

def socrata(ds, codigo, lote=200000):
    # Descarga por páginas todas las observaciones de una estación en un conjunto de datos
    partes, offset = [], 0
    while True:
        q = {"$select": "fechaobservacion,valorobservado", "$where": f"codigoestacion='{codigo}'",
             "$order": "fechaobservacion", "$limit": lote, "$offset": offset}
        r = requests.get(URL_SOC.format(ds=ds), params=q, timeout=1800); r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text)); partes.append(df)
        if len(df) < lote: break
        offset += lote
    d = pd.concat(partes)
    d["fecha"] = pd.to_datetime(d["fechaobservacion"])
    return d.set_index("fecha")["valorobservado"].astype(float).sort_index()

def palomera_horaria():
    ruta = CRUDOS / "palomera" / "ideam_aut_horario.csv"
    if ruta.exists():
        return pd.read_csv(ruta, index_col=0, parse_dates=True)
    if PREVIO_PALOMERA.exists():                      # reutiliza HR y T del trabajo anterior
        h = pd.read_csv(PREVIO_PALOMERA, index_col=0, parse_dates=True)[["hr", "t"]]
    else:
        h = pd.DataFrame({v: socrata(DS_IDEAM[v], PALOMERA["codigo"]) for v in ("hr", "t")})
        h = h.groupby(h.index.floor("h")).mean()
    crudo_p = CRUDOS / "palomera" / "ideam_aut_prec_crudo.csv"
    try:
        if crudo_p.exists() and crudo_p.stat().st_size > 1000:
            p = pd.read_csv(crudo_p); p.index = pd.to_datetime(p["fechaobservacion"])
            p = p["valorobservado"].astype(float).sort_index()
        else:
            p = socrata(DS_IDEAM["prec"], PALOMERA["codigo"])
        p = p[~p.index.duplicated()]
        hp = p.groupby(p.index.floor("h")).agg(["sum", "count"])
        h = h.join(hp["sum"].rename("prec"), how="outer").join(hp["count"].rename("n_prec"), how="left")
    except Exception as e:
        print("   No se pudo obtener la lluvia de La Palomera:", e)
        h["prec"], h["n_prec"] = np.nan, np.nan
    h.rename_axis("fecha_hora").to_csv(ruta)
    return h

pal_h = palomera_horaria()
print(pal_h.describe().round(1))
print("Periodo:", pal_h.index.min(), "→", pal_h.index.max())
""")

md(r"""
---
# 2. Estación La Palomera: control de calidad y datos diarios

**Control de calidad (QC)** antes de comparar:
1. **Rango físico:** HR fuera de 10–100 % o T fuera de 10–45 °C → se descarta (QC básico).
2. **Filtro del sensor de temperatura** (problema detectado en este análisis): entre 2011 y 2012 el sensor de T de La Palomera marcó medias diarias de 12–15 °C, imposibles en los Llanos. El filtro descarta las horas con T fuera de 15–42 °C y los días con T media fuera de 20–33 °C.

   ⚠️ **Se conservan las dos versiones** para documentar el problema y su efecto en la inferencia:
   - `pal_d_sf` → **sin filtro** (datos como vienen del IDEAM, solo QC básico).
   - `pal_d` → **con filtro** (versión principal, la que se usa en el resto del cuaderno).

   La comparación está en la sección **3.1**.
3. **Sensor pegado:** la misma HR durante 12 horas seguidas (y < 99 %) indica un sensor bloqueado → se descarta.
4. **Lluvia:** horas con > 100 mm se descartan. Un día de lluvia solo se acepta si tiene registros en ≥ 22 horas, porque la estación registra ceros (si faltan horas, el total del día queda subestimado).

**De horario a diario.** Un día se calcula solo si tiene ≥ 22 horas válidas (`MIN_HORAS_DIA`):
- `tmed`, `tmax`, `tmin`: media, máxima y mínima de las horas.
- `hr`: HR media.
- `hr90_horas`: número de horas con HR ≥ 90 % (horas de hoja mojada aproximadas).
- `dpv`: déficit de presión de vapor (kPa), `DPV = es(T)·(1 − HR/100)`, con `es(T) = 0.6108·exp(17.27·T/(T+237.3))`. Mide la "sed" del aire; un DPV alto seca la hoja y frena la germinación de esporas.
""")

code(r"""
def qc_horario(h, filtro_sensor=True):
    # filtro_sensor=False -> solo QC básico (versión "sin filtro", con el problema del sensor de T)
    # filtro_sensor=True  -> además elimina los días con T imposible (versión "con filtro", la principal)
    h = h.copy()
    h["hr"] = h["hr"].where(h["hr"].between(10, 100))
    if filtro_sensor:
        h["t"] = h["t"].where(h["t"].between(15, 42))      # rango horario plausible en los Llanos
        # Días con T media fuera de 20-33 °C = sensor dañado (p. ej. 2011-2012 marcó medias de 12-15 °C)
        t_dia = h["t"].groupby(h.index.normalize()).transform("mean")
        h.loc[~t_dia.between(20, 33), "t"] = np.nan
    else:
        h["t"] = h["t"].where(h["t"].between(10, 45))      # QC básico del trabajo anterior
    pegado = h["hr"].diff().eq(0).rolling(12).sum().ge(11) & h["hr"].lt(99)   # sensor bloqueado
    h.loc[pegado, "hr"] = np.nan
    if "prec" in h:
        h["prec"] = h["prec"].where(h["prec"].between(0, 100))
    return h

def dpv_kpa(t, hr):
    es = 0.6108 * np.exp(17.27 * t / (t + 237.3))     # presión de vapor de saturación (kPa)
    return es * (1 - hr / 100)

def a_diario(h, sufijo):
    # Convierte una tabla horaria (t, hr, [prec]) en diaria, exigiendo MIN_HORAS_DIA horas válidas
    dia = h.index.normalize()
    g = h.groupby(dia)
    n_t, n_hr = g["t"].count(), g["hr"].count()
    ok_t, ok_hr = n_t >= MIN_HORAS_DIA, n_hr >= MIN_HORAS_DIA
    d = pd.DataFrame({
        "tmed": g["t"].mean().where(ok_t), "tmax": g["t"].max().where(ok_t), "tmin": g["t"].min().where(ok_t),
        "hr": g["hr"].mean().where(ok_hr),
        "hr90_horas": (h["hr"] >= HR_UMBRAL).groupby(dia).sum().where(ok_hr),
        "dpv": dpv_kpa(h["t"], h["hr"]).groupby(dia).mean().where(ok_t & ok_hr),
    })
    if "prec" in h:
        n_p = (h["n_prec"] if "n_prec" in h else h["prec"].notna()).gt(0).groupby(dia).sum()
        d["prec"] = h["prec"].groupby(dia).sum(min_count=1).where(n_p >= MIN_HORAS_DIA)
    d.index.name = "fecha"
    return d.add_suffix(sufijo)

pal_h_bruto = pal_h.copy()                                   # tal como se descargó
pal_h_sf = qc_horario(pal_h_bruto, filtro_sensor=False)      # versión SIN filtro del sensor de T
pal_h = qc_horario(pal_h_bruto, filtro_sensor=True)          # versión CON filtro (principal)
pal_d_sf = a_diario(pal_h_sf.loc[PERIODO[0]:PERIODO[1]], "_pal")
pal_d = a_diario(pal_h.loc[PERIODO[0]:PERIODO[1]], "_pal")

# Cobertura: % de días con dato por año (importa para saber qué años se pueden usar)
cob = pal_d.notna().groupby(pal_d.index.year).mean().mul(100).round(0)
print("% de días con dato en La Palomera, por año:")
print(cob[["tmed_pal", "hr90_horas_pal", "prec_pal"]].T.to_string())
""")

md(r"""
### Figura 2.1 – Disponibilidad de datos en La Palomera
Cada celda es un mes; el color indica el % de días con dato. Sirve para ver huecos antes de validar.
""")

code(r"""
fig, axs = plt.subplots(1, 3, figsize=(12, 3.6), sharey=True)
for ax, (var, tit) in zip(axs, [("tmed_pal", "Temperatura"), ("hr90_horas_pal", "HR horaria"), ("prec_pal", "Lluvia")]):
    m = pal_d[var].notna().groupby([pal_d.index.year, pal_d.index.month]).mean().unstack() * 100
    im = ax.imshow(m.values, aspect="auto", cmap="Blues", vmin=0, vmax=100)
    ax.set_xticks(range(12)); ax.set_xticklabels([MESES[i][0] for i in range(1, 13)])
    ax.set_yticks(range(len(m.index))); ax.set_yticklabels(m.index); ax.set_title(tit); ax.grid(False)
fig.colorbar(im, ax=axs, label="% de días con dato", shrink=0.8)
fig.suptitle("La Palomera AUT: disponibilidad mensual de datos", y=1.02)
guardar(fig, "2_1_disponibilidad_palomera")
""")

md(r"""
---
# 3. ¿Se pueden correlacionar La Palomera, CHIRPS y ERA5-Land de enero a abril?

Se comparan los productos **en la celda de La Palomera** (no en el lote), para que la diferencia sea solo del producto y no de la distancia.

**Escalas temporales.** La lluvia diaria casi nunca coincide entre un satélite y un pluviómetro (una tormenta convectiva puede caer a 2 km de la estación). Por eso se compara a tres escalas:
- **diaria**,
- **8 días** (la misma frecuencia del muestreo del cultivo),
- **mensual**.

Los periodos de 8 días empiezan el 1 de enero de cada año (1–8 ene, 9–16 ene, …); un agregado solo se calcula si hay ≥ 80 % de días con dato en los dos productos.

**Métricas:**
- *Sesgo* = media(producto − estación): error sistemático (+ sobreestima, − subestima).
- *MAE* = error absoluto medio; *RMSE* = raíz del error cuadrático medio (penaliza errores grandes).
- *r* de Pearson (relación lineal) y *ρ* de Spearman (relación por rangos, robusta a valores extremos).
- Para la lluvia diaria, además: **POD** (probabilidad de detectar un día lluvioso), **FAR** (falsas alarmas) y **CSI** (índice de acierto crítico).
""")

code(r"""
def productos_diarios(k):
    # Tabla diaria de productos en el punto k: ERA5-Land (T, HR), ERA5 (lluvia, rad, ETo) y CHIRPS (lluvia)
    e = a_diario(era5h[k], "_era5")
    e = e.join(era5d[k].add_suffix("_era5"))
    e["prec_chirps"] = chirps[k]
    return e.loc[PERIODO[0]:PERIODO[1]]

prod_pal = productos_diarios("palomera")
base_val = pal_d.join(prod_pal, how="inner")

def periodo8(idx):
    # Número de periodo de 8 días dentro del año (1 = 1-8 ene, 2 = 9-16 ene, ...)
    return (idx.dayofyear - 1) // PASO_DIAS + 1

def agregar(df, escala, suma):
    # Agrega a 8 días o mensual; 'suma' = True para lluvia, False para promedio
    if escala == "diaria":
        return df
    clave = [df.index.year, periodo8(df.index)] if escala == "8 días" else [df.index.year, df.index.month]
    g = df.groupby(clave)
    out = g.sum(min_count=1) if suma else g.mean()
    n_ok = g.count().min(axis=1); n_tot = g.size()
    return out[(n_ok / n_tot) >= 0.8]

def metricas(o, p):
    m = pd.concat([o, p], axis=1).dropna(); o, p = m.iloc[:, 0], m.iloc[:, 1]
    if len(m) < 10: return dict(n=len(m))
    return dict(n=len(m), media_obs=o.mean(), media_prod=p.mean(), sesgo=(p - o).mean(),
                MAE=(p - o).abs().mean(), RMSE=np.sqrt(((p - o) ** 2).mean()),
                r_pearson=o.corr(p), rho_spearman=o.corr(p, method="spearman"))

COMPARAR = [  # (variable, columna estación, columna producto, nombre producto, es suma)
    ("T media (°C)", "tmed_pal", "tmed_era5", "ERA5-Land", False),
    ("T máxima (°C)", "tmax_pal", "tmax_era5", "ERA5-Land", False),
    ("T mínima (°C)", "tmin_pal", "tmin_era5", "ERA5-Land", False),
    ("HR media (%)", "hr_pal", "hr_era5", "ERA5-Land", False),
    ("Horas HR≥90 % (h/día)", "hr90_horas_pal", "hr90_horas_era5", "ERA5-Land", False),
    ("DPV (kPa)", "dpv_pal", "dpv_era5", "ERA5-Land", False),
    ("Lluvia (mm)", "prec_pal", "prec_chirps", "CHIRPS", True),
    ("Lluvia (mm)", "prec_pal", "prec_era5", "ERA5", True),
]

filas = []
for ventana, sel in [("Ene–Abr", base_val.index.month.isin(VENTANA_MESES)), ("Año completo", slice(None))]:
    sub = base_val[sel]
    for escala in ["diaria", "8 días", "mensual"]:
        for var, co, cp, prod, suma in COMPARAR:
            a = agregar(sub[[co, cp]], escala, suma)
            filas.append(dict(ventana=ventana, escala=escala, variable=var, producto=prod,
                              **metricas(a[co], a[cp])))
VALIDACION = pd.DataFrame(filas).round(3)
VALIDACION[VALIDACION.ventana == "Ene–Abr"]
""")

md(r"""
## 3.1 Problema del sensor de temperatura de La Palomera: datos con y sin filtro

**Observación.** Al comparar la temperatura de La Palomera con ERA5-Land se encontró que entre **2011 y 2012** el sensor marcó medias diarias de **12–15 °C** durante semanas (por ejemplo, de octubre de 2011 en adelante), mientras ERA5-Land marcaba 25–27 °C. En los Llanos Orientales a ~200 m s. n. m. no existen medias diarias tan bajas, así que son **errores del sensor**, no clima real. El patrón (un desplazamiento constante y no picos aislados) sugiere un sensor descalibrado o un cambio de sensor sin registrar.

**Se comparan las dos versiones:**
- **Sin filtro**: datos como los entrega el IDEAM (solo QC básico 10–45 °C).
- **Con filtro**: se descartan horas fuera de 15–42 °C y días con T media fuera de 20–33 °C.

**Posible problema en la inferencia:**
1. **Validación de productos:** sin filtro, la correlación de T con ERA5-Land queda artificialmente baja y el sesgo artificialmente alto. Se podría concluir, erradamente, que ERA5-Land no sirve para T en el sitio.
2. **Corrección de la HR:** la corrección por cuantiles (sección 4) usa solo la HR, así que **no se ve afectada**.
3. **Indicadores de riesgo con datos de la estación** (`salb_fav_pal`, `clf_fav_pal`): usan la T media. Con medias de 13 °C ningún día cumple el rango de 20–28 °C, y se subestimaría el riesgo. Esto solo afecta los años con el problema.
4. **Relación con el cultivo (2017–2020):** depende de cuántos días malos caen en esos años. La tabla de abajo lo cuantifica, y la sección 8.3 compara los ρ con y sin filtro.
""")

code(r"""
# Días con T eliminados por el filtro, por año (días que tenían T media sin filtro y la pierden con filtro)
t_sf, t_cf = pal_d_sf["tmed_pal"], pal_d["tmed_pal"]
quitados = t_sf.notna() & t_cf.isna()
SENSOR_DIAS = pd.DataFrame({"dias_con_T_sin_filtro": t_sf.notna().groupby(t_sf.index.year).sum(),
                            "dias_eliminados": quitados.groupby(t_sf.index.year).sum(),
                            "T_media_dias_eliminados": t_sf[quitados].groupby(t_sf[quitados].index.year).mean()})
SENSOR_DIAS["pct_eliminado"] = 100 * SENSOR_DIAS.dias_eliminados / SENSOR_DIAS.dias_con_T_sin_filtro
SENSOR_DIAS = SENSOR_DIAS.rename_axis("anio").reset_index().round(2)
print(SENSOR_DIAS.to_string(index=False))
anios_cult = SENSOR_DIAS.anio.between(2016, 2020)
print(f"\nDías eliminados en los años del cultivo (2016–2020): {int(SENSOR_DIAS.loc[anios_cult, 'dias_eliminados'].sum())}")

# Validación de la temperatura con las dos versiones
filas = []
for version, pdd in [("Sin filtro", pal_d_sf), ("Con filtro", pal_d)]:
    b = pdd.join(prod_pal, how="inner")
    for ventana, sel in [("Ene–Abr", b.index.month.isin(VENTANA_MESES)), ("Año completo", slice(None))]:
        for escala in ["diaria", "8 días", "mensual"]:
            for var, co, cp in [("T media (°C)", "tmed_pal", "tmed_era5"), ("T máxima (°C)", "tmax_pal", "tmax_era5"),
                                ("T mínima (°C)", "tmin_pal", "tmin_era5")]:
                a = agregar(b[sel][[co, cp]], escala, False)
                filas.append(dict(version=version, ventana=ventana, escala=escala, variable=var, **metricas(a[co], a[cp])))
SENSOR_VAL = pd.DataFrame(filas).round(3)
SENSOR_VAL.pivot_table(index=["ventana", "variable", "escala"], columns="version", values=["r_pearson", "sesgo"]).round(2)
""")

md(r"""
### Figura 3.3 – Temperatura media diaria de La Palomera sin filtro, con filtro y ERA5-Land
Los puntos rojos son los días que elimina el filtro. Se ve el bloque de 2011–2012 con medias de ~13 °C.
""")

code(r"""
e_dia = prod_pal["tmed_era5"]
fig, ax = plt.subplots(figsize=(13, 3.8))
ax.plot(e_dia.index, e_dia.rolling(7, center=True).mean(), color=COL_FUENTE["ERA5-Land"], lw=1, label="ERA5-Land (media móvil 7 d)")
ax.scatter(t_cf.index, t_cf, s=2, color="#2b2b2b", label="La Palomera con filtro")
ax.scatter(t_sf[quitados].index, t_sf[quitados], s=5, color="#e34948", label="Eliminados por el filtro (sin filtro)")
ax.set_ylabel("T media diaria (°C)"); ax.legend(loc="lower right", ncol=3, markerscale=3)
ax.set_title("Problema del sensor de temperatura de La Palomera")
guardar(fig, "3_3_sensor_T_palomera")
""")

code(r"""
def deteccion_lluvia(o, p, umbral=LLUVIA_DIA_MM):
    # Tabla de contingencia de días lluviosos: aciertos, fallos, falsas alarmas
    m = pd.concat([o, p], axis=1).dropna(); lo, lp = m.iloc[:, 0] >= umbral, m.iloc[:, 1] >= umbral
    a, b, c = (lo & lp).sum(), (~lo & lp).sum(), (lo & ~lp).sum()
    return dict(n=len(m), POD=a / (a + c), FAR=b / (a + b), CSI=a / (a + b + c))

sub = base_val[base_val.index.month.isin(VENTANA_MESES)]
DETECCION = pd.DataFrame([
    dict(producto=prod, desfase_dias=lag, **deteccion_lluvia(sub["prec_pal"], base_val[cp].shift(-lag).reindex(sub.index)))
    for prod, cp in [("CHIRPS", "prec_chirps"), ("ERA5", "prec_era5")] for lag in (0, 1)]).round(3)
# desfase 1 = el producto se compara con el día siguiente (el IDEAM a veces registra la lluvia de 7 am a 7 am)
DETECCION
""")

md(r"""
### Figura 3.1 – Dispersión estación vs. producto, enero–abril
Cada punto es un día (gris) o un periodo de 8 días (color). La línea discontinua es la relación 1:1 (acuerdo perfecto). Si los puntos de 8 días se acercan más a la línea que los diarios, conviene trabajar con agregados de 8 días.
""")

code(r"""
pares = [("T media (°C)", "tmed_pal", "tmed_era5", "ERA5-Land", False),
         ("Horas HR≥90 %", "hr90_horas_pal", "hr90_horas_era5", "ERA5-Land", False),
         ("DPV (kPa)", "dpv_pal", "dpv_era5", "ERA5-Land", False),
         ("Lluvia CHIRPS (mm)", "prec_pal", "prec_chirps", "CHIRPS", True),
         ("Lluvia ERA5 (mm)", "prec_pal", "prec_era5", "ERA5", True)]
fig, axs = plt.subplots(1, 5, figsize=(16, 3.6))
for ax, (tit, co, cp, prod, suma) in zip(axs, pares):
    d = sub[[co, cp]].dropna(); a8 = agregar(sub[[co, cp]], "8 días", suma).dropna()
    if suma: a8 = a8 / PASO_DIAS                     # lluvia de 8 días expresada como mm/día para comparar
    ax.scatter(d[co], d[cp], s=6, color="#bdbdbd", alpha=0.5, label="diaria")
    ax.scatter(a8[co], a8[cp], s=14, color=COL_FUENTE[prod], label="8 días" + (" (mm/día)" if suma else ""))
    lim = [np.nanmin([d.min().min(), 0 if suma else d.min().min()]), d.max().max()]
    ax.plot(lim, lim, "--", color="#555", lw=1)
    r1, r8 = d[co].corr(d[cp]), a8[co].corr(a8[cp])
    ax.set_title(tit); ax.set_xlabel("La Palomera (obs.)"); ax.set_ylabel(prod)
    ax.text(0.03, 0.97, f"r diaria = {r1:.2f}\nr 8 días = {r8:.2f}", transform=ax.transAxes, va="top", fontsize=8.5)
axs[0].legend(loc="lower right", fontsize=8)
fig.suptitle("Validación enero–abril en la celda de La Palomera", y=1.03)
guardar(fig, "3_1_dispersion_validacion_ene_abr")
""")

md(r"""
### Figura 3.2 – La correlación mejora al agregar en el tiempo
Correlación de Pearson (r) por variable y escala en enero–abril. Barras más altas = mejor acuerdo.
""")

code(r"""
v = VALIDACION[(VALIDACION.ventana == "Ene–Abr")].copy()
v["etiqueta"] = v["variable"] + "\n" + v["producto"]
tab = v.pivot_table(index="etiqueta", columns="escala", values="r_pearson")[["diaria", "8 días", "mensual"]]
fig, ax = plt.subplots(figsize=(11, 3.8))
x = np.arange(len(tab)); w = 0.26
for i, (esc, col) in enumerate(zip(tab.columns, ["#9cc3ee", "#2a78d6", "#0d3f80"])):
    ax.bar(x + (i - 1) * w, tab[esc], w * 0.92, color=col, label=esc)
ax.set_xticks(x); ax.set_xticklabels(tab.index, fontsize=8); ax.set_ylabel("r de Pearson"); ax.set_ylim(-0.1, 1)
ax.axhline(0, color="#999", lw=0.8); ax.legend(title="Escala", ncol=3, loc="upper left")
ax.set_title("Acuerdo estación–producto en enero–abril según la escala de agregación")
guardar(fig, "3_2_correlacion_por_escala")
tab.round(2)
""")

md(r"""
---
# 4. Corrección de la humedad relativa de ERA5-Land con La Palomera

**Problema.** Los reanálisis suelen tener noches demasiado secas en los Llanos durante la época seca: casi nunca alcanzan HR ≥ 90 %, mientras que la estación sí. Si se usara ERA5-Land tal cual, se subestimaría el riesgo de infección.

**Solución: mapeo empírico de cuantiles (*quantile mapping*, QM).** Para cada **mes** y **bloque de 3 horas** del día:
1. Se ordenan los valores de HR de ERA5-Land y de la estación en las horas en que ambos tienen dato.
2. Se calculan sus percentiles (0, 1, …, 100).
3. A cada valor de ERA5-Land se le asigna el valor de la estación que tiene el mismo percentil.

Así la corrección conserva *cuándo* está húmedo según ERA5-Land, pero ajusta *cuánto* según la estación. Agrupar por mes y hora respeta el ciclo diario y estacional.

**Validación cruzada.** Para no "hacer trampa", se entrena con los años impares y se prueba en los pares, y viceversa.

**Para el lote.** La corrección entrenada en la celda de La Palomera se aplica a la celda del lote (están a pocos km y en el mismo paisaje de sabana).
""")

code(r"""
CUANTILES = np.linspace(0, 1, 101)

def clave_qm(idx):
    return idx.month * 10 + idx.hour // 3            # p. ej. 13 = enero, bloque 3-5 h

def entrenar_qm(obs, mod):
    m = pd.concat({"o": obs, "m": mod}, axis=1).dropna()
    return {k: (np.quantile(g["m"], CUANTILES), np.quantile(g["o"], CUANTILES))
            for k, g in m.groupby(clave_qm(m.index))}

def aplicar_qm(mod, tabla):
    out = mod.astype(float).copy(); claves = clave_qm(mod.index)
    for k, (qm, qo) in tabla.items():
        sel = claves == k
        out[sel] = np.interp(mod[sel], qm, qo)        # interpolación entre percentiles
    return out.clip(0, 100)

obs_hr = pal_h["hr"].loc[PERIODO[0]:PERIODO[1]]
mod_hr = era5h["palomera"]["hr"]
impar = mod_hr.index.year % 2 == 1
# Validación cruzada: corrige años pares con lo aprendido en impares y viceversa
hr_cv = pd.concat([aplicar_qm(mod_hr[~impar], entrenar_qm(obs_hr[obs_hr.index.year % 2 == 1], mod_hr)),
                   aplicar_qm(mod_hr[impar],  entrenar_qm(obs_hr[obs_hr.index.year % 2 == 0], mod_hr))]).sort_index()

def horas90(hr):
    dia = hr.index.normalize(); n = hr.groupby(dia).count()
    return (hr >= HR_UMBRAL).groupby(dia).sum().where(n >= MIN_HORAS_DIA)

h_obs = horas90(obs_hr)
filas = []
for nombre, serie in [("ERA5-Land", mod_hr), ("ERA5-Land corregido", hr_cv)]:
    m = pd.concat([h_obs, horas90(serie)], axis=1).dropna(); m.columns = ["obs", "prod"]
    for vent, mm in [("Año completo", m), ("Ene–Abr", m[m.index.month.isin(VENTANA_MESES)])]:
        filas.append(dict(producto=nombre, ventana=vent, n_dias=len(mm), horas_obs=mm.obs.mean(),
                          horas_prod=mm["prod"].mean(), sesgo_h=(mm["prod"] - mm.obs).mean(),
                          MAE_h=(mm["prod"] - mm.obs).abs().mean(), r=mm.obs.corr(mm["prod"]),
                          acierto_umbral_SALB_pct=100 * ((mm.obs >= SALB["horas_min"]) == (mm["prod"] >= SALB["horas_min"])).mean()))
VALID_QM = pd.DataFrame(filas).round(2)
VALID_QM
""")

md(r"""
### Figura 4.1 – Horas diarias con HR ≥ 90 % por mes: estación, ERA5-Land y ERA5-Land corregido
La curva corregida debería quedar sobre la de la estación. La franja gris marca enero–abril.
""")

code(r"""
m = pd.concat({"La Palomera (obs.)": h_obs, "ERA5-Land": horas90(mod_hr), "ERA5-Land corregido": horas90(hr_cv)}, axis=1).dropna()
clim = m.groupby(m.index.month).mean()
fig, ax = plt.subplots(figsize=(7.5, 3.6))
ax.axvspan(0.5, 4.5, color="#f0f0f0", zorder=0)
for c in clim:
    ax.plot(clim.index, clim[c], marker="o", ms=4, color=COL_FUENTE[c], label=c,
            ls="--" if c == "ERA5-Land corregido" else "-")
ax.set_xticks(range(1, 13)); ax.set_xticklabels([MESES[i] for i in range(1, 13)])
ax.set_ylabel("horas/día con HR ≥ 90 %"); ax.legend(); ax.set_ylim(0, None)
ax.set_title("Corrección de la HR de ERA5-Land (validación cruzada por años)")
guardar(fig, "4_1_correccion_hr_mensual")
""")

md(r"""
---
# 5. Base climática diaria del lote San Carlos (2011–2025)

Se arma una tabla con una fila por día y estas fuentes:

| Sufijo | Fuente | Variables |
|---|---|---|
| `_era5c` | ERA5-Land en el lote con HR **corregida** (QM entrenado con todos los años de La Palomera) | T, HR, horas HR ≥ 90 %, DPV — **fuente principal** (serie completa y homogénea) |
| `_era5` | ERA5-Land en el lote sin corregir, + ERA5 | HR sin corregir; lluvia, radiación y ETo de ERA5 |
| `_chirps` | CHIRPS en el lote | lluvia — **fuente principal de lluvia** |
| `_pal` | La Palomera observada (a pocos km) | T, HR, horas HR ≥ 90 %, lluvia — **análisis de sensibilidad** |

**Indicadores de riesgo diarios:**
- `salb_fav`: 1 si el día cumple la condición de SALB.
- `clf_fav`: 1 si el día cumple la condición de Antracnosis/CLF.
- `lluvia_dia`: 1 si llovió ≥ 1 mm.

**Medias móviles** (suavizan el ruido de un día):
- *Retrasada* `_ma3r`, `_ma7r`: promedio del día y los 2 (o 6) anteriores. Usa solo el pasado → es la adecuada para relacionar con la enfermedad o para alertas.
- *Centrada* `_ma3c`, `_ma7c`: promedio alrededor del día. Solo para describir.
- La lluvia se **acumula** en lugar de promediarse (`_acum3r`, `_acum7r`).
""")

code(r"""
# 1) Corrección QM entrenada con todo el periodo de La Palomera y aplicada a la celda del lote
TABLA_QM = entrenar_qm(obs_hr, era5h["palomera"]["hr"])
h_lote = era5h["sancarlos"].copy()
h_lote_c = h_lote.assign(hr=aplicar_qm(h_lote["hr"], TABLA_QM))

# 2) Tabla diaria del lote
D = a_diario(h_lote_c, "_era5c")[["tmed_era5c", "tmax_era5c", "tmin_era5c", "hr_era5c", "hr90_horas_era5c", "dpv_era5c"]]
D = D.join(a_diario(h_lote, "_era5")[["hr_era5", "hr90_horas_era5"]])
D = D.join(era5d["sancarlos"].add_suffix("_era5"))
D["prec_chirps"] = chirps["sancarlos"]
D = D.join(pal_d)                                         # La Palomera con filtro (sensibilidad)
D = D.join(pal_d_sf[["tmed_pal", "tmin_pal", "tmax_pal", "dpv_pal"]].add_suffix("_sf"))   # T sin filtro
D = D.loc[PERIODO[0]:PERIODO[1]]

# 3) Indicadores de riesgo (fuente principal: T y HR de ERA5-Land corregido; lluvia CHIRPS)
def indicadores(df, sT, sH, sP):
    t, h, p = df[f"tmed{sT}"], df[f"hr90_horas{sH}"], df[f"prec{sP}"]
    salb = ((h >= SALB["horas_min"]) & t.between(SALB["t_min"], SALB["t_max"])).astype(float)
    clf = (((h >= CLF["horas_min"]) | (p >= CLF["lluvia_mm"])) & t.between(CLF["t_min"], CLF["t_max"])).astype(float)
    falta = t.isna() | h.isna()
    return salb.mask(falta), clf.mask(falta | p.isna())

D["salb_fav"], D["clf_fav"] = indicadores(D, "_era5c", "_era5c", "_chirps")
D["salb_fav_pal"], D["clf_fav_pal"] = indicadores(D, "_pal", "_pal", "_pal")
D["salb_fav_pal_sf"], D["clf_fav_pal_sf"] = indicadores(D, "_pal_sf", "_pal", "_pal")   # con T sin filtro
D["lluvia_dia"] = (D["prec_chirps"] >= LLUVIA_DIA_MM).astype(float).mask(D["prec_chirps"].isna())

# 4) Medias móviles y acumulados
MA_VARS = ["tmed_era5c", "tmin_era5c", "tmax_era5c", "hr_era5c", "hr90_horas_era5c", "dpv_era5c"]
for v in MA_VARS:
    for n in (3, 7):
        D[f"{v}_ma{n}r"] = D[v].rolling(n, min_periods=n).mean()                 # retrasada
        D[f"{v}_ma{n}c"] = D[v].rolling(n, min_periods=n, center=True).mean()    # centrada
for n in (3, 7):
    D[f"prec_chirps_acum{n}r"] = D["prec_chirps"].rolling(n, min_periods=n).sum()

# 5) Etiquetas de tiempo
D["anio"], D["mes"], D["periodo8"] = D.index.year, D.index.month, periodo8(D.index)
D["en_ventana"] = D["mes"].isin(VENTANA_MESES)
print(D.shape); D.loc["2019-01-01":"2019-01-10", ["tmed_era5c", "hr90_horas_era5c", "prec_chirps", "salb_fav", "clf_fav", "hr90_horas_pal"]]
""")

md(r"""
### Figura 5.1 – Climatología mensual del lote (2011–2025)
Promedio de cada mes en los 15 años. La franja gris es la ventana enero–abril: el paso de la época seca (ene–feb) a la lluviosa (abr).
""")

code(r"""
clim = D.groupby("mes").agg(tmed=("tmed_era5c", "mean"), tmax=("tmax_era5c", "mean"), tmin=("tmin_era5c", "mean"),
                            hr90=("hr90_horas_era5c", "mean"), hr90_pal=("hr90_horas_pal", "mean"),
                            dpv=("dpv_era5c", "mean"), salb=("salb_fav", "mean"), clf=("clf_fav", "mean"))
clim["lluvia"] = D.groupby(["anio", "mes"])["prec_chirps"].sum(min_count=25).groupby("mes").mean()
x = clim.index; et = [MESES[i] for i in x]
fig, axs = plt.subplots(2, 2, figsize=(11, 6.2), sharex=True)
for ax in axs.flat: ax.axvspan(0.5, 4.5, color="#f0f0f0", zorder=0)
a = axs[0, 0]; a.fill_between(x, clim.tmin, clim.tmax, color="#9cc3ee", alpha=0.5, label="T mín–máx")
a.plot(x, clim.tmed, color="#2a78d6", marker="o", ms=3, label="T media"); a.set_ylabel("°C"); a.set_title("Temperatura"); a.legend()
a = axs[0, 1]; a.bar(x, clim.lluvia, color="#1baf7a", width=0.7); a.set_ylabel("mm/mes"); a.set_title("Lluvia (CHIRPS)")
a = axs[1, 0]; a.plot(x, clim.hr90, color="#eb6834", marker="o", ms=3, label="ERA5-Land corregido")
a.plot(x, clim.hr90_pal, color="#2b2b2b", marker="o", ms=3, ls=":", label="La Palomera (obs.)")
a.set_ylabel("h/día"); a.set_title("Horas con HR ≥ 90 % (hoja mojada)"); a.legend()
a = axs[1, 1]; a.plot(x, 100 * clim.salb, color="#6250d6", marker="o", ms=3, label="SALB")
a.plot(x, 100 * clim.clf, color="#e34948", marker="o", ms=3, label="Antracnosis/CLF")
a.set_ylabel("% de días favorables"); a.set_title("Días favorables para infección"); a.legend()
for a in axs[1]: a.set_xticks(x); a.set_xticklabels(et)
fig.suptitle("Lote San Carlos – climatología 2011–2025", y=1.01)
guardar(fig, "5_1_climatologia_lote")
clim.round(2)
""")

md(r"""
### Figura 5.2 – Enero–abril de cada año, en periodos de 8 días
Cada línea es un año. Los años con datos de cultivo (2017–2020) van en color; los demás en gris para dar contexto.
""")

code(r"""
V = D[D.en_ventana]
p8 = V.groupby(["anio", "periodo8"]).agg(tmed=("tmed_era5c", "mean"), hr90=("hr90_horas_era5c", "mean"),
                                         dpv=("dpv_era5c", "mean"), lluvia=("prec_chirps", "sum"),
                                         salb=("salb_fav", "mean"), clf=("clf_fav", "mean")).reset_index()
P8 = p8[p8.periodo8 <= 15]                                  # 15 periodos completos de ene-abr
COL_ANIO = {2017: "#2a78d6", 2018: "#eb6834", 2019: "#1baf7a", 2020: "#6250d6"}
ini = pd.Timestamp("2001-01-01")
etq = [(ini + pd.Timedelta(days=(k - 1) * 8)).strftime("%d-%b") for k in range(1, 16)]
fig, axs = plt.subplots(2, 3, figsize=(14, 6.4), sharex=True)
for ax, (v, tit, u) in zip(axs.flat, [("tmed", "T media", "°C"), ("hr90", "Horas HR ≥ 90 %", "h/día"),
                                      ("dpv", "DPV", "kPa"), ("lluvia", "Lluvia (CHIRPS)", "mm / 8 días"),
                                      ("salb", "Días favorables SALB", "fracción"), ("clf", "Días favorables Antracnosis/CLF", "fracción")]):
    for a, g in P8.groupby("anio"):
        es = a in COL_ANIO
        ax.plot(g.periodo8, g[v], color=COL_ANIO.get(a, "#cfcfcf"), lw=2 if es else 0.9,
                zorder=3 if es else 1, label=str(a) if es else None)
    ax.plot(P8.groupby("periodo8")[v].mean(), color="#2b2b2b", ls="--", lw=1.4, label="media 2011–2025")
    ax.set_title(tit); ax.set_ylabel(u)
for ax in axs[1]: ax.set_xticks(range(1, 16, 2)); ax.set_xticklabels(etq[::2], rotation=45)
axs[0, 0].legend(fontsize=8, ncol=2)
fig.suptitle("Lote San Carlos: enero–abril por periodos de 8 días (años del cultivo en color)", y=1.01)
guardar(fig, "5_2_ene_abr_periodos_8dias")
""")

md(r"""
---
# 6. ¿La información cada 8 días presenta cambios?

El cultivo se evaluó aproximadamente cada 8 días. Antes de relacionar clima y enfermedad hay que saber si el clima **cambia de verdad** entre un periodo de 8 días y el siguiente, o si las diferencias son solo ruido día a día. Tres pruebas complementarias, solo para enero–abril de 2011–2025:

1. **Kruskal–Wallis entre periodos.** ¿Los 15 periodos de 8 días tienen distribuciones distintas (juntando los 15 años)? Es una prueba no paramétrica (no supone normalidad). *p* < 0.05 → hay una progresión estacional real a escala de 8 días.

2. **Proporción de varianza entre periodos (η²).** De toda la variación diaria dentro de un año, ¿qué fracción se explica por el periodo de 8 días al que pertenece el día? Se calcula con un ANOVA de una vía por año y se promedia. η² cercano a 0 → el periodo no dice nada; η² > 0.14 se considera un efecto grande.

3. **Cambios entre periodos consecutivos.** Para cada año y cada par de periodos consecutivos (p. ej. 1–8 ene vs. 9–16 ene) se aplica la prueba U de Mann–Whitney a los 8 valores diarios. Se reporta el % de transiciones con cambio significativo (*p* < 0.05). Si el clima no cambiara, se esperaría ~5 % por azar.

Además, la **autocorrelación de un periodo al siguiente** (r lag-1) indica si un periodo húmedo tiende a seguir a otro húmedo (persistencia).
""")

code(r"""
VARS_8 = {"tmed_era5c": "T media", "tmin_era5c": "T mínima", "hr90_horas_era5c": "Horas HR≥90 %",
          "dpv_era5c": "DPV", "prec_chirps": "Lluvia (CHIRPS)", "hr90_horas_pal": "Horas HR≥90 % (La Palomera)"}
W = D[D.en_ventana & (D.periodo8 <= 15)]

def eta2(y, grupos):
    # Fracción de la varianza total explicada por los grupos (ANOVA de una vía)
    df = pd.DataFrame({"y": y, "g": grupos}).dropna()
    if df.g.nunique() < 3: return np.nan
    tot = ((df.y - df.y.mean()) ** 2).sum()
    entre = df.groupby("g").y.apply(lambda s: len(s) * (s.mean() - df.y.mean()) ** 2).sum()
    return entre / tot if tot > 0 else np.nan

filas = []
for v, nom in VARS_8.items():
    grupos = [g[v].dropna().values for _, g in W.groupby("periodo8") if g[v].notna().sum() > 5]
    H, pkw = stats.kruskal(*grupos) if len(grupos) > 2 else (np.nan, np.nan)
    e2 = np.nanmean([eta2(g[v], g["periodo8"]) for _, g in W.groupby("anio")])
    cambios, n_tr, ac = 0, 0, []
    for a, g in W.groupby("anio"):
        bloques = [b[v].dropna().values for _, b in g.groupby("periodo8")]
        medias = [b.mean() if len(b) >= 6 else np.nan for b in bloques]
        for b1, b2 in zip(bloques[:-1], bloques[1:]):
            if len(b1) >= 6 and len(b2) >= 6 and np.ptp(np.r_[b1, b2]) > 0:
                n_tr += 1; cambios += stats.mannwhitneyu(b1, b2).pvalue < 0.05
        s = pd.Series(medias).dropna()
        if len(s) > 5: ac.append(s.autocorr(1))
    filas.append(dict(variable=nom, kruskal_H=H, kruskal_p=pkw, eta2_medio=e2,
                      transiciones=n_tr, pct_cambios_signif=100 * cambios / max(n_tr, 1),
                      autocorr_lag1_8dias=np.nanmean(ac)))
CAMBIOS_8D = pd.DataFrame(filas).round(4)
CAMBIOS_8D
""")

md(r"""
### Figura 6.1 – Distribución por periodo de 8 días (enero–abril, 2011–2025)
Cada caja resume los 15 años de un periodo: la línea central es la mediana y la caja contiene el 50 % central de los valores. Si las cajas suben o bajan de forma ordenada, hay un cambio sistemático a escala de 8 días.
""")

code(r"""
fig, axs = plt.subplots(1, 4, figsize=(15, 3.6), sharex=True)
for ax, (v, u) in zip(axs, [("tmed_era5c", "°C"), ("hr90_horas_era5c", "h/día"), ("dpv_era5c", "kPa"), ("prec_chirps", "mm/día")]):
    datos = [g[v].dropna().values for _, g in W.groupby("periodo8")]
    ax.boxplot(datos, widths=0.6, showfliers=False, patch_artist=True,
               boxprops=dict(facecolor="#d6e6f8", edgecolor="#2a78d6"), medianprops=dict(color="#0d3f80", lw=1.6),
               whiskerprops=dict(color="#2a78d6"), capprops=dict(color="#2a78d6"))
    fila = CAMBIOS_8D[CAMBIOS_8D.variable == VARS_8[v]].iloc[0]
    ax.set_title(f"{VARS_8[v]}\nKruskal p = {fila.kruskal_p:.1e} · η² = {fila.eta2_medio:.2f}", fontsize=9.5)
    ax.set_ylabel(u); ax.set_xticks(range(1, 16, 2)); ax.set_xticklabels(etq[::2], rotation=45)
fig.suptitle("¿Cambia el clima cada 8 días? Enero–abril, lote San Carlos", y=1.05)
guardar(fig, "6_1_boxplot_periodos_8dias")
""")

md(r"""
---
# 7. Datos del cultivo (San Carlos, 2016–2020)

## 7.1 Lectura y limpieza
Hojas del archivo `Fenologia_base Orinoquia.xlsx`:

| Hoja | Unidad de muestreo | Variables |
|---|---|---|
| FENOLOGIA | árbol (8 rep. × 4 árboles × 3 clones = 96 árboles) | densidad foliar (0–10), estados de hoja A, B, C, D1–D5 (%), floración, frutos, **Antracnosis (0–4)**, **Mal Suramericano (0–4)**, Costra negra, Mancha areolada, Punteros |
| NECROMASA | trampa de hojarasca | peso de hojas y flores caídas (g) |
| IMAGENES | foto hemisférica del dosel | % porosidad, % cobertura, LAI4, LAI5 |

**Estados de la hoja de caucho** (Hallé et al. 1978): **A** yema que brota → **B** hoja joven color bronce (colgante) → **C** hoja verde claro en expansión → **D** hoja madura (endurecida). Las hojas B y C son las **susceptibles** a SALB y Antracnosis. D1…D5 son hojas maduras de cada ciclo anual sucesivo, así que aquí se suman como `D`.

**Correcciones de nombres** (se informan abajo):
- Clones escritos de varias formas (`FX3864`, `RRIM`, `RRIM600`) → nombre único.
- `FX 3865` aparece solo el 03-oct-2017, justo la fecha que le falta a FX 3864 → se trata como error de digitación de **FX 3864**.
""")

code(r"""
def limpiar_clon(s):
    s = str(s).upper().replace(" ", "")
    if s.startswith("FX386"): return "FX 3864"        # incluye el error FX 3865
    if s.startswith("IAN"):   return "IAN 873"
    if s.startswith("RRIM"):  return "RRIM 600"
    return s

def leer_hoja(nombre):
    x = pd.read_excel(ARCHIVO_CULTIVO, sheet_name=nombre)
    x.columns = [str(c).strip() for c in x.columns]
    x["Fecha"] = pd.to_datetime(x["Fecha"], errors="coerce").dt.normalize()
    x["Clon_original"] = x["Clon"]
    x["Clon"] = x["Clon"].map(limpiar_clon)
    return x

fen = leer_hoja("FENOLOGIA")
print("Clones (original → limpio):"); print(fen.groupby(["Clon_original", "Clon"]).size())
# Nombres cortos de columnas
fen = fen.rename(columns={"Densidad Total": "dens_foliar", "Densidad Floral (0-10)": "dens_floral",
                          "Antracnosis": "antrac", "Mal Suramericano": "salb", "Costra negra": "costra",
                          "Mancha aerolada": "mancha", "Punteros (0-1)": "punteros"})
fen = fen.rename(columns={c: "dens_floral" for c in fen.columns if c.lower().startswith("densidad floral")})
num = ["dens_foliar", "D1", "A", "B", "C", "D2", "D3", "D4", "D5", "antrac", "salb", "costra", "mancha", "punteros"]
for c in num: fen[c] = pd.to_numeric(fen[c], errors="coerce")
fen["D"] = fen[["D1", "D2", "D3", "D4", "D5"]].sum(axis=1, min_count=1)      # hojas maduras
fen["joven"] = fen[["A", "B", "C"]].sum(axis=1, min_count=1)                # % hojas jóvenes
fen["susceptible"] = fen[["B", "C"]].sum(axis=1, min_count=1)               # % hojas B + C
fen["Arbol"] = fen["Arbol"].astype(str).str.strip()
fen["id_arbol"] = fen["Clon"] + "_" + fen["Arbol"]                            # identificador único de árbol
fen["rep"] = fen["Arbol"].str.extract(r"R(\d+)")[0].astype(float)
print(fen[["Fecha"]].agg(["min", "max"]).T, "\nÁrboles:", fen.id_arbol.nunique(), "| Fechas:", fen.Fecha.nunique())
print("Enfermedades registradas desde:", fen.loc[fen.antrac.notna(), "Fecha"].min().date())
""")

md(r"""
## 7.2 Incidencia y severidad por fecha y clon

Para cada fecha de evaluación y clon (32 árboles):
- **Incidencia (%)** = árboles con nota ≥ 1 / árboles evaluados × 100. Responde *¿cuántos árboles están enfermos?*
- **Severidad media** = promedio de la nota (escala 0–4).
- **Índice de severidad (ISE, %)** de McKinney (1923): `ISE = Σ(nota × nº de árboles con esa nota) / (nº de árboles × nota máxima) × 100`. Combina incidencia y severidad en un solo número de 0 a 100.

Para Costra negra, Mancha areolada y Punteros (presencia/ausencia) solo se calcula la incidencia.
""")

code(r"""
def resumen_fecha(df):
    # Resume los árboles de un clon en una fecha
    r = {"n_arboles": df["antrac"].notna().sum() if df["antrac"].notna().any() else len(df)}
    for v, nmax in [("antrac", 4), ("salb", 4)]:
        s = df[v].dropna()
        r[f"{v}_inc"] = 100 * (s >= 1).mean() if len(s) else np.nan
        r[f"{v}_sev"] = s.mean() if len(s) else np.nan
        r[f"{v}_ise"] = 100 * s.sum() / (len(s) * nmax) if len(s) else np.nan
    for v in ["costra", "mancha", "punteros"]:
        s = df[v].dropna(); r[f"{v}_inc"] = 100 * (s > 0).mean() if len(s) else np.nan
    for v in ["dens_foliar", "joven", "susceptible", "A", "B", "C", "D", "dens_floral"]:
        r[v] = df[v].mean() if v in df else np.nan
    return pd.Series(r)

CULT = fen.groupby(["Clon", "Fecha"]).apply(resumen_fecha).reset_index()
CULT["anio"], CULT["mes"] = CULT.Fecha.dt.year, CULT.Fecha.dt.month
CULT["en_ventana"] = CULT.mes.isin(VENTANA_MESES)
# Intervalo entre evaluaciones (días)
CULT["dias_desde_anterior"] = CULT.groupby("Clon").Fecha.diff().dt.days
# Nuevas infecciones: aumento de la incidencia respecto a la evaluación anterior
for v in ["antrac_inc", "salb_inc", "antrac_ise"]:
    CULT[f"delta_{v}"] = CULT.groupby("Clon")[v].diff()
print("Intervalo entre evaluaciones en ene–abr (días):", CULT.loc[CULT.en_ventana, "dias_desde_anterior"].describe().round(1).to_dict())
CULT.head()
""")

md(r"""
### Figura 7.1 – Serie de tiempo del cultivo por clon
Franjas grises = enero–abril. Se ve el ciclo anual: caída de hojas (densidad baja) → brotación de hojas jóvenes → aparición de Antracnosis y SALB sobre las hojas nuevas.
""")

code(r"""
paneles = [("dens_foliar", "Densidad foliar (0–10)"), ("joven", "Hojas jóvenes A+B+C (%)"),
           ("antrac_inc", "Incidencia Antracnosis (%)"), ("antrac_ise", "Índice de severidad Antracnosis (%)"),
           ("salb_inc", "Incidencia SALB (%)"), ("punteros_inc", "Incidencia Punteros (%)")]
fig, axs = plt.subplots(len(paneles), 1, figsize=(12, 13), sharex=True)
for ax, (v, tit) in zip(axs, paneles):
    for a in range(2017, 2021):
        ax.axvspan(pd.Timestamp(f"{a}-01-01"), pd.Timestamp(f"{a}-04-30"), color="#f0f0f0", zorder=0)
    for clon, g in CULT.groupby("Clon"):
        ax.plot(g.Fecha, g[v], color=COL_CLON[clon], marker="o", ms=2.5, lw=1.3, label=clon)
    ax.set_ylabel(tit, fontsize=8.5)
axs[0].legend(ncol=3, loc="lower left")
axs[-1].xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
axs[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b-%Y")); plt.setp(axs[-1].get_xticklabels(), rotation=45)
fig.suptitle("Lote San Carlos: fenología y enfermedades foliares por clon (2016–2020)", y=1.0)
fig.tight_layout(); guardar(fig, "7_1_serie_cultivo_clones")
""")

md(r"""
## 7.3 Área bajo la curva de progreso de la enfermedad (ABCPE) por temporada enero–abril

El **ABCPE** (en inglés AUDPC) resume en un solo número cuánta enfermedad hubo durante una temporada, integrando la incidencia en el tiempo con la regla del trapecio:

`ABCPE = Σ [(y_i + y_{i+1}) / 2] × (t_{i+1} − t_i)`

Se calcula **por árbol** (nota de severidad 0–4) y por temporada enero–abril. Luego se compara entre clones con la prueba de **Kruskal–Wallis** (no paramétrica) y, por pares, con **Mann–Whitney** corregido por Holm.
""")

code(r"""
def abcpe(fechas, y):
    s = pd.Series(np.asarray(y, float), index=pd.to_datetime(fechas)).dropna().sort_index()
    if len(s) < 3: return np.nan
    t = (s.index - s.index[0]).days.values
    return float(np.trapezoid(s.values, t) if hasattr(np, "trapezoid") else np.trapz(s.values, t))

fv = fen[fen.Fecha.dt.month.isin(VENTANA_MESES) & fen.antrac.notna()]
ARB = (fv.groupby(["Clon", "id_arbol", fv.Fecha.dt.year.rename("anio")])
         .apply(lambda g: pd.Series({"abcpe_antrac": abcpe(g.Fecha, g.antrac), "abcpe_salb": abcpe(g.Fecha, g.salb),
                                     "max_antrac": g.antrac.max(), "max_salb": g.salb.max(),
                                     "n_eval": g.Fecha.nunique()})).reset_index())
print("Evaluaciones por temporada ene–abr:"); print(ARB.groupby("anio").n_eval.median())
pruebas = []
for v in ["abcpe_antrac", "abcpe_salb"]:
    for a, g in ARB.groupby("anio"):
        grupos = [x[v].dropna().values for _, x in g.groupby("Clon")]
        if all(len(x) > 3 for x in grupos) and np.ptp(np.concatenate(grupos)) > 0:
            H, p = stats.kruskal(*grupos)
            pruebas.append(dict(variable=v, anio=a, H=H, p=p, **{f"mediana_{c}": x[v].median() for c, x in g.groupby("Clon")}))
KW_CLONES = pd.DataFrame(pruebas).round(4)
KW_CLONES
""")

code(r"""
fig, axs = plt.subplots(1, 2, figsize=(12, 3.8))
for ax, (v, tit) in zip(axs, [("abcpe_antrac", "Antracnosis"), ("abcpe_salb", "Mal Suramericano (SALB)")]):
    anios = sorted(ARB.anio.unique()); clones = list(COL_CLON)
    for j, c in enumerate(clones):
        datos = [ARB[(ARB.anio == a) & (ARB.Clon == c)][v].dropna().values for a in anios]
        pos = np.arange(len(anios)) + (j - 1) * 0.27
        bp = ax.boxplot(datos, positions=pos, widths=0.22, showfliers=False, patch_artist=True)
        for e in ("boxes",): [b.set(facecolor=COL_CLON[c], alpha=0.75, edgecolor=COL_CLON[c]) for b in bp[e]]
        for e in ("whiskers", "caps"): [b.set(color=COL_CLON[c]) for b in bp[e]]
        [m.set(color="#222") for m in bp["medians"]]
        ax.plot([], [], color=COL_CLON[c], lw=6, label=c)
    ax.set_xticks(range(len(anios))); ax.set_xticklabels(anios); ax.set_title(f"ABCPE {tit}, enero–abril")
    ax.set_ylabel("nota × días")
axs[0].legend()
guardar(fig, "7_2_abcpe_clones")
""")

md(r"""
## 7.4 Necromasa (caída de hojas) e índice de área foliar (LAI)
- **Tasa de caída de hojas** (g/trampa/día) = peso de hojas recogido / días desde la recolección anterior. Divide por los días porque las trampas no siempre se vaciaron con el mismo intervalo.
- **LAI4**: índice de área foliar efectivo (m² de hoja por m² de suelo), calculado de fotos hemisféricas en ángulos cenitales 0–60°. **% cobertura** = 100 − % porosidad.
""")

code(r"""
nec = leer_hoja("NECROMASA")
nec = nec.rename(columns={c: "peso_hojas" for c in nec.columns if "hojas" in c.lower()})
nec = nec.rename(columns={c: "peso_flores" for c in nec.columns if "flores" in c.lower()})
for c in ("peso_hojas", "peso_flores"): nec[c] = pd.to_numeric(nec[c], errors="coerce")
NEC = nec.groupby(["Clon", "Fecha"]).agg(peso_hojas=("peso_hojas", "mean"), peso_flores=("peso_flores", "mean"),
                                         n_trampas=("peso_hojas", "count")).reset_index()
NEC["dias"] = NEC.groupby("Clon").Fecha.diff().dt.days
NEC["caida_hojas_g_dia"] = NEC.peso_hojas / NEC.dias                         # g/trampa/día

img = leer_hoja("IMAGENES")
for c in ["% Porosidad", "LAI4", "LAI5", "% Cobertura"]: img[c] = pd.to_numeric(img[c], errors="coerce")
LAI = img.groupby(["Clon", "Fecha"]).agg(LAI4=("LAI4", "mean"), LAI5=("LAI5", "mean"),
                                         cobertura=("% Cobertura", "mean")).reset_index()
print("Necromasa:", NEC.Fecha.min().date(), "→", NEC.Fecha.max().date(), "| LAI:", LAI.Fecha.min().date(), "→", LAI.Fecha.max().date())

fig, axs = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
for ax, (df, v, tit) in zip(axs, [(NEC, "caida_hojas_g_dia", "Caída de hojas (g/trampa/día)"), (LAI, "LAI4", "LAI4 (m²/m²)")]):
    for a in range(2017, 2021): ax.axvspan(pd.Timestamp(f"{a}-01-01"), pd.Timestamp(f"{a}-04-30"), color="#f0f0f0", zorder=0)
    for c, g in df.groupby("Clon"): ax.plot(g.Fecha, g[v], color=COL_CLON[c], marker="o", ms=2.5, lw=1.3, label=c)
    ax.set_ylabel(tit)
axs[0].legend(ncol=3); fig.suptitle("Necromasa y dosel por clon", y=1.0); fig.tight_layout()
guardar(fig, "7_3_necromasa_lai")
""")

md(r"""
---
# 8. Relación entre el clima y las enfermedades

## 8.1 Ventanas de clima previas a cada evaluación ("ventana deslizante")
La enfermedad que se ve hoy es el resultado del clima de días o semanas antes (tiempo de infección + periodo de incubación de ~5–15 días para SALB y Antracnosis). Por eso, para cada fecha de evaluación se resume el clima en **ventanas hacia atrás** de 8 días, igual que la frecuencia de muestreo:

| Ventana | Días antes de la evaluación |
|---|---|
| `v0-8` | 1 a 8 |
| `v8-16` | 9 a 16 |
| `v16-24` | 17 a 24 |
| `v24-32` | 25 a 32 |
| `v0-16`, `v0-32` | acumulados de 1 a 16 y de 1 a 32 |

En cada ventana se calcula: T media, T mínima, horas HR ≥ 90 %, DPV, lluvia total, nº de días lluviosos, y la fracción de días favorables para SALB y para Antracnosis.

Se calculan con dos fuentes: el lote con ERA5-Land corregido + CHIRPS (principal) y La Palomera observada (sensibilidad).
""")

code(r"""
VENTANAS = {"v0-8": (1, 8), "v8-16": (9, 16), "v16-24": (17, 24), "v24-32": (25, 32), "v0-16": (1, 16), "v0-32": (1, 32)}
CLIMA_VARS = {  # nombre: (columna, función de agregación)
    "T media": ("tmed_era5c", "mean"), "T mínima": ("tmin_era5c", "mean"), "Horas HR≥90 %": ("hr90_horas_era5c", "mean"),
    "DPV": ("dpv_era5c", "mean"), "Lluvia": ("prec_chirps", "sum"), "Días lluviosos": ("lluvia_dia", "sum"),
    "Días fav. SALB": ("salb_fav", "mean"), "Días fav. Antracnosis": ("clf_fav", "mean"),
    "Horas HR≥90 % (Palomera)": ("hr90_horas_pal", "mean"), "Lluvia (Palomera)": ("prec_pal", "sum"),
    "Días fav. SALB (Palomera)": ("salb_fav_pal", "mean"), "Días fav. Antracnosis (Palomera)": ("clf_fav_pal", "mean"),
    "T media (Palomera)": ("tmed_pal", "mean"), "T media (Palomera sin filtro)": ("tmed_pal_sf", "mean"),
    "Días fav. SALB (Palomera sin filtro)": ("salb_fav_pal_sf", "mean"),
    "Días fav. Antracnosis (Palomera sin filtro)": ("clf_fav_pal_sf", "mean"),
}

def clima_previo(fecha):
    # Resume el clima en cada ventana de días previos a 'fecha'
    out = {}
    for vn, (a, b) in VENTANAS.items():
        tramo = D.loc[fecha - pd.Timedelta(days=b): fecha - pd.Timedelta(days=a)]
        for nom, (col, f) in CLIMA_VARS.items():
            s = tramo[col]
            ok = s.notna().mean() >= 0.8                                   # exige 80 % de días con dato
            out[f"{nom} | {vn}"] = (s.sum() if f == "sum" else s.mean()) if ok else np.nan
    return pd.Series(out)

fechas_eval = pd.Series(sorted(CULT.Fecha.unique()))
CLIMA_EVAL = fechas_eval.apply(clima_previo); CLIMA_EVAL.index = fechas_eval.values; CLIMA_EVAL.index.name = "Fecha"
REL = CULT.merge(CLIMA_EVAL, left_on="Fecha", right_index=True, how="left")
print(REL.shape)
""")

md(r"""
## 8.2 Correlaciones de Spearman (enero–abril, 2018–2020)

Se usa la correlación de **Spearman (ρ)** porque la incidencia no sigue una distribución normal y la relación puede no ser lineal.

Respuestas:
- **Incidencia de Antracnosis** e **incidencia de SALB** en la fecha.
- **Δ incidencia** (cambio desde la evaluación anterior): aproxima las **nuevas** infecciones y suele responder mejor al clima reciente que el nivel acumulado.

**Precauciones estadísticas:**
1. Se prueban muchas combinaciones (variables × ventanas), así que algunas saldrán "significativas" por azar. Se corrige con **Benjamini–Hochberg (FDR)** y se reporta `p_FDR`.
2. Las evaluaciones consecutivas no son independientes (autocorrelación temporal) y los 3 clones comparten el mismo clima. Por eso se calcula con el **promedio de los 3 clones por fecha** (n = nº de fechas), lo que evita inflar el tamaño de muestra. Las correlaciones por clon se dan como complemento.
3. Con 3 temporadas con datos de enfermedad (2018–2020; en 2017 las notas empiezan el 27 de marzo) los resultados son **exploratorios**: indican qué ventana y variable vale la pena modelar o validar en campo.
""")

code(r"""
RESP = {"antrac_inc": "Incidencia Antracnosis", "delta_antrac_inc": "Δ incidencia Antracnosis",
        "salb_inc": "Incidencia SALB", "delta_salb_inc": "Δ incidencia SALB"}
clim_cols = [c for c in REL.columns if " | v" in c]
Rv = REL[REL.en_ventana & REL.antrac_inc.notna()]
Rm = Rv.groupby("Fecha")[list(RESP) + ["joven", "susceptible"] + clim_cols].mean()   # promedio de clones por fecha

def fdr(p):
    # Benjamini-Hochberg sobre los p válidos (los NaN se dejan como NaN)
    p = pd.Series(p, dtype=float); out = pd.Series(np.nan, index=p.index); ok = p.notna()
    if ok.any(): out[ok] = multipletests(p[ok], method="fdr_bh")[1]
    return out.values

filas = []
for r, rnom in RESP.items():
    for c in clim_cols:
        m = Rm[[r, c]].dropna()
        if len(m) >= 10 and m[c].nunique() > 2:
            rho, p = stats.spearmanr(m[r], m[c])
            var, vent = c.split(" | ")
            filas.append(dict(respuesta=rnom, variable=var, ventana=vent, n=len(m), rho=rho, p=p))
CORR = pd.DataFrame(filas)
CORR["p_FDR"] = fdr(CORR.p)
CORR = CORR.round(4)
print("Fechas de evaluación en ene–abr con enfermedad:", len(Rm))
CORR.sort_values("p").head(20)
""")

md(r"""
### Figura 8.1 – Mapa de correlaciones clima × ventana
Cada celda es ρ de Spearman entre la respuesta y la variable de clima en la ventana indicada. Azul = relación negativa; rojo = positiva; gris claro = sin relación. `*` p < 0.05, `**` p_FDR < 0.05.
""")

code(r"""
orden_v = list(VENTANAS); vars_ppal = [k for k in CLIMA_VARS if "Palomera" not in k]
fig, axs = plt.subplots(1, 4, figsize=(17, 4.6), sharey=True)
for ax, rnom in zip(axs, RESP.values()):
    t = CORR[(CORR.respuesta == rnom) & CORR.variable.isin(vars_ppal)]
    M = t.pivot(index="variable", columns="ventana", values="rho").reindex(index=vars_ppal, columns=orden_v)
    P = t.pivot(index="variable", columns="ventana", values="p").reindex(index=vars_ppal, columns=orden_v)
    Q = t.pivot(index="variable", columns="ventana", values="p_FDR").reindex(index=vars_ppal, columns=orden_v)
    im = ax.imshow(M.values, cmap="RdBu_r", vmin=-0.8, vmax=0.8, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            if pd.notna(M.iat[i, j]):
                s = "**" if Q.iat[i, j] < 0.05 else ("*" if P.iat[i, j] < 0.05 else "")
                ax.text(j, i, f"{M.iat[i, j]:.2f}{s}", ha="center", va="center", fontsize=7.5,
                        color="white" if abs(M.iat[i, j]) > 0.55 else "#222")
    ax.set_xticks(range(len(orden_v))); ax.set_xticklabels(orden_v, rotation=45); ax.set_title(rnom, fontsize=9.5); ax.grid(False)
axs[0].set_yticks(range(len(vars_ppal))); axs[0].set_yticklabels(vars_ppal)
fig.colorbar(im, ax=axs, label="ρ de Spearman", shrink=0.8)
fig.suptitle("Clima previo (lote: ERA5-Land corregido + CHIRPS) vs. enfermedad, enero–abril 2018–2020", y=1.02)
guardar(fig, "8_1_mapa_correlaciones")
""")

md(r"""
### 8.3 Sensibilidad: ¿cambia el resultado según la fuente o el filtro del sensor?
Dos comparaciones, con las mismas respuestas y ventanas:
1. **Lote (ERA5-Land corregido + CHIRPS) vs. La Palomera observada.**
2. **La Palomera con filtro vs. sin filtro del sensor de T.** Muestra si el problema del sensor cambia la inferencia en los años del cultivo.

Si los ρ coinciden en signo y magnitud (|Δρ| pequeño), el resultado es robusto.
""")

code(r"""
pares_sens = [  # (comparación, variable A, variable B)
    ("Lote vs. Palomera", "Horas HR≥90 %", "Horas HR≥90 % (Palomera)"),
    ("Lote vs. Palomera", "Lluvia", "Lluvia (Palomera)"),
    ("Lote vs. Palomera", "Días fav. SALB", "Días fav. SALB (Palomera)"),
    ("Lote vs. Palomera", "Días fav. Antracnosis", "Días fav. Antracnosis (Palomera)"),
    ("Palomera con vs. sin filtro de T", "T media (Palomera)", "T media (Palomera sin filtro)"),
    ("Palomera con vs. sin filtro de T", "Días fav. SALB (Palomera)", "Días fav. SALB (Palomera sin filtro)"),
    ("Palomera con vs. sin filtro de T", "Días fav. Antracnosis (Palomera)", "Días fav. Antracnosis (Palomera sin filtro)"),
]
filas = []
for comp, a, b in pares_sens:
    x = CORR[CORR.variable == a].set_index(["respuesta", "ventana"])[["rho", "p", "n"]]
    y = CORR[CORR.variable == b].set_index(["respuesta", "ventana"])[["rho", "p", "n"]]
    j = x.join(y, lsuffix="_A", rsuffix="_B").dropna().reset_index()
    j.insert(0, "variable_B", b); j.insert(0, "variable_A", a); j.insert(0, "comparacion", comp)
    filas.append(j)
SENS = pd.concat(filas).round(3)
for comp, g in SENS.groupby("comparacion"):
    print(f"{comp}: acuerdo de signo {100 * (np.sign(g.rho_A) == np.sign(g.rho_B)).mean():.0f} % | "
          f"r entre los ρ = {g.rho_A.corr(g.rho_B):.2f} | máx |Δρ| = {(g.rho_A - g.rho_B).abs().max():.2f}")
SENS.head(12)
""")

md(r"""
## 8.4 Modelo a nivel de árbol: Ecuaciones de Estimación Generalizadas (GEE)

Las correlaciones no separan el efecto del clima del efecto del clon ni de la fenología (hay más enfermedad simplemente porque hay más hojas jóvenes). Un modelo los considera a la vez:

`logit P(árbol con Antracnosis) = β0 + β_clon + β1·(% hojas jóvenes del árbol) + β2·clima₁ + β3·clima₂`

- **Unidad**: cada árbol en cada fecha (enero–abril, 2018–2020).
- **GEE binomial con correlación intercambiable por árbol**: tiene en cuenta que el mismo árbol se mide muchas veces (sus observaciones no son independientes) y da errores estándar robustos.
- Las variables de clima se **estandarizan** (media 0, desviación 1), así que cada **OR** (razón de odds, `exp(β)`) se lee como: *cuánto se multiplican las probabilidades de que el árbol esté enfermo cuando la variable sube una desviación estándar*. OR > 1 aumenta el riesgo, OR < 1 lo reduce.
- Se eligen automáticamente las dos variables climáticas con mayor |ρ| para la respuesta (una de humedad/lluvia y una de temperatura/DPV), evitando meter variables muy correlacionadas entre sí.
- También se ajusta el modelo para SALB si hay suficientes árboles enfermos.
""")

code(r"""
def elegir_clima(resp_nombre):
    # Mejor variable de humedad/lluvia y mejor de temperatura/DPV (fuente principal), por |ρ|
    t = CORR[(CORR.respuesta == resp_nombre) & ~CORR.variable.str.contains("Palomera")].copy()
    t["abs"] = t.rho.abs()
    hum = t[t.variable.isin(["Horas HR≥90 %", "Lluvia", "Días lluviosos", "Días fav. SALB", "Días fav. Antracnosis"])]
    tem = t[t.variable.isin(["T media", "T mínima", "DPV"])]
    sel = [hum.sort_values("abs").iloc[-1], tem.sort_values("abs").iloc[-1]]
    return [f"{s.variable} | {s.ventana}" for s in sel]

def ajustar_gee(enf, resp_nombre):
    vars_c = elegir_clima(resp_nombre)
    arb = fen[fen.Fecha.dt.month.isin(VENTANA_MESES) & fen[enf].notna()].copy()
    arb["y"] = (arb[enf] >= 1).astype(int)
    arb = arb.merge(CLIMA_EVAL[vars_c], left_on="Fecha", right_index=True, how="left")
    nombres = {c: f"clima{i + 1}" for i, c in enumerate(vars_c)}
    arb = arb.rename(columns=nombres)
    for c in list(nombres.values()) + ["joven"]:
        arb[c + "_z"] = (arb[c] - arb[c].mean()) / arb[c].std()          # estandarización
    arb = arb.dropna(subset=["y", "joven_z", "clima1_z", "clima2_z"]).sort_values(["id_arbol", "Fecha"])
    arb = arb[["y", "Clon", "id_arbol", "Fecha", "joven_z", "clima1_z", "clima2_z"]]   # solo columnas del modelo
    if arb.y.sum() < 30:
        print(f"{enf}: muy pocos casos positivos ({arb.y.sum()}); no se ajusta el modelo."); return None
    mod = smf.gee("y ~ C(Clon) + joven_z + clima1_z + clima2_z", groups="id_arbol", data=arb,
                  family=sm.families.Binomial(), cov_struct=sm.cov_struct.Exchangeable()).fit()
    ic = mod.conf_int()
    tabla = pd.DataFrame({"OR": np.exp(mod.params), "IC95_inf": np.exp(ic[0]), "IC95_sup": np.exp(ic[1]), "p": mod.pvalues})
    tabla = tabla.rename(index={"clima1_z": vars_c[0] + " (z)", "clima2_z": vars_c[1] + " (z)", "joven_z": "% hojas jóvenes (z)"})
    tabla.insert(0, "enfermedad", enf)
    print(f"\n=== {enf}: n = {len(arb)} obs., {arb.id_arbol.nunique()} árboles, {arb.y.mean() * 100:.1f} % positivos ===")
    return tabla.round(4)

GEE = pd.concat([t for t in [ajustar_gee("antrac", "Incidencia Antracnosis"), ajustar_gee("salb", "Incidencia SALB")] if t is not None])
GEE
""")

md(r"""
### Figura 8.2 – Razones de odds (OR) del modelo GEE
Punto = OR; línea = intervalo de confianza del 95 %. Si la línea cruza el 1 (línea vertical), el efecto no es significativo.
""")

code(r"""
t = GEE[~GEE.index.str.contains("Intercept")].copy(); t["etiqueta"] = t.enfermedad.map({"antrac": "Antracnosis", "salb": "SALB"}) + ": " + t.index
t = t.iloc[::-1]
fig, ax = plt.subplots(figsize=(8, 0.42 * len(t) + 1))
y = np.arange(len(t))
ax.hlines(y, t.IC95_inf, t.IC95_sup, color="#2a78d6", lw=2)
ax.plot(t.OR, y, "o", color="#2a78d6", ms=7, mec="white", mew=1.5)
ax.axvline(1, color="#777", ls="--", lw=1); ax.set_xscale("log")
ax.set_yticks(y); ax.set_yticklabels(t.etiqueta, fontsize=8.5); ax.set_xlabel("Razón de odds (escala log)")
ax.set_title("Modelo GEE: factores asociados a árboles enfermos (enero–abril)")
guardar(fig, "8_2_gee_odds_ratios")
""")

md(r"""
---
# 9. Clima, caída de hojas y dosel

La defoliación invernal (*wintering*) del caucho ocurre en la época seca y su intensidad depende del déficit hídrico. Una defoliación corta y concentrada produce una refoliación sincronizada, que puede "escapar" a la enfermedad si coincide con días secos. Aquí se explora:
- **Caída de hojas** (g/trampa/día) frente al DPV, la lluvia y la T de las ventanas previas.
- **LAI4** frente al clima.

Mismo procedimiento que en 8.2: promedio de los clones por fecha, Spearman y FDR. Aquí se usa **todo el año** (la defoliación empieza en diciembre).
""")

code(r"""
def corr_fecha(df, resp):
    m = df.merge(CLIMA_EVAL.reindex(columns=clim_cols).reset_index(), on="Fecha", how="left") \
          if not set(clim_cols) <= set(df.columns) else df
    m = m.groupby("Fecha")[[resp] + clim_cols].mean()
    fil = []
    for c in clim_cols:
        if "Palomera" in c: continue
        x = m[[resp, c]].dropna()
        if len(x) >= 10:
            rho, p = stats.spearmanr(x[resp], x[c]); var, vent = c.split(" | ")
            fil.append(dict(respuesta=resp, variable=var, ventana=vent, n=len(x), rho=rho, p=p))
    t = pd.DataFrame(fil); t["p_FDR"] = fdr(t.p)
    return t.round(4)

# CLIMA_EVAL solo tiene las fechas de FENOLOGIA; se calcula también para las de NECROMASA e IMAGENES
extra = sorted(set(NEC.Fecha) | set(LAI.Fecha) - set(CLIMA_EVAL.index))
if extra:
    ce = pd.Series(extra).apply(clima_previo); ce.index = extra
    CLIMA_EVAL = pd.concat([CLIMA_EVAL, ce]); CLIMA_EVAL = CLIMA_EVAL[~CLIMA_EVAL.index.duplicated()].sort_index()
    CLIMA_EVAL.index.name = "Fecha"
CORR_DOSEL = pd.concat([corr_fecha(NEC.dropna(subset=["caida_hojas_g_dia"]), "caida_hojas_g_dia"), corr_fecha(LAI, "LAI4")])
CORR_DOSEL.sort_values("p").head(12)
""")

md(r"""
### Figura 9.1 – Ciclo medio anual: clima, caída de hojas, hojas jóvenes y enfermedad
Todas las variables por mes (promedio de años y clones), cada una en su propio panel con su escala. Permite ver la secuencia: seca → caída de hojas → brotación → enfermedad.
""")

code(r"""
mens = lambda df, v: df.groupby(df.Fecha.dt.month)[v].mean()
paneles = [("Lluvia (mm/mes, CHIRPS)", clim["lluvia"], "#1baf7a"), ("DPV (kPa)", clim["dpv"], "#eda100"),
           ("Caída de hojas (g/trampa/día)", mens(NEC, "caida_hojas_g_dia"), "#8a6d3b"),
           ("Hojas jóvenes A+B+C (%)", mens(CULT, "joven"), "#2a78d6"),
           ("Incidencia Antracnosis (%)", mens(CULT, "antrac_inc"), "#e34948"),
           ("Incidencia SALB (%)", mens(CULT, "salb_inc"), "#6250d6")]
fig, axs = plt.subplots(len(paneles), 1, figsize=(8, 10), sharex=True)
for ax, (tit, s, col) in zip(axs, paneles):
    ax.axvspan(0.5, 4.5, color="#f0f0f0", zorder=0)
    s = s.reindex(range(1, 13)); ax.plot(s.index, s.values, marker="o", ms=4, color=col)
    ax.set_ylabel(tit, fontsize=8, rotation=0, ha="right", va="center")
axs[-1].set_xticks(range(1, 13)); axs[-1].set_xticklabels([MESES[i] for i in range(1, 13)])
fig.suptitle("Lote San Carlos: secuencia anual clima → fenología → enfermedad", y=0.995); fig.tight_layout()
guardar(fig, "9_1_ciclo_anual_integrado")
""")

md(r"""
---
# 10. Exportar resultados

Se guarda un Excel `Base_SanCarlos_clima_cultivo.xlsx` con una hoja **LEEME** que describe cada hoja. Las figuras ya están en `resultados/figuras/`.
""")

code(r"""
LEEME = pd.DataFrame([
    ("clima_diario", "Base climática diaria del lote 2011-2025. Sufijos: _era5c ERA5-Land con HR corregida (principal T/HR), _era5 ERA5-Land/ERA5 sin corregir, _chirps CHIRPS (principal lluvia), _pal La Palomera observada. _ma3r/_ma7r medias móviles retrasadas, _ma3c/_ma7c centradas, _acum lluvia acumulada. salb_fav/clf_fav días favorables (1/0)."),
    ("clima_8dias_ene_abr", "Agregados por periodos de 8 días (desde el 1 de enero) en enero-abril, por año."),
    ("validacion_palomera", "Métricas estación La Palomera vs. ERA5-Land y CHIRPS en la celda de la estación, por escala (diaria, 8 días, mensual) y ventana."),
    ("deteccion_lluvia", "POD, FAR y CSI de días lluviosos (≥1 mm) en ene-abr; desfase 1 = producto comparado con el día siguiente."),
    ("validacion_correccion_HR", "Horas/día con HR≥90 %: ERA5-Land sin y con corrección por cuantiles (validación cruzada por años)."),
    ("cambios_8dias", "Pruebas de cambio entre periodos de 8 días en ene-abr: Kruskal-Wallis, eta², % de transiciones consecutivas con cambio significativo (Mann-Whitney), autocorrelación."),
    ("cultivo_fecha_clon", "Resumen por fecha y clon: incidencia (_inc, %), severidad media (_sev, 0-4), índice de severidad de McKinney (_ise, %), estados de hoja, densidades, delta = cambio desde la evaluación anterior."),
    ("abcpe_arbol", "Área bajo la curva de progreso de la enfermedad por árbol y temporada ene-abr."),
    ("kruskal_clones", "Comparación de ABCPE entre clones por temporada."),
    ("necromasa", "Peso medio de hojas y flores por trampa, y tasa de caída (g/trampa/día)."),
    ("lai", "LAI4, LAI5 y % de cobertura por fecha y clon."),
    ("clima_por_evaluacion", "Clima resumido en ventanas previas a cada fecha de evaluación (v0-8 = días 1 a 8 antes, etc.)."),
    ("correlaciones", "Spearman enfermedad vs. clima por ventana, ene-abr 2018-2020, promedio de clones por fecha. p_FDR = Benjamini-Hochberg."),
    ("sensibilidad_fuente", "ρ con la fuente A vs. B: lote vs. La Palomera, y La Palomera con vs. sin filtro del sensor de T."),
    ("sensor_T_palomera", "Problema del sensor de T de La Palomera: días eliminados por año y validación de T con y sin filtro."),
    ("modelo_GEE", "Razones de odds del modelo GEE binomial a nivel de árbol."),
    ("correlaciones_dosel", "Spearman caída de hojas y LAI vs. clima (todo el año)."),
], columns=["hoja", "descripcion"])

ruta_xlsx = RESULT / "Base_SanCarlos_clima_cultivo.xlsx"
with pd.ExcelWriter(ruta_xlsx) as xw:
    LEEME.to_excel(xw, sheet_name="LEEME", index=False)
    D.round(3).to_excel(xw, sheet_name="clima_diario")
    P8.round(3).to_excel(xw, sheet_name="clima_8dias_ene_abr", index=False)
    VALIDACION.to_excel(xw, sheet_name="validacion_palomera", index=False)
    DETECCION.to_excel(xw, sheet_name="deteccion_lluvia", index=False)
    VALID_QM.to_excel(xw, sheet_name="validacion_correccion_HR", index=False)
    CAMBIOS_8D.to_excel(xw, sheet_name="cambios_8dias", index=False)
    CULT.round(3).to_excel(xw, sheet_name="cultivo_fecha_clon", index=False)
    ARB.round(3).to_excel(xw, sheet_name="abcpe_arbol", index=False)
    KW_CLONES.to_excel(xw, sheet_name="kruskal_clones", index=False)
    NEC.round(3).to_excel(xw, sheet_name="necromasa", index=False)
    LAI.round(3).to_excel(xw, sheet_name="lai", index=False)
    CLIMA_EVAL.round(3).to_excel(xw, sheet_name="clima_por_evaluacion")
    CORR.to_excel(xw, sheet_name="correlaciones", index=False)
    SENS.to_excel(xw, sheet_name="sensibilidad_fuente", index=False)
    SENSOR_DIAS.to_excel(xw, sheet_name="sensor_T_palomera", index=False)
    SENSOR_VAL.to_excel(xw, sheet_name="sensor_T_palomera", index=False, startcol=len(SENSOR_DIAS.columns) + 2)
    GEE.to_excel(xw, sheet_name="modelo_GEE")
    CORR_DOSEL.to_excel(xw, sheet_name="correlaciones_dosel", index=False)
print("Excel guardado en:", ruta_xlsx)
print("Figuras:", sorted(p.name for p in FIGS.glob("*.png")))
""")

md(r"""
## 10.1 Resumen automático de resultados
Esta celda imprime las cifras clave para redactar los resultados del artículo.
""")

code(r"""
def linea(t): print("•", t)
print("RESUMEN – Lote San Carlos\n")
linea(f"Distancia a La Palomera: {DIST_PAL:.1f} km")
v = VALIDACION[(VALIDACION.ventana == "Ene–Abr")].set_index(["escala", "variable", "producto"])
for var, prod in [("T media (°C)", "ERA5-Land"), ("Horas HR≥90 % (h/día)", "ERA5-Land"), ("Lluvia (mm)", "CHIRPS"), ("Lluvia (mm)", "ERA5")]:
    rr = [v.loc[(e, var, prod), "r_pearson"] if (e, var, prod) in v.index else np.nan for e in ("diaria", "8 días", "mensual")]
    linea(f"Ene–abr {var} {prod}: r diaria {rr[0]:.2f} · 8 días {rr[1]:.2f} · mensual {rr[2]:.2f}")
q = VALID_QM[VALID_QM.ventana == "Ene–Abr"].set_index("producto")
linea(f"Horas HR≥90 % ene–abr: sesgo ERA5-Land {q.loc['ERA5-Land', 'sesgo_h']:+.1f} h/día → corregido {q.loc['ERA5-Land corregido', 'sesgo_h']:+.1f} h/día")
for _, f in CAMBIOS_8D.iterrows():
    linea(f"Cada 8 días – {f.variable}: Kruskal p={f.kruskal_p:.1e}, η²={f.eta2_medio:.2f}, {f.pct_cambios_signif:.0f} % de transiciones con cambio significativo")
for r in RESP.values():
    t = CORR[(CORR.respuesta == r) & ~CORR.variable.str.contains("Palomera")].sort_values("p").head(1)
    if len(t):
        t = t.iloc[0]; linea(f"{r}: mejor relación con {t.variable} en {t.ventana} (ρ={t.rho:+.2f}, p={t.p:.3f}, p_FDR={t.p_FDR:.3f}, n={t.n})")
""")

md(r"""
---
## Cómo interpretar y limitaciones (para la discusión del artículo)

1. **Fuente de humedad.** La HR de ERA5-Land se corrigió con La Palomera, que está a pocos km del lote; es el mejor escenario posible sin sensores en el lote. La sensibilidad (8.3) indica si las conclusiones dependen de la fuente.
2. **Lluvia diaria.** El acuerdo diario entre pluviómetro y satélite es bajo en lluvias convectivas; por eso se trabaja con acumulados de 8 días o más.
3. **Tamaño de muestra.** Solo hay 3 temporadas enero–abril completas con enfermedad (2018–2020; en 2017 solo hay evaluaciones desde el 27 de marzo) y un lote. Las correlaciones son exploratorias; la relación entre años (p. ej. 2018 con más SALB) depende de pocos casos.
4. **Fenología como confusor.** Gran parte de la variación de la enfermedad sigue a la aparición de hojas jóvenes. Por eso el modelo GEE incluye el % de hojas jóvenes: el efecto del clima se interpreta *dado* un nivel de follaje susceptible.
5. **Sensor de temperatura de La Palomera.** Entre 2011 y 2012 marcó medias de 12–15 °C (error del sensor). Se reportan los resultados con y sin filtro (secciones 3.1 y 8.3). La conclusión principal usa la versión con filtro; el efecto sobre la relación con el cultivo depende de los días afectados en 2016–2020 (tabla 3.1). Conviene informarlo al IDEAM.
6. **Siguientes pasos sugeridos:** (a) incluir el índice ONI (El Niño/La Niña) para explicar diferencias entre años; (b) instalar un sensor de mojadura foliar en el lote durante una temporada para validar el umbral de 10 h; (c) si hay datos de otros lotes, repetir el cuaderno cambiando las coordenadas en la celda 0.2.

**Referencias de métodos:** McKinney (1923) índice de severidad; Shaner & Finney (1977) ABCPE; Liang & Zeger (1986) GEE; Benjamini & Hochberg (1995) FDR; Themeßl et al. (2011) mapeo de cuantiles; Hallé et al. (1978) estados foliares del caucho; Funk et al. (2015) CHIRPS; Muñoz-Sabater et al. (2021) ERA5-Land.
""")


nb = nbf.v4.new_notebook()
nb["cells"] = celdas
nb["metadata"] = {"kernelspec": {"name": "python3", "display_name": "Python 3"},
                  "language_info": {"name": "python"}, "colab": {"provenance": []}}
nbf.write(nb, sys.argv[1])
print("Cuaderno escrito:", sys.argv[1], len(celdas), "celdas")
