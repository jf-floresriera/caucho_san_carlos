# Lote San Carlos: clima y cultivo de caucho (2016–2020)

Cuaderno principal: [`Analisis_SanCarlos_clima_cultivo.ipynb`](Analisis_SanCarlos_clima_cultivo.ipynb). Funciona en Google Colab y en local, y cada sección está documentada.

## Dos modos de ejecución (celda 0.2, `MODO_DATOS`)

| Modo | Qué hace | Tiempo |
|---|---|---|
| `"reutilizar"` (por defecto) | Usa los datos ya descargados en `datos_crudos/`. Repite exactamente las cifras del análisis. | ~2 min |
| `"descargar"` | Baja **todo** otra vez desde las fuentes originales a `datos_crudos_descarga_AAAA-MM-DD/`. Los resultados van a `resultados_descarga_AAAA-MM-DD/`. No borra nada anterior. | 15–40 min |

DHIME no tiene API, así que en los dos modos se leen los Excel descargados a mano (sección 1.4 del cuaderno).

## Qué subir a Google Drive

```
MyDrive/tapiero/
├── Fenologia_base Orinoquia.xlsx                  ← siempre
└── san_carlos/
    ├── Analisis_SanCarlos_clima_cultivo.ipynb     ← siempre
    └── datos_crudos/
        ├── palomera/dhime/*.xlsx                  ← siempre (descarga manual de DHIME)
        └── (todo lo demás)                        ← solo para modo "reutilizar"
```

- **Para repetir el trabajo ya hecho** (modo `"reutilizar"`): suba la carpeta `san_carlos/datos_crudos/` completa. La carpeta `climate/` **no** hace falta.
- **Para descargar todo de nuevo** (modo `"descargar"`): basta con el Excel de fenología, el cuaderno y `datos_crudos/palomera/dhime/`.

## Archivos DHIME de La Palomera [35185010]

Descárguelos en http://dhime.ideam.gov.co/atencionciudadano/ con frecuencia diaria, de 01/01/2010 a hoy, y guárdelos en `datos_crudos/palomera/dhime/`:

| Archivo | Variable | Parámetro | Estado |
|---|---|---|---|
| `DHIME_HR_LaPalomera.xlsx` | HUM RELATIVA | Humedad relativa media diaria | ✅ ya está (copiado de `climate/`) |
| `DHIME_BS_LaPalomera.xlsx` | BRILLO SOLAR | Brillo solar total diario | ⬜ falta |
| `DHIME_PREC_LaPalomera.xlsx` | PRECIPITACION | Precipitación total diaria | ⬜ falta |
| `DHIME_TMAX_LaPalomera.xlsx` | TEMPERATURA | Temperatura máxima diaria | ⬜ falta |
| `DHIME_TMIN_LaPalomera.xlsx` | TEMPERATURA | Temperatura mínima diaria | ⬜ falta |
| `DHIME_TMED_LaPalomera.xlsx` | TEMPERATURA | Temperatura seca media diaria | ⬜ falta |

Los archivos `Dhime * Las Margaritas.xlsx` de `climate/` son de otra estación (a 39 km) y no sirven aquí, salvo el de HR, que en realidad es de La Palomera. El cuaderno detecta y descarta los archivos de otra estación.

## Salidas
- `resultados/Base_SanCarlos_clima_cultivo.xlsx`: todas las tablas. La hoja LEEME explica cada una; `procedencia_datos` y `versiones_software` documentan los datos y el software.
- `resultados/figuras/*.png`: figuras a 300 dpi.
- `datos_crudos/metadatos_descarga.json`: fuente, URL, parámetros, fecha de descarga y huella SHA-256 de cada archivo crudo.

## Notas
- La Palomera AUT está a 8.6 km del lote.
- **Sensor de T de La Palomera:** en 2011–2012 registró medias de 12–15 °C, lo que es un error del sensor. Se conservan las dos versiones, con y sin filtro (secciones 3.1 y 8.3). No hay días afectados en 2016–2020.
- La T máx/mín de la estación viene de los sensores de extremos de datos.gov.co (`ccvq-rp9s`, `afdg-3zpb`).
- El brillo solar del lote viene de ERA5 (`sunshine_duration`); se valida con DHIME cuando esté el archivo.
- El servidor de CHIRPS de UCSB bloquea la IP si recibe muchas peticiones seguidas. Por eso se usa ClimateSERV, que da valores idénticos.
- Para el artículo: deposite `datos_crudos/` con DOI (p. ej. Zenodo), porque las fuentes se revisan con el tiempo.
