<div align="center">

<img src="assets/readme/banner.svg" alt="caucho_san_carlos — Clima y enfermedades foliares del caucho, lote San Carlos" width="100%">

<p>
  <a href="https://colab.research.google.com/github/jf-floresriera/caucho_san_carlos/blob/main/Analisis_SanCarlos_clima_cultivo.ipynb"><img src="https://img.shields.io/badge/Abrir_en-Colab-1baf7a?style=for-the-badge&logo=googlecolab&logoColor=white&labelColor=0f1f17" alt="Abrir en Colab"></a>
  <img src="https://img.shields.io/badge/Python-3.12-1baf7a?style=for-the-badge&logo=python&logoColor=white&labelColor=0f1f17" alt="Python 3.12">
  <img src="https://img.shields.io/badge/ERA5--Land-ECMWF-1baf7a?style=for-the-badge&labelColor=0f1f17" alt="ERA5-Land">
  <img src="https://img.shields.io/badge/CHIRPS-v2.0-1baf7a?style=for-the-badge&labelColor=0f1f17" alt="CHIRPS v2.0">
  <img src="https://img.shields.io/badge/IDEAM-La_Palomera-1baf7a?style=for-the-badge&labelColor=0f1f17" alt="IDEAM La Palomera">
  <img src="https://img.shields.io/badge/reproducible-SHA--256-9be15d?style=for-the-badge&labelColor=0f1f17" alt="Reproducible">
</p>

</div>

<img src="assets/readme/divider.svg" alt="" width="100%">

# 🌳 Resumen

