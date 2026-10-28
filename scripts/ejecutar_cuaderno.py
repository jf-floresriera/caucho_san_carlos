"""Ejecuta el cuaderno completo en local, guarda las salidas en el mismo archivo
y exporta una copia en HTML (se abre en cualquier navegador, con las figuras incluidas).
Uso (desde san_carlos/):  python scripts/ejecutar_cuaderno.py"""
import time
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter

RUTA = "Analisis_SanCarlos_clima_cultivo.ipynb"
nb = nbformat.read(RUTA, 4)
t0 = time.time()
try:
    NotebookClient(nb, timeout=7200, kernel_name="python3", resources={"metadata": {"path": "."}}).execute()
    print("OK en", round(time.time() - t0), "s")
finally:
    nbformat.write(nb, RUTA)

html, _ = HTMLExporter().from_notebook_node(nb)
with open(RUTA.replace(".ipynb", ".html"), "w", encoding="utf-8") as f:
    f.write(html)
print("HTML guardado:", RUTA.replace(".ipynb", ".html"))
