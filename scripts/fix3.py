"""Parche 3: modos reutilizar/descargar, procedencia, T máx/mín, brillo solar, DHIME."""
from pathlib import Path

RUTA = Path(__file__).with_name("construir_cuaderno.py")
s = RUTA.read_text()


def rep(viejo, nuevo, n=1):
    global s
    c = s.count(viejo)
    assert c == n, f"{c} coincidencias para: {viejo[:80]!r}"
    s = s.replace(viejo, nuevo)


def rep_entre(inicio, fin, nuevo):
    # Reemplaza desde 'inicio' hasta 'fin' (incluido)
    global s
    i = s.index(inicio); j = s.index(fin, i) + len(fin)
    assert s.count(inicio) == 1, inicio[:60]
    s = s[:i] + nuevo + s[j:]


# ------------------------------------------------------------------ portada
rep("| 1. Descarga de datos | Obtiene ERA5-Land (T, HR horaria), ERA5 (lluvia, radiación, ETo), CHIRPS (lluvia diaria) y la estación automática IDEAM **La Palomera** (HR, T y lluvia). |",
    "| 1. Descarga de datos | **Protocolo de descarga reproducible.** ERA5-Land (T, HR horaria), ERA5 (lluvia, radiación, brillo solar, ETo), CHIRPS (lluvia diaria), IDEAM **La Palomera** automática (HR, T, T máx, T mín, lluvia) y diaria oficial DHIME (brillo solar, HR, lluvia, T máx, T mín, T media). Cada archivo queda registrado con fecha, URL, parámetros y huella SHA-256. |")
rep("| 3. Validación ene–abr | ¿Se pueden correlacionar los datos de La Palomera con CHIRPS y ERA5-Land de enero a abril? ¿A qué escala (diaria, 8 días, mensual)? |",
    "| 3. Validación ene–abr | ¿Se pueden correlacionar los datos de La Palomera con CHIRPS y ERA5-Land de enero a abril? ¿A qué escala (diaria, 8 días, mensual)? Incluye la validación con la serie diaria oficial DHIME y el brillo solar. |")

rep_entre("## Cómo usarlo en Google Colab\n1. En su Google Drive",
          "y todo corre en ~2 min.",
          r"""## Cómo usarlo en Google Colab
1. En su Google Drive debe estar la carpeta del proyecto (por ejemplo `MyDrive/tapiero/`) con:
   - `Fenologia_base Orinoquia.xlsx` en la raíz (**siempre**);
   - `san_carlos/datos_crudos/palomera/dhime/` con los Excel de DHIME (**siempre**: DHIME no tiene API y no se puede descargar desde el código; ver 1.4);
   - el resto de `san_carlos/datos_crudos/` **solo si quiere repetir exactamente el análisis ya hecho** (modo `"reutilizar"`).
2. Abra este cuaderno en Colab (*Archivo → Abrir cuaderno → Google Drive*).
3. En la celda **0.2** revise `RUTA_DRIVE` y elija `MODO_DATOS`:
   - `"reutilizar"` → usa los datos ya descargados (las mismas cifras del artículo). Tarda ~2 min.
   - `"descargar"` → baja **todo** otra vez desde las fuentes originales a una carpeta nueva `datos_crudos_descarga_AAAA-MM-DD/`. Tarda 15–40 min, porque datos.gov.co es lento. No borra los datos anteriores.
4. *Entorno de ejecución → Ejecutar todas*.""")

# ------------------------------------------------------------------ 0.1 importaciones
rep("import io, json, math, time, warnings\nfrom pathlib import Path",
    "import io, json, math, re, time, unicodedata, warnings, hashlib, platform\nimport importlib.metadata\nfrom datetime import datetime\nfrom pathlib import Path")

# ------------------------------------------------------------------ 0.2 texto
rep("- Si ya existe la carpeta `climate/datos_crudos/palomera/` del trabajo anterior, se reutiliza la HR horaria de La Palomera para no descargarla de nuevo.\n",
    r"""- `MODO_DATOS`: de dónde salen los datos climáticos.

  | Modo | Qué hace | Cuándo usarlo |
  |---|---|---|
  | `"reutilizar"` | Lee los archivos de `san_carlos/datos_crudos/`. Si falta alguno, lo descarga. Si faltan los crudos de HR/T de La Palomera pero existe la carpeta `climate/` del trabajo anterior, usa esa serie horaria. | Repetir exactamente el análisis (mismas cifras). |
  | `"descargar"` | Ignora lo guardado y baja **todo** de las fuentes originales a `san_carlos/datos_crudos_descarga_AAAA-MM-DD/`. Los resultados van a `resultados_descarga_AAAA-MM-DD/`. | Comprobar que el método se reproduce desde cero o actualizar los datos. |

  En los dos modos, DHIME se lee de los Excel que usted descarga a mano (sección 1.4).
""")

# ------------------------------------------------------------------ 0.2 código
rep('''SALIDA   = RUTA_DRIVE / "san_carlos"            # carpeta de trabajo de este análisis
CRUDOS   = SALIDA / "datos_crudos"              # descargas (se guardan para no repetirlas)
RESULT   = SALIDA / "resultados"                # Excel
FIGS     = RESULT / "figuras"                   # figuras PNG
PREVIO_PALOMERA = RUTA_DRIVE / "climate" / "datos_crudos" / "palomera" / "ideam_aut_horario.csv"
for c in (CRUDOS / "sancarlos", CRUDOS / "palomera", FIGS):
    c.mkdir(parents=True, exist_ok=True)''',
    '''SALIDA   = RUTA_DRIVE / "san_carlos"            # carpeta de trabajo de este análisis

# ---------------------------------------------------------------- MODO DE DATOS  ✏️
# "reutilizar": usa los datos ya descargados (los "congelados" con los que se hizo el análisis).
#               Si falta un archivo, lo descarga de la fuente.
# "descargar" : baja TODO otra vez de las fuentes originales a una carpeta nueva con la fecha de hoy
#               (no sobrescribe los datos congelados, así se pueden comparar las dos versiones).
MODO_DATOS = "reutilizar"
assert MODO_DATOS in ("reutilizar", "descargar"), "MODO_DATOS debe ser 'reutilizar' o 'descargar'"

HOY = f"{datetime.now():%Y-%m-%d}"
CONGELADOS = SALIDA / "datos_crudos"            # datos con los que se hizo el análisis
if MODO_DATOS == "reutilizar":
    CRUDOS, RESULT = CONGELADOS, SALIDA / "resultados"
else:
    CRUDOS, RESULT = SALIDA / f"datos_crudos_descarga_{HOY}", SALIDA / f"resultados_descarga_{HOY}"
FIGS      = RESULT / "figuras"                  # figuras PNG
DHIME_DIR = CRUDOS / "palomera" / "dhime"       # Excel de DHIME descargados a mano (sección 1.4)
# Serie horaria de HR/T de La Palomera del trabajo anterior (solo se usa en modo "reutilizar" si faltan los crudos)
PREVIO_PALOMERA = RUTA_DRIVE / "climate" / "datos_crudos" / "palomera" / "ideam_aut_horario.csv"
for c in (CRUDOS / "sancarlos", CRUDOS / "palomera", DHIME_DIR, FIGS):
    c.mkdir(parents=True, exist_ok=True)''')
