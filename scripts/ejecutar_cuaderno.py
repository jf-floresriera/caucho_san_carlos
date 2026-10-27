"""Ejecuta el cuaderno completo en local y guarda las salidas dentro del mismo archivo.
Uso (desde san_carlos/):  python scripts/ejecutar_cuaderno.py"""
import time
import nbformat
from nbclient import NotebookClient

RUTA = "Analisis_SanCarlos_clima_cultivo.ipynb"
nb = nbformat.read(RUTA, 4)
t0 = time.time()
try:
    NotebookClient(nb, timeout=7200, kernel_name="python3", resources={"metadata": {"path": "."}}).execute()
    print("OK en", round(time.time() - t0), "s")
finally:
    nbformat.write(nb, RUTA)
