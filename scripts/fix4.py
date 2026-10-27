"""Parche 4: descarga Socrata por años, con reintentos y verificación de la respuesta."""
from pathlib import Path
RUTA = Path(__file__).with_name("construir_cuaderno.py")
s = RUTA.read_text()
viejo = s[s.index("def socrata(ds, codigo, lote=500000):"):s.index("def palomera_cruda(var):")]
nuevo = '''def socrata(ds, codigo, anios=range(2005, datetime.now().year + 1), lote=200000):
    # Descarga año por año (consultas pequeñas: el servidor corta las consultas grandes con "Timeout")
    # y, dentro de cada año, por páginas de 'lote' filas. Reintenta hasta 5 veces si el servidor falla.
    partes = []
    for anio in anios:
        offset = 0
        while True:
            q = {**consulta_socrata(codigo), "$limit": lote, "$offset": offset}
            q["$where"] += f" AND fechaobservacion >= '{anio}-01-01T00:00:00' AND fechaobservacion < '{anio + 1}-01-01T00:00:00'"
            for intento in range(5):
                try:
                    r = requests.get(URL_SOC.format(ds=ds), params=q, timeout=900)
                    if r.status_code == 200 and r.text.startswith('"fechaobservacion"'):   # respuesta CSV válida
                        break
                    motivo = f"HTTP {r.status_code}: {r.text[:80]!r}"
                except requests.RequestException as e:
                    motivo = str(e)[:80]
                print(f"   {ds} {anio}: falló ({motivo}); reintento {intento + 1}/5")
                time.sleep(30 * (intento + 1))
            else:
                raise RuntimeError(f"datos.gov.co no respondió para {ds} {anio}")
            df = pd.read_csv(io.StringIO(r.text)); partes.append(df)
            if len(df) < lote: break
            offset += lote
        print(f"   {ds} {anio}: {sum(len(p) for p in partes):,} registros acumulados")
    return pd.concat(partes, ignore_index=True)

'''
s = s.replace(viejo, nuevo)
s = s.replace("""    if nuevo:
        socrata(ds, PALOMERA["codigo"]).to_csv(ruta, index=False)""",
"""    if nuevo:   # se escribe primero a .part para no dejar un archivo a medias si se corta
        socrata(ds, PALOMERA["codigo"]).to_csv(ruta.with_suffix(".part"), index=False)
        ruta.with_suffix(".part").replace(ruta)""")
assert "anios=range(2005" in s and ".part" in s
RUTA.write_text(s)
print("Parche 4 aplicado.")