rep('''MIN_HORAS_DIA = 22                                         # horas válidas mínimas para calcular un día''',
    '''MIN_HORAS_DIA = 22                                         # horas válidas mínimas para calcular un día
MIN_HORAS_EXT = 18                                         # horas mínimas para T máx/mín de los sensores de extremos''')
rep('''print("Resultados en:", SALIDA)''',
    '''print("Modo de datos:", MODO_DATOS, "| datos crudos en:", CRUDOS)
print("Resultados en:", RESULT)''')

# ------------------------------------------------------------------ 1. encabezado + 1.0 + 1.1
rep_entre("---\n# 1. Descarga de datos climáticos",
          '''    era5d[k].columns = ["rad", "etp", "prec"]               # MJ/m²/día, mm/día, mm/día
print({k: (v.index.min().date(), v.index.max().date()) for k, v in era5h.items()})
""")''',
          r'''---
# 1. Descarga de datos (protocolo reproducible)

## 1.0 Fuentes, modos de ejecución y registro de procedencia

| Fuente | Proveedor | Acceso | Resolución | Variables usadas | Cita |
|---|---|---|---|---|---|
| **ERA5-Land** | ECMWF / Copernicus C3S (reanálisis) | API *archive* de Open-Meteo, `models=era5_land` | 0.1° (~9 km), horaria | T, HR, punto de rocío | Muñoz-Sabater et al. (2021) |
| **ERA5** | ECMWF / Copernicus C3S | API *archive* de Open-Meteo, `models=era5` | 0.25° (~28 km), diaria | lluvia, radiación de onda corta, brillo solar, ETo FAO-56 | Hersbach et al. (2020) |
| **CHIRPS v2.0** | Climate Hazards Center, UCSB | API ClimateSERV (NASA–USAID SERVIR), `datatype=0` | 0.05° (~5 km), diaria | lluvia | Funk et al. (2015) |
| **IDEAM La Palomera AUT [35185010]**, automática | IDEAM | API Socrata de datos.gov.co | puntual, 10 min a 1 h | HR, T, T máx, T mín, lluvia | IDEAM (año de consulta) |
| **IDEAM La Palomera, DHIME** (serie diaria oficial) | IDEAM | descarga manual en DHIME (no tiene API) | puntual, diaria | brillo solar, HR, lluvia, T máx, T mín, T media | IDEAM (año de consulta) |

Open-Meteo se cita como Zippenfenig (2023), *Open-Meteo.com Weather API*, Zenodo, doi:10.5281/zenodo.7970649.

**Modo de ejecución** (celda 0.2, `MODO_DATOS`):
- `"reutilizar"`: cada función de descarga mira primero si el archivo ya existe en `datos_crudos/`; si existe, lo lee y no se conecta a internet.
- `"descargar"`: se escribe en una carpeta nueva y vacía, así que todo se vuelve a bajar.

El código de descarga es el mismo en los dos modos. Eso garantiza que los datos guardados salieron de este mismo método.

**Registro de procedencia.** Cada archivo que entra al análisis queda anotado en `datos_crudos/metadatos_descarga.json` y en la hoja `procedencia_datos` del Excel final, con estos datos:
- fuente, URL y parámetros exactos de la consulta;
- fecha de descarga;
- celda del modelo que devolvió Open-Meteo;
- tamaño del archivo y huella **SHA-256**.

La huella SHA-256 es un código de 64 caracteres que cambia si cambia un solo byte del archivo. Si un revisor obtiene la misma huella, tiene exactamente los mismos datos.

> **Para el artículo.** Las fuentes se revisan con el tiempo: el IDEAM corrige y aprueba datos (Preliminar → Definitivo), CHIRPS reemplaza la versión preliminar por la final y ERA5 se reprocesa. Por eso, al publicar, conviene depositar la carpeta `datos_crudos/` (con `metadatos_descarga.json`) en un repositorio con DOI, como Zenodo, y citarla en *Disponibilidad de datos*. Este cuaderno documenta **el método**; la carpeta congelada permite reproducir **las mismas cifras**.
""")
code(r"""
RUTA_REGISTRO = CRUDOS / "metadatos_descarga.json"
try:                                               # registro de una ejecución anterior (si existe)
    REGISTRO_PREVIO = {r["archivo"]: r for r in json.loads(RUTA_REGISTRO.read_text())["archivos"]}
except Exception:
    REGISTRO_PREVIO = {}
REGISTRO = {}                                      # se llena con cada archivo usado en esta ejecución

def sha256(ruta):
    # Huella digital del archivo (se lee por bloques de 1 MB para no llenar la memoria)
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()

def usar_existente(ruta):
    # True -> leer el archivo guardado; False -> descargarlo.
    # En modo "descargar" CRUDOS es una carpeta nueva y vacía, así que siempre se descarga.
    return Path(ruta).exists() and Path(ruta).stat().st_size > 0

def registrar(ruta, fuente, url, parametros, descargado_ahora, nota="", fecha=None):
    # Anota de dónde salió un archivo crudo, con qué consulta, cuándo, y su huella SHA-256
    ruta = Path(ruta)
    try:
        rel = str(ruta.relative_to(RUTA_DRIVE))
    except ValueError:
        rel = str(ruta)
    previo, huella = REGISTRO_PREVIO.get(rel, {}), sha256(ruta)
    if descargado_ahora:
        fecha = datetime.now().isoformat(timespec="seconds")
    elif fecha is None:   # se conserva la fecha original; si no hay registro, la fecha del archivo
        fecha = previo.get("fecha_descarga") or \
            datetime.fromtimestamp(ruta.stat().st_mtime).isoformat(timespec="seconds") + " (fecha del archivo)"
    if previo.get("sha256") and previo["sha256"] != huella and not descargado_ahora:
        print(f"   ⚠️ {rel}: el archivo cambió desde que se registró (SHA-256 distinto)")
    REGISTRO[rel] = dict(archivo=rel, fuente=fuente, url=url, parametros=parametros, fecha_descarga=fecha,
                         origen_en_esta_ejecucion="descargado" if descargado_ahora else "reutilizado",
                         bytes=ruta.stat().st_size, sha256=huella, nota=nota or previo.get("nota", ""))

print("Modo:", MODO_DATOS, "| archivos registrados en una ejecución anterior:", len(REGISTRO_PREVIO))
""")

md(r"""
## 1.1 ERA5-Land horario y ERA5 diario (Open-Meteo)
La API *archive* de Open-Meteo entrega el reanálisis para un punto: devuelve la celda del modelo más cercana y su ubicación queda en el registro. `models=era5_land` fuerza la versión de 9 km. Las horas se piden en hora local (`America/Bogota`) para que el "día" coincida con el de la estación.

*Notas:*
- Open-Meteo no publica la lluvia de ERA5-Land, así que la lluvia del reanálisis viene de ERA5 (25 km).
- El **brillo solar** de ERA5 (`sunshine_duration`) es la suma de las horas en que la radiación solar directa supera 120 W/m². Es la definición de la OMM, la misma que usa un heliógrafo. Se convierte de segundos a horas.
""")
code(r"""
URL_OM = "https://archive-api.open-meteo.com/v1/archive"
MODELO = {"era5_land": "ERA5-Land", "era5": "ERA5"}

def open_meteo(lat, lon, params, ruta):
    # Descarga una serie de Open-Meteo y la guarda como CSV; si el archivo ya existe (modo reutilizar), lo lee
    consulta = dict(latitude=round(lat, 6), longitude=round(lon, 6), start_date=PERIODO[0], end_date=PERIODO[1],
                    timezone="America/Bogota", **params)
    fuente = f"{MODELO[params['models']]} (ECMWF/Copernicus) vía Open-Meteo"
    if usar_existente(ruta):
        registrar(ruta, fuente, URL_OM, consulta, descargado_ahora=False)
        return pd.read_csv(ruta, index_col=0, parse_dates=True)
    for intento in range(5):                              # reintentos si la API está ocupada
        r = requests.get(URL_OM, params=consulta, timeout=300)
        if r.status_code == 200:
            break
        print(f"   Open-Meteo respondió {r.status_code}; reintento {intento + 1}/5")
        time.sleep(20 * (intento + 1))
    r.raise_for_status()
    js = r.json()
    clave = "hourly" if "hourly" in params else "daily"
    d = pd.DataFrame(js[clave]).rename(columns={"time": "fecha"})
    d["fecha"] = pd.to_datetime(d["fecha"])
    d = d.set_index("fecha")
    d.to_csv(ruta)
    nota = f"celda del modelo: {js['latitude']:.4f}, {js['longitude']:.4f}; elevación {js.get('elevation')} m"
    registrar(ruta, fuente, URL_OM, consulta, descargado_ahora=True, nota=nota)
    print(f"   descargado {ruta.name}: {nota} | {len(d)} filas")
    return d

def renombrar(d, mapa):
    # Nombres cortos; acepta nombres con sufijo del modelo (p. ej. 'temperature_2m_era5_land')
    return d.rename(columns={c: corto for c in d.columns for largo, corto in mapa.items() if c.startswith(largo)})

era5h, era5d = {}, {}
for k, p in PUNTOS.items():
    era5h[k] = renombrar(open_meteo(p["lat"], p["lon"],
                                    dict(hourly="temperature_2m,relative_humidity_2m,dew_point_2m", models="era5_land"),
                                    CRUDOS / k / "era5land_horario.csv"),
                         {"temperature_2m": "t", "relative_humidity_2m": "hr", "dew_point_2m": "td"})
    era5d[k] = renombrar(open_meteo(p["lat"], p["lon"],
                                    dict(daily="shortwave_radiation_sum,et0_fao_evapotranspiration,precipitation_sum,"
                                               "sunshine_duration", models="era5"),
                                    CRUDOS / k / "era5_diario.csv"),
                         {"shortwave_radiation_sum": "rad", "et0_fao_evapotranspiration": "etp",
                          "precipitation_sum": "prec", "sunshine_duration": "bs"})
    era5d[k]["bs"] = era5d[k]["bs"] / 3600                 # segundos -> horas de sol por día
    # Unidades: rad MJ/m²/día, etp mm/día, prec mm/día, bs h/día
print({k: (v.index.min().date(), v.index.max().date()) for k, v in era5h.items()})
""")''')

