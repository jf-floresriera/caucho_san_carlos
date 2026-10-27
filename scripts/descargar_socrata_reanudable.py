"""Descarga una variable de La Palomera (datos.gov.co) año por año, reanudable.
Cada año queda en datos_crudos/palomera/_<var>_por_anio/<año>.csv; si el proceso se corta,
al volver a ejecutarlo solo baja los años que faltan. Al final une todo en ideam_aut_<var>_crudo.csv.
Usa la misma función socrata() del cuaderno.
Uso (desde san_carlos/):  python scripts/descargar_socrata_reanudable.py t
"""
import io, sys, time
from datetime import datetime
from pathlib import Path
import nbformat, pandas as pd, requests

var = sys.argv[1] if len(sys.argv) > 1 else "t"
nb = nbformat.read("Analisis_SanCarlos_clima_cultivo.ipynb", 4)
celda = next(c.source for c in nb.cells if c.cell_type == "code" and "def socrata(" in c.source)
g = {"io": io, "time": time, "requests": requests, "pd": pd, "datetime": datetime}
exec(celda.split("def palomera_cruda")[0], g)              # define URL_SOC, DS_IDEAM, socrata()
ds = g["DS_IDEAM"][var][0]

carpeta = Path(f"datos_crudos/palomera/_{var}_por_anio"); carpeta.mkdir(parents=True, exist_ok=True)
for anio in range(2005, datetime.now().year + 1):
    f = carpeta / f"{anio}.csv"
    if f.exists():
        continue
    d = g["socrata"](ds, "0035185010", anios=[anio])
    d.to_csv(f.with_suffix(".part"), index=False); f.with_suffix(".part").replace(f)
todo = pd.concat([pd.read_csv(f) for f in sorted(carpeta.glob("*.csv"))], ignore_index=True)
destino = Path(f"datos_crudos/palomera/ideam_aut_{var}_crudo.csv")
todo.to_csv(destino, index=False)
print("Listo:", destino, len(todo), "registros")