Análisis del clima del **lote San Carlos** (4°11'15.52" N, 72°32'14.55" O; San Carlos de Guaroa, Meta) y su relación con la fenología y las enfermedades foliares del caucho (*Hevea brasiliensis*). Se estudian los clones **FX 3864**, **IAN 873** y **RRIM 600** (96 árboles, 2016–2020), con énfasis en **enero–abril**: defoliación invernal → refoliación → maduración de la hoja.

Preguntas que responde el cuaderno:

| # | Pregunta | Sección |
|---|---|---|
| 1 | ¿Se pueden correlacionar los datos de la estación IDEAM **La Palomera** con **CHIRPS** y **ERA5** de enero a abril? | 3 |
| 2 | ¿La información **cada 8 días** presenta cambios? | 6 |
| 3 | ¿Cómo evolucionan la **incidencia** de SALB y Antracnosis en los campos clonales, y qué clima la explica? | 7–8 |

### 📍 Lote y estación de referencia

| | Latitud | Longitud |
|---|---|---|
| **Lote San Carlos** | 4°11'15.52" N | 72°32'14.55" O |

**La Palomera AUT [35185010]** está a **8.6 km** y es la **única estación climática activa cerca del lote**. Según el catálogo del IDEAM, la siguiente estación con temperatura y humedad está a casi 40 km (Hacienda Las Margaritas). Las intermedias son pluviométricas, limnimétricas o están suspendidas. Por eso La Palomera es la referencia observada para validar los productos y corregir la humedad.

| Estación | Categoría | Estado | Distancia |
|---|---|---|---|
| **La Palomera AUT** | Agrometeorológica, automática | Activa | **8.6 km** |
| Fundo Nuevo Humapo | Pluviométrica | Activa | 22.5 km |
| Cabuyaro | Meteorológica especial | Suspendida | 30.3 km |
| Lajitas | Climatológica ordinaria | Suspendida | 38.4 km |
| Hacienda Las Margaritas AUT | Climatológica principal | Activa | 39.9 km |

Todo está en un solo cuaderno documentado celda por celda: [`Analisis_SanCarlos_clima_cultivo.ipynb`](Analisis_SanCarlos_clima_cultivo.ipynb).

<img src="assets/readme/divider.svg" alt="" width="100%">

# 🛰️ Aportes y resultados

### 1 · Validación de los productos con La Palomera (enero–abril)

La estación está a **8.6 km** del lote. A escala diaria el acuerdo es moderado. Al agregar a **8 días** o a un **mes**, la humedad y la lluvia mejoran mucho. La lluvia diaria casi nunca coincide entre satélite y pluviómetro, porque las tormentas convectivas son muy locales.

<div align="center"><img src="assets/readme/escalas.svg" alt="r por escala de agregación" width="100%"></div>

<details><summary>📊 Ver figuras de la validación</summary>

![Dispersión estación vs producto](resultados/figuras/3_1_dispersion_validacion_ene_abr.png)
![Correlación por escala](resultados/figuras/3_2_correlacion_por_escala.png)
![Disponibilidad de datos](resultados/figuras/2_1_disponibilidad_palomera.png)
</details>

### 2 · Brillo solar: validación regional con Las Margaritas

La Palomera **no mide brillo solar**. Por eso ERA5 se validó en la celda de **Hacienda Las Margaritas AUT [35125010]** (Puerto López), la estación más cercana que lo mide, a **39.9 km** del lote.

| Enero–abril | r diaria | r 8 días | r mensual | Sesgo |
|---|---|---|---|---|
| ERA5 vs. Las Margaritas | 0.41 | 0.43 | 0.26 | **+5.1 h/día** |

- ✅ ERA5 reproduce el **ciclo estacional**: enero–febrero es lo más soleado y junio–julio lo menos.
- ❌ Sobreestima unas 5 h y muchas veces se queda pegado cerca de 12 h, el máximo posible. Sigue poco las diferencias entre días y entre años.
- ⚠️ **Limitación:** es una validación **regional (40 km), no local**. Las relaciones del brillo solar con la enfermedad son **exploratorias**.

![Brillo solar ERA5 vs Las Margaritas](resultados/figuras/3_4_brillo_solar_margaritas_era5.png)

### 3 · Problema del sensor de temperatura de La Palomera

En **2011–2012** el sensor registró medias diarias de **12–15 °C**, imposibles en los Llanos. Se conservan **las dos versiones**, con y sin filtro, y se documenta el efecto:

| | r T media vs. ERA5-Land (ene–abr, diaria) |
|---|---|
| Sin filtro | 0.27 |
| Con filtro | **0.56** |

En los años del cultivo (2016–2020) no hay días afectados, así que la relación con el cultivo no cambia (Δρ = 0). La serie oficial de DHIME permite comprobar si el IDEAM ya corrigió esos días.

![Sensor de T](resultados/figuras/3_3_sensor_T_palomera.png)

### 4 · Corrección de la humedad de ERA5-Land

ERA5-Land da noches demasiado secas. Con un **mapeo de cuantiles** por mes y bloque de 3 horas, entrenado con La Palomera y validado de forma cruzada por años, el sesgo de las horas con HR ≥ 90 % en enero–abril pasa de **−6.0 a +1.1 h/día**.

![Corrección HR](resultados/figuras/4_1_correccion_hr_mensual.png)

### 5 · ¿Cambia el clima cada 8 días?

**Sí, para la temperatura, la humedad y el DPV.** El periodo de 8 días explica entre el 57 % y el 71 % de la varianza (η²), y entre el 27 % y el 42 % de los pasos de un periodo al siguiente son significativos (Mann–Whitney; por azar se esperaría ~5 %). La lluvia es más errática: η² = 0.29 y solo el 8 % de los pasos son significativos.

![Periodos de 8 días](resultados/figuras/6_1_boxplot_periodos_8dias.png)

<details><summary>📊 Climatología del lote y enero–abril por años</summary>

![Climatología](resultados/figuras/5_1_climatologia_lote.png)
![Ene–abr por periodos de 8 días](resultados/figuras/5_2_ene_abr_periodos_8dias.png)
</details>

### 6 · Incidencia de enfermedades en los campos clonales

Para cada clon y fecha se calculan la incidencia, la severidad y el índice de McKinney, junto con los estados de la hoja (A, B, C, D), el área bajo la curva de progreso de la enfermedad (ABCPE), la necromasa y el LAI.

![Serie del cultivo por clon](resultados/figuras/7_1_serie_cultivo_clones.png)

<details><summary>📊 ABCPE, necromasa y LAI</summary>

![ABCPE por clon](resultados/figuras/7_2_abcpe_clones.png)
![Necromasa y LAI](resultados/figuras/7_3_necromasa_lai.png)
</details>

### 7 · Clima × enfermedad

- **Antracnosis:** la incidencia sube con la **temperatura de 25–32 días antes** (ρ = +0.55; p_FDR = 0.051, en el límite). En el modelo GEE a nivel de árbol:
  - una desviación estándar más de T media en esa ventana multiplica las probabilidades de que el árbol esté enfermo por **OR = 2.05**;
  - **IAN 873** es el clon menos afectado (OR = 0.47).
- **SALB:** **RRIM 600** concentra la enfermedad (OR = 22). Los días favorables a SALB de 9–16 días antes aumentan el riesgo (OR = 1.42).
- Con 3 temporadas (2018–2020), los resultados son **exploratorios**.

![Mapa de correlaciones](resultados/figuras/8_1_mapa_correlaciones.png)
![GEE](resultados/figuras/8_2_gee_odds_ratios.png)

### 8 · Secuencia anual: clima → caída de hojas → brotación → enfermedad

![Ciclo anual integrado](resultados/figuras/9_1_ciclo_anual_integrado.png)

<img src="assets/readme/divider.svg" alt="" width="100%">

# 🔁 Reproducibilidad

El cuaderno contiene **toda la metodología de descarga**. En la celda 0.2 se elige el modo:

| `MODO_DATOS` | Qué hace | Tiempo |
|---|---|---|
| `"reutilizar"` *(por defecto)* | Usa los datos congelados de [`datos_crudos/`](datos_crudos/) y reproduce exactamente las cifras de este repositorio. | ~2 min |
| `"descargar"` | Baja **todo** otra vez desde las fuentes originales a `datos_crudos_descarga_AAAA-MM-DD/`, sin borrar nada. | 15–40 min |

Cada archivo queda registrado en [`datos_crudos/metadatos_descarga.json`](datos_crudos/metadatos_descarga.json) con:
- fuente, URL y parámetros exactos de la consulta;
- fecha de descarga;
- celda del modelo;
- huella **SHA-256**.

| Fuente | Acceso | Variables |
|---|---|---|
| ERA5-Land (ECMWF/Copernicus) | API Open-Meteo, `models=era5_land` | T, HR, punto de rocío (horario, 9 km) |
| ERA5 | API Open-Meteo, `models=era5` | lluvia, radiación, **brillo solar**, ETo (diario) |
| CHIRPS v2.0 | API ClimateSERV | lluvia (diaria, 5 km) |
| IDEAM La Palomera AUT [35185010] | datos.gov.co (`uext-mhny`, `sbwg-7ju4`, `ccvq-rp9s`, `afdg-3zpb`, `s54a-sgyg`) | HR, T, T máx, T mín, lluvia |
| IDEAM DHIME | descarga manual (no tiene API) | HR diaria oficial (La Palomera no reporta brillo solar ni lluvia en DHIME) |

### ¿Qué subir a Google Drive para usarlo en Colab?

```
MyDrive/tapiero/
├── Fenologia_base Orinoquia.xlsx                  ← siempre (no está en este repositorio)
└── san_carlos/                                    ← este repositorio
    ├── Analisis_SanCarlos_clima_cultivo.ipynb
    └── datos_crudos/
        ├── palomera/dhime/DHIME_HR_LaPalomera.xlsx  ← ya incluido
        └── (resto)                                ← solo para el modo "reutilizar"
```

> 🔒 **Los datos de campo** (`Fenologia_base Orinoquia.xlsx`) no se publican aquí hasta que salga el artículo. Hay que ponerlos en la carpeta **padre** del repositorio.

### ¿Qué registra La Palomera?

Revisado en datos.gov.co y en [DHIME](http://dhime.ideam.gov.co/atencionciudadano/) el 27-oct-2026:

| Variable | Sensores automáticos (datos.gov.co) | DHIME (diaria oficial) |
|---|---|---|
| Humedad relativa | ✅ horaria | ✅ (en `datos_crudos/palomera/dhime/`) |
| Temperatura media, máxima y mínima | ✅ horaria | no se usa |
| Precipitación | ✅ cada 10 min, desde 2017 | ❌ no la reporta |
| Brillo solar | ❌ | ❌ la estación no lo registra |

- **Lluvia:** se usa el pluviómetro automático, que cubre todos los años del cultivo. *Día pluviométrico*, total mensual y total anual son parámetros DHIME de estaciones convencionales y no existen para La Palomera.
- **Brillo solar:** se usa ERA5, validado de forma **regional** con Hacienda Las Margaritas (Puerto López, a 39.9 km), cuyo Excel DHIME está en `datos_crudos/margaritas/dhime/`. Ver el aporte 2.

<img src="assets/readme/divider.svg" alt="" width="100%">

# 🗂️ Estructura

```
Analisis_SanCarlos_clima_cultivo.ipynb   cuaderno principal (Colab o local), con salidas
datos_crudos/                            datos congelados + metadatos_descarga.json
  sancarlos/  palomera/  margaritas/  chirps_diario.csv
resultados/
  Base_SanCarlos_clima_cultivo.xlsx      todas las tablas (hoja LEEME)
  figuras/                               figuras PNG a 300 dpi
scripts/
  construir_cuaderno.py                  genera el cuaderno (fuente del texto y el código)
  ejecutar_cuaderno.py                   lo ejecuta en local
  descargar_socrata_reanudable.py        descarga de datos.gov.co año por año, reanudable
  fix3.py … fix5.py                      parches aplicados (trazabilidad de los cambios)
assets/readme/                           banner y gráficos animados de este README
```

**En local:**
```bash
pip install pandas numpy scipy statsmodels matplotlib requests openpyxl nbformat nbclient ipykernel
python scripts/construir_cuaderno.py Analisis_SanCarlos_clima_cultivo.ipynb   # (opcional) regenerar
python scripts/ejecutar_cuaderno.py
```

<img src="assets/readme/divider.svg" alt="" width="100%">

# 🧭 Historial

| Versión | Cambios |
|---|---|
| **v2** | Análisis base: validación ene–abr, corrección de HR, cambios cada 8 días, clima × enfermedad, problema del sensor de T. |
| **v3** | Protocolo de descarga reproducible (modos, SHA-256), T máx/mín de sensores de extremos, brillo solar, lector y validación DHIME, descarga reanudable de datos.gov.co. |
| **v3.1** | La Palomera es la única estación climática cerca del lote; validación regional del brillo solar de ERA5 con Hacienda Las Margaritas (40 km). |

Al agregar T máxima y brillo solar crece el número de pruebas. Por eso los p_FDR de la v3 difieren algo de los de la v2: el mejor pasa de ≈ 0.066 a 0.051. Los ρ no cambian.

<img src="assets/readme/divider.svg" alt="" width="100%">

# 📚 Referencias

- Funk, C. et al. (2015). *Scientific Data* 2, 150066. CHIRPS.
- Hersbach, H. et al. (2020). *Q. J. R. Meteorol. Soc.* 146, 1999–2049. ERA5.
- Muñoz-Sabater, J. et al. (2021). *Earth Syst. Sci. Data* 13, 4349–4383. ERA5-Land.
- Zippenfenig, P. (2023). Open-Meteo.com Weather API. Zenodo, doi:10.5281/zenodo.7970649.
- Métodos: McKinney (1923); Shaner & Finney (1977); Liang & Zeger (1986); Benjamini & Hochberg (1995); Themeßl et al. (2011); Hallé et al. (1978).

Trabajo relacionado: [hevea-agroclima-salb-clf](https://github.com/jf-floresriera/hevea-agroclima-salb-clf) (Las Delicias y C.I. Taluma).

<div align="center">
<br>
<img src="assets/readme/logo-unal.png" alt="Universidad Nacional de Colombia" height="56">
<br><sub>Jesús Enrique Flores Riera · Universidad Nacional de Colombia</sub>
</div>