# ------------------------------------------------------------------ 1.2 CHIRPS con registro
rep('''def descargar_chirps():
    ruta = CRUDOS / "chirps_diario.csv"
    if ruta.exists():
        return pd.read_csv(ruta, index_col=0, parse_dates=True).astype(float)''',
    '''def descargar_chirps():
    ruta = CRUDOS / "chirps_diario.csv"
    consulta = dict(datatype="0 (CHIRPS v2.0 diario)", operationtype="5 (promedio espacial)", intervaltype=0,
                    poligono="cuadrado de ±0.0024° alrededor de cada punto (dentro de un píxel)",
                    bloques="5 años", periodo=PERIODO,
                    puntos={k: [round(p["lat"], 6), round(p["lon"], 6)] for k, p in PUNTOS.items()})
    fuente = "CHIRPS v2.0 (UCSB-CHC) vía ClimateSERV"
    if usar_existente(ruta):
        registrar(ruta, fuente, URL_CS, consulta, descargado_ahora=False)
        return pd.read_csv(ruta, index_col=0, parse_dates=True).astype(float)''')
rep('''    df = pd.DataFrame(tabla).rename_axis("fecha")
    df.to_csv(ruta)
    return df''',
    '''    df = pd.DataFrame(tabla).rename_axis("fecha")
    df.to_csv(ruta)
    registrar(ruta, fuente, URL_CS, consulta, descargado_ahora=True)
    return df''')

# ------------------------------------------------------------------ 1.3 datos.gov.co
rep_entre("## 1.3 Estación automática IDEAM La Palomera (datos.gov.co)",
          '''pal_h = palomera_horaria()
print(pal_h.describe().round(1))
print("Periodo:", pal_h.index.min(), "→", pal_h.index.max())
""")''',
          r'''## 1.3 Estación automática IDEAM La Palomera (datos.gov.co)
El IDEAM publica en datos.gov.co las observaciones de sus estaciones automáticas (API *Socrata*). Se descarga cada variable completa para la estación `0035185010` y se guarda **tal como llega** (`ideam_aut_<variable>_crudo.csv`); el paso a datos horarios se hace aquí, a la vista:

| Variable | Conjunto de datos | Registro original | Agregación horaria |
|---|---|---|---|
| Humedad del aire a 2 m | `uext-mhny` | cada 10 min | promedio |
| Temperatura del aire a 2 m | `sbwg-7ju4` | cada 10 min | promedio |
| Temperatura máxima del aire a 2 m | `ccvq-rp9s` | máxima de cada hora | **máximo** |
| Temperatura mínima del aire a 2 m | `afdg-3zpb` | mínima de cada hora | **mínimo** |
| Precipitación | `s54a-sgyg` | cada 10 min | **suma** |

La T máxima y la mínima vienen de sensores de extremos, que registran el valor extremo dentro de cada hora. Por eso son mejores que tomar la máxima o la mínima de los promedios de 10 min, que suavizan los picos.

datos.gov.co **no publica el brillo solar**. Se obtiene de DHIME (sección 1.4).

En modo `"reutilizar"`, si faltan los crudos de HR y T pero existe la carpeta `climate/` del trabajo anterior, se usa su serie horaria, que salió de los mismos conjuntos de datos.
""")
code(r"""
URL_SOC = "https://www.datos.gov.co/resource/{ds}.csv"
DS_IDEAM = {  # variable: (conjunto de datos, nombre en datos.gov.co, agregación horaria, columna horaria)
    "hr":   ("uext-mhny", "Humedad del Aire 2 m", "mean", "hr"),
    "t":    ("sbwg-7ju4", "Temperatura Ambiente del Aire 2 m", "mean", "t"),
    "tmax": ("ccvq-rp9s", "Temperatura Máxima del Aire 2 m", "max", "tx"),
    "tmin": ("afdg-3zpb", "Temperatura Mínima del Aire 2 m", "min", "tn"),
    "prec": ("s54a-sgyg", "Precipitación", "sum", "prec"),
}

def consulta_socrata(codigo):
    return {"$select": "fechaobservacion,valorobservado", "$where": f"codigoestacion='{codigo}'",
            "$order": "fechaobservacion"}

def socrata(ds, codigo, lote=500000):
    # Descarga por páginas (de 'lote' filas) todas las observaciones de una estación en un conjunto de datos
    partes, offset = [], 0
    while True:
        q = {**consulta_socrata(codigo), "$limit": lote, "$offset": offset}
        r = requests.get(URL_SOC.format(ds=ds), params=q, timeout=3600); r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text)); partes.append(df)
        print(f"   {ds}: {offset + len(df):,} registros")
        if len(df) < lote: break
        offset += lote
    return pd.concat(partes, ignore_index=True)

def palomera_cruda(var):
    # Serie original (sin agregar) de una variable; se descarga solo si no está guardada
    ds, nombre, _, _ = DS_IDEAM[var]
    ruta = CRUDOS / "palomera" / f"ideam_aut_{var}_crudo.csv"
    nuevo = not usar_existente(ruta)
    if nuevo:
        socrata(ds, PALOMERA["codigo"]).to_csv(ruta, index=False)
    registrar(ruta, f"IDEAM vía datos.gov.co – {nombre}", URL_SOC.format(ds=ds),
              consulta_socrata(PALOMERA["codigo"]), descargado_ahora=nuevo)
    d = pd.read_csv(ruta)
    s = pd.Series(d["valorobservado"].astype(float).values, index=pd.to_datetime(d["fechaobservacion"]))
    return s[~s.index.duplicated()].sort_index()

def palomera_horaria():
    partes = {}
    for var, (ds, nombre, agregacion, col) in DS_IDEAM.items():
        crudo = CRUDOS / "palomera" / f"ideam_aut_{var}_crudo.csv"
        if var in ("hr", "t") and MODO_DATOS == "reutilizar" and not usar_existente(crudo) and PREVIO_PALOMERA.exists():
            # Serie horaria del trabajo anterior (carpeta climate/), obtenida del mismo conjunto de datos
            partes[col] = pd.read_csv(PREVIO_PALOMERA, index_col=0, parse_dates=True)[var]
            registrar(PREVIO_PALOMERA, "IDEAM vía datos.gov.co (serie horaria del trabajo climate/)",
                      URL_SOC.format(ds=ds), consulta_socrata(PALOMERA["codigo"]), descargado_ahora=False)
            continue
        try:
            s = palomera_cruda(var)
        except Exception as e:
            print(f"   ⚠️ No se pudo obtener {nombre}: {e}"); continue
        g = s.groupby(s.index.floor("h"))                 # agrupa por hora
        partes[col] = g.agg(agregacion)
        if var == "prec":
            partes["n_prec"] = g.count()                  # nº de registros de lluvia en la hora
    h = pd.DataFrame(partes).sort_index()
    h.index.name = "fecha_hora"
    return h

pal_h = palomera_horaria()
print(pal_h.describe().round(1))
print("Periodo:", pal_h.index.min(), "→", pal_h.index.max())
""")

md(r"""
## 1.4 Serie diaria oficial de La Palomera en DHIME (incluye brillo solar)
**DHIME** (http://dhime.ideam.gov.co/atencionciudadano/) es el sistema oficial del IDEAM. Allí cada dato diario tiene un **nivel de aprobación** (*Definitivo*, *En revisión* o *Preliminar*), y es la única fuente del **brillo solar**. No tiene API, así que se descarga a mano **una vez** y los Excel se guardan en `san_carlos/datos_crudos/palomera/dhime/`.

**Pasos en DHIME:**
1. Entre a la página, acepte los términos y abra *Consultar y descargar datos*.
2. En el filtro de estaciones busque **35185010** (LA PALOMERA - AUT).
3. Elija **Frecuencia: Diaria** y el rango de fechas **01/01/2010 hasta hoy**.
4. Haga una consulta por cada fila de la tabla, agréguela y descargue el Excel.

| Archivo sugerido | Variable | Parámetro |
|---|---|---|
| `DHIME_BS_LaPalomera.xlsx` | BRILLO SOLAR | Brillo solar total diario |
| `DHIME_HR_LaPalomera.xlsx` | HUM RELATIVA | Humedad relativa del aire a 2 metros media diaria |
| `DHIME_PREC_LaPalomera.xlsx` | PRECIPITACION | Precipitación total diaria (o *Día pluviométrico*) |
| `DHIME_TMAX_LaPalomera.xlsx` | TEMPERATURA | Temperatura máxima diaria |
| `DHIME_TMIN_LaPalomera.xlsx` | TEMPERATURA | Temperatura mínima diaria |
| `DHIME_TMED_LaPalomera.xlsx` | TEMPERATURA | Temperatura seca media diaria |

El nombre del archivo no importa. El código lee el encabezado de cada Excel (estación, variable, parámetro, fecha del reporte) y así sabe qué contiene. Si un archivo es de otra estación, se avisa y se ignora.

Lo que falte simplemente se omite: el análisis principal no depende de DHIME. DHIME sirve para **(a)** validar ERA5 con el brillo solar, **(b)** comprobar la serie automática de datos.gov.co contra la oficial y **(c)** ver si la serie oficial también tiene el problema del sensor de T de 2011–2012.

En modo `"descargar"`, si la carpeta nueva no tiene archivos DHIME, se usan los de `datos_crudos/palomera/dhime/` y se avisa.
""")
code(r"""
URL_DHIME = "http://dhime.ideam.gov.co/atencionciudadano/"

def sin_tildes(t):
    return "".join(c for c in unicodedata.normalize("NFD", str(t)) if unicodedata.category(c) != "Mn").upper()

def identificar(variable, parametro):
    # Nombre corto de la variable a partir del encabezado DHIME
    v, p = sin_tildes(variable), sin_tildes(parametro)
    if "BRILLO" in v: return "bs"
    if "HUM" in v: return "hr"
    if "PRECIP" in v: return "prec"
    if "TEMP" in v:
        for clave, corto in (("MAXIMA", "tmax"), ("MINIMA", "tmin"), ("MEDIA", "tmed")):
            if clave in p: return corto
    return None

def leer_dhime(ruta):
    # Lee un reporte DHIME (puede traer varios bloques estación/variable) y devuelve una tabla larga
    crudo = pd.read_excel(ruta, header=None, dtype=str)
    m = re.search(r"generado \((.+?)\)", " ".join(crudo.iloc[0].dropna().astype(str)))
    generado = m.group(1) if m else None
    filas, est, var, par = [], "", "", ""
    for f in crudo.itertuples(index=False):
        c0 = str(f[0]).strip()
        if c0 == "Nombre estacion:": est = str(f[1])
        elif c0 == "Variable:":      var = str(f[1])
        elif c0 == "Parametro:":     par = str(f[1])
        elif re.match(r"^\d{4}-\d{2}-\d{2}", c0):
            filas.append((est, identificar(var, par), par, pd.Timestamp(c0[:10]), f[2], f[4] if len(f) > 4 else None))
    t = pd.DataFrame(filas, columns=["estacion", "var", "parametro", "fecha", "valor", "aprobacion"])
    t["valor"] = pd.to_numeric(t["valor"], errors="coerce")
    return t, generado

def cargar_dhime():
    carpeta = DHIME_DIR
    archivos = sorted(carpeta.glob("*.xls*"))
    if not archivos and MODO_DATOS == "descargar":
        carpeta = CONGELADOS / "palomera" / "dhime"; archivos = sorted(carpeta.glob("*.xls*"))
        if archivos:
            print("   ⚠️ DHIME no tiene API: se usan los Excel DHIME de", carpeta)
    partes, inventario = [], []
    for a in archivos:
        t, generado = leer_dhime(a)
        if t.empty:
            print("   ⚠️", a.name, "no tiene datos reconocibles"); continue
        estaciones = t.estacion.unique()
        if not any(PALOMERA["codigo"].lstrip("0") in e for e in estaciones):
            print(f"   ⚠️ {a.name} es de otra estación ({', '.join(estaciones)}); se ignora"); continue
        t = t[t.estacion.str.contains(PALOMERA["codigo"].lstrip("0")) & t["var"].notna()]
        registrar(a, "IDEAM DHIME (descarga manual)", URL_DHIME,
                  dict(estacion=PALOMERA["nombre"], variables=sorted(t["var"].unique()),
                       parametros=sorted(t.parametro.unique()), frecuencia="Diaria"),
                  descargado_ahora=False, nota=f"reporte DHIME generado el {generado}",
                  fecha=f"{generado} (reporte DHIME)" if generado else None)
        for v, g in t.groupby("var"):
            ap = g.aprobacion.value_counts(normalize=True).mul(100).round(1)
            inventario.append(dict(variable=v, archivo=a.name, parametro=g.parametro.iloc[0],
                                   desde=g.fecha.min().date(), hasta=g.fecha.max().date(), n_dias=g.valor.notna().sum(),
                                   **{f"pct_{k}": x for k, x in ap.items()}))
        partes.append(t)
    if not partes:
        return pd.DataFrame(index=pd.DatetimeIndex([], name="fecha")), pd.DataFrame()
    t = pd.concat(partes).drop_duplicates(["var", "fecha"])
    ancho = t.pivot(index="fecha", columns="var", values="valor").add_suffix("_dhime")
    # Control de rango físico (mismos límites que la estación automática)
    limites = {"bs_dhime": (0, 13), "hr_dhime": (10, 100), "prec_dhime": (0, 300),
               "tmax_dhime": (10, 45), "tmin_dhime": (10, 45), "tmed_dhime": (10, 45)}
    for c, (a, b) in limites.items():
        if c in ancho: ancho[c] = ancho[c].where(ancho[c].between(a, b))
    ancho.index.name = "fecha"
    return ancho, pd.DataFrame(inventario)

pal_dhime, DHIME_INV = cargar_dhime()
faltan = [v for v in ("bs", "hr", "prec", "tmax", "tmin", "tmed") if f"{v}_dhime" not in pal_dhime]
print("Variables DHIME disponibles:", [c.replace("_dhime", "") for c in pal_dhime.columns] or "ninguna")
if faltan:
    print("Faltan en", DHIME_DIR, "→", faltan, "(descárguelas de DHIME siguiendo la tabla de arriba)")
DHIME_INV
""")

md(r"""
## 1.5 Registro de procedencia y versiones del software
Aquí se guarda `metadatos_descarga.json` y se muestra el registro completo. También se anotan las versiones de Python y de las librerías: un cambio de versión puede alterar ligeramente algunos resultados, como los del modelo GEE.
""")
code(r"""
VERSIONES = pd.DataFrame([("python", platform.python_version())] +
                         [(p, importlib.metadata.version(p)) for p in
                          ("numpy", "pandas", "scipy", "statsmodels", "matplotlib", "requests", "openpyxl")],
                         columns=["paquete", "version"])
META = dict(proyecto="Lote San Carlos – clima y cultivo de caucho", cuaderno="Analisis_SanCarlos_clima_cultivo.ipynb",
            modo_datos=MODO_DATOS, ejecutado=datetime.now().isoformat(timespec="seconds"), periodo=PERIODO,
            lote=LOTE, estacion=PALOMERA, en_colab=EN_COLAB,
            software=dict(zip(VERSIONES.paquete, VERSIONES.version)), archivos=list(REGISTRO.values()))
RUTA_REGISTRO.write_text(json.dumps(META, ensure_ascii=False, indent=2, default=str))
PROCEDENCIA = pd.DataFrame(REGISTRO.values())
PROCEDENCIA["parametros"] = PROCEDENCIA["parametros"].apply(lambda x: json.dumps(x, ensure_ascii=False, default=str))
print("Registro guardado en:", RUTA_REGISTRO)
print(VERSIONES.to_string(index=False))
PROCEDENCIA[["archivo", "fuente", "fecha_descarga", "origen_en_esta_ejecucion", "bytes", "sha256", "nota"]]
""")''')

# ------------------------------------------------------------------ 2. QC y diario con T máx/mín
rep('''4. **Lluvia:** horas con > 100 mm se descartan.''',
    '''4. **T máxima y mínima** (sensores de extremos): mismos rangos que la T. Con filtro, también se descartan en los días que el filtro marca como malos.
5. **Lluvia:** horas con > 100 mm se descartan.''')
rep('''- `tmed`, `tmax`, `tmin`: media, máxima y mínima de las horas.''',
    '''- `tmed`: media de las horas.
- `tmax`, `tmin`: en La Palomera, máximo y mínimo de los **sensores de extremos**. Se exigen ≥ 18 horas con registro (`MIN_HORAS_EXT`), porque estos sensores tienen más huecos y el extremo del día casi nunca se pierde con 18 horas. En ERA5-Land, máximo y mínimo de las 24 horas.''')
rep('''    h["hr"] = h["hr"].where(h["hr"].between(10, 100))
    if filtro_sensor:
        h["t"] = h["t"].where(h["t"].between(15, 42))      # rango horario plausible en los Llanos
        # Días con T media fuera de 20-33 °C = sensor dañado (p. ej. 2011-2012 marcó medias de 12-15 °C)
        t_dia = h["t"].groupby(h.index.normalize()).transform("mean")
        h.loc[~t_dia.between(20, 33), "t"] = np.nan
    else:
        h["t"] = h["t"].where(h["t"].between(10, 45))      # QC básico del trabajo anterior''',
    '''    h["hr"] = h["hr"].where(h["hr"].between(10, 100))
    cols_t = [c for c in ("t", "tx", "tn") if c in h]       # T media horaria y sensores de extremos
    if filtro_sensor:
        for c in cols_t:
            h[c] = h[c].where(h[c].between(15, 42))        # rango horario plausible en los Llanos
        # Días con T media fuera de 20-33 °C = sensor dañado (p. ej. 2011-2012 marcó medias de 12-15 °C)
        t_dia = h["t"].groupby(h.index.normalize()).transform("mean")
        h.loc[~t_dia.between(20, 33), cols_t] = np.nan
    else:
        for c in cols_t:
            h[c] = h[c].where(h[c].between(10, 45))        # QC básico del trabajo anterior''')
rep('''    n_t, n_hr = g["t"].count(), g["hr"].count()
    ok_t, ok_hr = n_t >= MIN_HORAS_DIA, n_hr >= MIN_HORAS_DIA
    d = pd.DataFrame({
        "tmed": g["t"].mean().where(ok_t), "tmax": g["t"].max().where(ok_t), "tmin": g["t"].min().where(ok_t),''',
    '''    n_t, n_hr = g["t"].count(), g["hr"].count()
    ok_t, ok_hr = n_t >= MIN_HORAS_DIA, n_hr >= MIN_HORAS_DIA
    # T máx/mín: sensores de extremos si existen (estación); si no, extremos de la T horaria (reanálisis)
    if "tx" in h:
        tmax = g["tx"].max().where(g["tx"].count() >= MIN_HORAS_EXT)
    else:
        tmax = g["t"].max().where(ok_t)
    if "tn" in h:
        tmin = g["tn"].min().where(g["tn"].count() >= MIN_HORAS_EXT)
    else:
        tmin = g["t"].min().where(ok_t)
    d = pd.DataFrame({
        "tmed": g["t"].mean().where(ok_t), "tmax": tmax, "tmin": tmin,''')

# ------------------------------------------------------------------ 3.2 validación DHIME (antes de la sección 4)
rep('''md(r"""
---
# 4. Corrección de la humedad relativa de ERA5-Land con La Palomera''',
    '''md(r"""
## 3.2 Validación con la serie diaria oficial DHIME (incluye brillo solar)
Esta sección solo corre con los archivos DHIME que haya (sección 1.4). Hace tres cosas:

1. **Consistencia DHIME vs. datos.gov.co.** Es la misma estación, así que deberían coincidir casi perfectamente (r ≈ 1). Las diferencias revelan distinto procesamiento o control de calidad. Se compara con las dos versiones de la automática (con y sin filtro del sensor) y con desfase de 0 y 1 día.
2. **Productos vs. DHIME** a escala diaria, de 8 días y mensual: brillo solar frente a ERA5; T y HR frente a ERA5-Land; lluvia frente a CHIRPS y ERA5.
3. **¿La serie oficial también tiene el problema del sensor?** Se cuentan los días con T media < 20 °C por año.

El desfase importa porque en las estaciones convencionales el "día pluviométrico" va de 7 a. m. a 7 a. m. y puede quedar asignado al día siguiente. Para la lluvia se usa el desfase que mejor coincide con datos.gov.co.
""")
code(r"""
VAR_DHIME = {"bs": "Brillo solar (h/día)", "hr": "HR media (%)", "prec": "Lluvia (mm)",
             "tmax": "T máxima (°C)", "tmin": "T mínima (°C)", "tmed": "T media (°C)"}
idx_dia = pd.date_range(PERIODO[0], PERIODO[1], freq="D", name="fecha")
CONSIST_DHIME, VALID_DHIME, SENSOR_DHIME = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
if pal_dhime.empty:
    print("No hay archivos DHIME de La Palomera: se omite esta sección (ver 1.4).")
else:
    bd = pal_dhime.reindex(idx_dia).join(pal_d).join(pal_d_sf.add_suffix("_sf")).join(prod_pal)

    # 1) Consistencia con la estación automática (datos.gov.co)
    filas = []
    for v in ("tmed", "tmax", "tmin", "hr", "prec"):
        if f"{v}_dhime" not in bd: continue
        for version, cp in (("con filtro", f"{v}_pal"), ("sin filtro", f"{v}_pal_sf")):
            for lag in (0, 1):   # lag 1: el dato DHIME del día d se compara con la automática del día d+1
                filas.append(dict(variable=VAR_DHIME[v], automatica=version, desfase_dias=lag,
                                  **metricas(bd[f"{v}_dhime"], bd[cp].shift(-lag))))
    CONSIST_DHIME = pd.DataFrame(filas).round(3)

    # Desfase de la lluvia: el que da mayor r con la automática
    LAG_PREC_DHIME = 0
    if "prec_dhime" in bd:
        c = CONSIST_DHIME[(CONSIST_DHIME.variable == VAR_DHIME["prec"]) & (CONSIST_DHIME.automatica == "con filtro")]
        LAG_PREC_DHIME = int(c.sort_values("r_pearson").desfase_dias.iloc[-1])
        bd["prec_dhime"] = bd["prec_dhime"].shift(LAG_PREC_DHIME)          # alinea con el día de la automática
        print("Desfase aplicado a la lluvia DHIME:", LAG_PREC_DHIME, "día(s)")

    # 2) Productos vs. DHIME
    COMP_DHIME = [("bs", "bs_era5", "ERA5", False), ("tmed", "tmed_era5", "ERA5-Land", False),
                  ("tmax", "tmax_era5", "ERA5-Land", False), ("tmin", "tmin_era5", "ERA5-Land", False),
                  ("hr", "hr_era5", "ERA5-Land", False), ("prec", "prec_chirps", "CHIRPS", True),
                  ("prec", "prec_era5", "ERA5", True)]
    filas = []
    for ventana, sel in [("Ene–Abr", bd.index.month.isin(VENTANA_MESES)), ("Año completo", slice(None))]:
        sub_d = bd[sel]
        for escala in ["diaria", "8 días", "mensual"]:
            for v, cp, prod, suma in COMP_DHIME:
                cd = f"{v}_dhime"
                if cd not in bd: continue
                a = agregar(sub_d[[cd, cp]], escala, suma)
                filas.append(dict(ventana=ventana, escala=escala, variable=VAR_DHIME[v], producto=prod,
                                  **metricas(a[cd], a[cp])))
    VALID_DHIME = pd.DataFrame(filas).round(3)

    # 3) ¿Tiene la serie oficial el problema del sensor de T?
    if "tmed_dhime" in bd:
        SENSOR_DHIME = pd.DataFrame({
            "dias_T_DHIME": bd["tmed_dhime"].notna().groupby(bd.index.year).sum(),
            "dias_T_DHIME_bajo_20C": bd["tmed_dhime"].lt(20).groupby(bd.index.year).sum(),
            "dias_T_automatica_bajo_20C": bd["tmed_pal_sf"].lt(20).groupby(bd.index.year).sum(),
        }).rename_axis("anio").reset_index()
        print(SENSOR_DHIME.to_string(index=False))
    print("\\nConsistencia DHIME vs. datos.gov.co (desfase 0):")
    print(CONSIST_DHIME[CONSIST_DHIME.desfase_dias == 0][["variable", "automatica", "n", "sesgo", "r_pearson"]].to_string(index=False))
VALID_DHIME[VALID_DHIME.ventana == "Ene–Abr"] if len(VALID_DHIME) else None
""")

md(r"""
### Figura 3.4 – Brillo solar: La Palomera (DHIME) vs. ERA5
Izquierda: ciclo anual medio, solo con los días que tienen las dos fuentes. Derecha: periodos de 8 días de enero–abril. Aparece solo si está el archivo DHIME de brillo solar.
""")
code(r"""
if not pal_dhime.empty and "bs_dhime" in bd:
    b2 = bd[["bs_dhime", "bs_era5"]].dropna()
    cl = b2.groupby(b2.index.month).mean()
    fig, axs = plt.subplots(1, 2, figsize=(11, 3.8))
    ax = axs[0]; ax.axvspan(0.5, 4.5, color="#f0f0f0", zorder=0)
    ax.plot(cl.index, cl.bs_dhime, marker="o", ms=4, color=COL_FUENTE["La Palomera (obs.)"], label="La Palomera (DHIME)")
    ax.plot(cl.index, cl.bs_era5, marker="o", ms=4, color=COL_FUENTE["ERA5"], label="ERA5")
    ax.set_xticks(range(1, 13)); ax.set_xticklabels([MESES[i] for i in range(1, 13)])
    ax.set_ylabel("horas de sol por día"); ax.set_ylim(0, None); ax.legend(); ax.set_title("Ciclo anual medio")
    ax = axs[1]
    a8 = agregar(bd[bd.index.month.isin(VENTANA_MESES)][["bs_dhime", "bs_era5"]], "8 días", False).dropna()
    d1 = bd[bd.index.month.isin(VENTANA_MESES)][["bs_dhime", "bs_era5"]].dropna()
    ax.scatter(d1.bs_dhime, d1.bs_era5, s=6, color="#bdbdbd", alpha=0.5, label="diaria")
    ax.scatter(a8.bs_dhime, a8.bs_era5, s=14, color=COL_FUENTE["ERA5"], label="8 días")
    ax.plot([0, 12], [0, 12], "--", color="#555", lw=1)
    ax.text(0.03, 0.97, f"r diaria = {d1.bs_dhime.corr(d1.bs_era5):.2f}\\nr 8 días = {a8.bs_dhime.corr(a8.bs_era5):.2f}",
            transform=ax.transAxes, va="top", fontsize=8.5)
    ax.set_xlabel("La Palomera, DHIME (h/día)"); ax.set_ylabel("ERA5 (h/día)"); ax.legend(loc="lower right")
    ax.set_title("Enero–abril")
    fig.suptitle("Brillo solar: estación vs. reanálisis", y=1.03)
    guardar(fig, "3_4_brillo_solar_dhime_era5")
else:
    print("Sin archivo DHIME de brillo solar: no se dibuja la figura.")
""")

# =====================================================================================
md(r"""
---
# 4. Corrección de la humedad relativa de ERA5-Land con La Palomera''')

# ------------------------------------------------------------------ 5. base diaria
rep('''| `_era5` | ERA5-Land en el lote sin corregir, + ERA5 | HR sin corregir; lluvia, radiación y ETo de ERA5 |''',
    '''| `_era5` | ERA5-Land en el lote sin corregir, + ERA5 | HR sin corregir; lluvia, radiación, **brillo solar** (`bs_era5`, h/día) y ETo de ERA5 |''')
rep('''| `_pal` | La Palomera observada (a pocos km) | T, HR, horas HR ≥ 90 %, lluvia — **análisis de sensibilidad** |''',
    '''| `_pal` | La Palomera observada (a pocos km) | T, T máx/mín (sensores de extremos), HR, horas HR ≥ 90 %, lluvia — **análisis de sensibilidad** |
| `_dhime` | La Palomera, serie diaria oficial DHIME (si se cargó) | brillo solar, HR, lluvia, T máx, T mín, T media |''')
rep('''D = D.join(pal_d_sf[["tmed_pal", "tmin_pal", "tmax_pal", "dpv_pal"]].add_suffix("_sf"))   # T sin filtro''',
    '''D = D.join(pal_d_sf[["tmed_pal", "tmin_pal", "tmax_pal", "dpv_pal"]].add_suffix("_sf"))   # T sin filtro
D = D.join(pal_dhime)                                     # serie oficial DHIME (puede estar vacía)''')

# ------------------------------------------------------------------ 8. variables de clima
rep('''En cada ventana se calcula: T media, T mínima, horas HR ≥ 90 %, DPV, lluvia total, nº de días lluviosos, y la fracción de días favorables para SALB y para Antracnosis.''',
    '''En cada ventana se calcula: T media, T mínima, T máxima, horas HR ≥ 90 %, DPV, brillo solar, lluvia total, nº de días lluviosos y la fracción de días favorables para SALB y para Antracnosis. El brillo solar se incluye porque la radiación seca la hoja y daña las esporas, y porque marca el paso de la época seca a la lluviosa.''')
rep('''    "T media": ("tmed_era5c", "mean"), "T mínima": ("tmin_era5c", "mean"), "Horas HR≥90 %": ("hr90_horas_era5c", "mean"),
    "DPV": ("dpv_era5c", "mean"), "Lluvia": ("prec_chirps", "sum"), "Días lluviosos": ("lluvia_dia", "sum"),''',
    '''    "T media": ("tmed_era5c", "mean"), "T mínima": ("tmin_era5c", "mean"), "T máxima": ("tmax_era5c", "mean"),
    "Horas HR≥90 %": ("hr90_horas_era5c", "mean"),
    "DPV": ("dpv_era5c", "mean"), "Brillo solar": ("bs_era5", "mean"),
    "Lluvia": ("prec_chirps", "sum"), "Días lluviosos": ("lluvia_dia", "sum"),''')
rep('''    "Días fav. Antracnosis (Palomera sin filtro)": ("clf_fav_pal_sf", "mean"),
}''',
    '''    "Días fav. Antracnosis (Palomera sin filtro)": ("clf_fav_pal_sf", "mean"),
    "Brillo solar (Palomera DHIME)": ("bs_dhime", "mean"),
}
CLIMA_VARS = {k: v for k, v in CLIMA_VARS.items() if v[0] in D}   # quita las que no existen (p. ej. sin DHIME)''')
rep('''    tem = t[t.variable.isin(["T media", "T mínima", "DPV"])]''',
    '''    tem = t[t.variable.isin(["T media", "T mínima", "T máxima", "DPV", "Brillo solar"])]''')
rep('''    ("Lote vs. Palomera", "Días fav. Antracnosis", "Días fav. Antracnosis (Palomera)"),''',
    '''    ("Lote vs. Palomera", "Días fav. Antracnosis", "Días fav. Antracnosis (Palomera)"),
    ("Lote vs. Palomera", "Brillo solar", "Brillo solar (Palomera DHIME)"),''')
rep('''    filas.append(j)
SENS = pd.concat(filas).round(3)''',
    '''    if len(j): filas.append(j)
SENS = pd.concat(filas).round(3)''')

# ------------------------------------------------------------------ 10. exportar
rep('''    ("clima_diario", "Base climática diaria del lote 2011-2025. Sufijos: _era5c ERA5-Land con HR corregida (principal T/HR), _era5 ERA5-Land/ERA5 sin corregir, _chirps CHIRPS (principal lluvia), _pal La Palomera observada.''',
    '''    ("procedencia_datos", "Registro de cada archivo crudo usado: fuente, URL, parámetros de la consulta, fecha de descarga, tamaño y huella SHA-256 (también en datos_crudos/metadatos_descarga.json)."),
    ("versiones_software", "Versiones de Python y librerías con que se ejecutó el cuaderno."),
    ("clima_diario", "Base climática diaria del lote 2011-2025. Sufijos: _era5c ERA5-Land con HR corregida (principal T/HR), _era5 ERA5-Land/ERA5 sin corregir (bs_era5 = brillo solar ERA5, h/día), _chirps CHIRPS (principal lluvia), _pal La Palomera automática (tmax/tmin de sensores de extremos), _dhime La Palomera serie oficial DHIME.''')
rep('''    ("deteccion_lluvia",''',
    '''    ("dhime_inventario", "Archivos DHIME cargados: variable, parámetro, periodo y % de datos por nivel de aprobación."),
    ("consistencia_dhime", "DHIME vs. estación automática de datos.gov.co (misma estación), con y sin filtro del sensor, desfase 0 y 1 día."),
    ("validacion_dhime", "Productos (ERA5, ERA5-Land, CHIRPS) vs. serie diaria oficial DHIME, incluido el brillo solar, por escala y ventana."),
    ("deteccion_lluvia",''')
rep('''    LEEME.to_excel(xw, sheet_name="LEEME", index=False)''',
    '''    LEEME.to_excel(xw, sheet_name="LEEME", index=False)
    PROCEDENCIA.to_excel(xw, sheet_name="procedencia_datos", index=False)
    VERSIONES.to_excel(xw, sheet_name="versiones_software", index=False)
    for nombre, tabla in [("dhime_inventario", DHIME_INV), ("consistencia_dhime", CONSIST_DHIME), ("validacion_dhime", VALID_DHIME)]:
        if len(tabla): tabla.to_excel(xw, sheet_name=nombre, index=False)
    if len(SENSOR_DHIME): SENSOR_DHIME.to_excel(xw, sheet_name="sensor_T_dhime", index=False)''')

# ------------------------------------------------------------------ 10.1 resumen
rep('''q = VALID_QM[VALID_QM.ventana == "Ene–Abr"].set_index("producto")''',
    '''if len(VALID_DHIME):
    vd = VALID_DHIME[VALID_DHIME.ventana == "Ene–Abr"].set_index(["escala", "variable", "producto"])
    for var, prod in [("Brillo solar (h/día)", "ERA5"), ("T máxima (°C)", "ERA5-Land"), ("T mínima (°C)", "ERA5-Land")]:
        if ("diaria", var, prod) in vd.index:
            rr = [vd.loc[(e, var, prod), "r_pearson"] for e in ("diaria", "8 días", "mensual")]
            linea(f"Ene–abr {var} {prod} vs. DHIME: r diaria {rr[0]:.2f} · 8 días {rr[1]:.2f} · mensual {rr[2]:.2f}")
q = VALID_QM[VALID_QM.ventana == "Ene–Abr"].set_index("producto")''')

# ------------------------------------------------------------------ limitaciones + referencias
rep('''6. **Siguientes pasos sugeridos:**''',
    '''6. **Reproducibilidad.** El cuaderno descarga todo desde las fuentes originales (`MODO_DATOS = "descargar"`), salvo DHIME, que se descarga a mano. Los datos usados en el artículo quedan congelados en `datos_crudos/` con su registro SHA-256. Las fuentes se revisan con el tiempo, así que una descarga nueva puede dar cifras algo distintas; por eso conviene depositar la carpeta congelada con DOI (p. ej. Zenodo).
7. **Siguientes pasos sugeridos:**''')
rep('''Funk et al. (2015) CHIRPS; Muñoz-Sabater et al. (2021) ERA5-Land.''',
    '''Funk et al. (2015) CHIRPS; Muñoz-Sabater et al. (2021) ERA5-Land; Hersbach et al. (2020) ERA5; Zippenfenig (2023) Open-Meteo.

**Datos:**
- Funk, C. et al. (2015). The climate hazards infrared precipitation with stations – a new environmental record for monitoring extremes. *Scientific Data* 2, 150066.
- Hersbach, H. et al. (2020). The ERA5 global reanalysis. *Q. J. R. Meteorol. Soc.* 146, 1999–2049.
- Muñoz-Sabater, J. et al. (2021). ERA5-Land: a state-of-the-art global reanalysis dataset for land applications. *Earth Syst. Sci. Data* 13, 4349–4383.
- Zippenfenig, P. (2023). Open-Meteo.com Weather API. Zenodo. doi:10.5281/zenodo.7970649.
- IDEAM. Datos hidrometeorológicos crudos de estaciones automáticas, datos.gov.co (conjuntos uext-mhny, sbwg-7ju4, ccvq-rp9s, afdg-3zpb, s54a-sgyg), y DHIME, estación La Palomera AUT [35185010]. Consulta: ver `metadatos_descarga.json`.''')

RUTA.write_text(s)
print("Parche 3 aplicado.")
