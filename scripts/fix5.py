"""Parche 5: validación regional del brillo solar de ERA5 con la estación Hacienda Las Margaritas."""
from pathlib import Path

RUTA = Path(__file__).with_name("construir_cuaderno.py")
s = RUTA.read_text()


def rep(viejo, nuevo):
    global s
    assert s.count(viejo) == 1, f"{s.count(viejo)} coincidencias: {viejo[:70]!r}"
    s = s.replace(viejo, nuevo)


# ---------------------------------------------------------------- configuración
rep('''PUNTOS = {"sancarlos": LOTE, "palomera": PALOMERA}   # se descargan productos en ambos puntos''',
    '''PUNTOS = {"sancarlos": LOTE, "palomera": PALOMERA}   # se descargan productos en ambos puntos
# Estación de referencia REGIONAL solo para el brillo solar (La Palomera no lo mide).
# Está a ~40 km del lote: se usa para validar ERA5 en su propia celda, no como dato del lote.
MARGARITAS = dict(nombre="Hacienda Las Margaritas AUT [35125010]", codigo="0035125010",
                  lat=4.3698889, lon=-72.2270638)''')
rep('''for c in (CRUDOS / "sancarlos", CRUDOS / "palomera", DHIME_DIR, FIGS):''',
    '''DHIME_MARG = CRUDOS / "margaritas" / "dhime"    # Excel DHIME de brillo solar de Las Margaritas
for c in (CRUDOS / "sancarlos", CRUDOS / "palomera", DHIME_DIR, DHIME_MARG, FIGS):''')
rep('''print(f"Distancia lote San Carlos – La Palomera: {DIST_PAL:.1f} km")''',
    '''print(f"Distancia lote San Carlos – La Palomera: {DIST_PAL:.1f} km")
DIST_MARG = distancia_km(LOTE["lat"], LOTE["lon"], MARGARITAS["lat"], MARGARITAS["lon"])
print(f"Distancia lote San Carlos – Las Margaritas (solo brillo solar): {DIST_MARG:.1f} km")''')

# ---------------------------------------------------------------- 1.1: ERA5 diario en Las Margaritas
rep('''print({k: (v.index.min().date(), v.index.max().date()) for k, v in era5h.items()})
""")''',
    '''print({k: (v.index.min().date(), v.index.max().date()) for k, v in era5h.items()})

# ERA5 diario en la celda de Las Margaritas: solo para validar el brillo solar (sección 3.3)
era5d["margaritas"] = renombrar(open_meteo(MARGARITAS["lat"], MARGARITAS["lon"],
                                           dict(daily="shortwave_radiation_sum,et0_fao_evapotranspiration,precipitation_sum,"
                                                      "sunshine_duration", models="era5"),
                                           CRUDOS / "margaritas" / "era5_diario.csv"),
                                {"shortwave_radiation_sum": "rad", "et0_fao_evapotranspiration": "etp",
                                 "precipitation_sum": "prec", "sunshine_duration": "bs"})
era5d["margaritas"]["bs"] = era5d["margaritas"]["bs"] / 3600
""")''')

# ---------------------------------------------------------------- 1.4: lector DHIME para cualquier estación
rep('''def cargar_dhime():
    carpeta = DHIME_DIR
    archivos = excel_dhime(carpeta)
    if not archivos and MODO_DATOS == "descargar":
        carpeta = CONGELADOS / "palomera" / "dhime"; archivos = excel_dhime(carpeta)''',
    '''def cargar_dhime(carpeta, estacion):
    # Lee los Excel DHIME de 'carpeta' que pertenezcan a 'estacion' (dict con nombre y código)
    archivos = excel_dhime(carpeta) if carpeta.exists() else []
    if not archivos and MODO_DATOS == "descargar":
        carpeta = CONGELADOS / carpeta.relative_to(CRUDOS)
        archivos = excel_dhime(carpeta) if carpeta.exists() else []''')
rep('''        if not any(PALOMERA["codigo"].lstrip("0") in e for e in estaciones):''',
    '''        if not any(estacion["codigo"].lstrip("0") in e for e in estaciones):''')
rep('''        t = t[t.estacion.str.contains(PALOMERA["codigo"].lstrip("0")) & t["var"].notna()]''',
    '''        t = t[t.estacion.str.contains(estacion["codigo"].lstrip("0")) & t["var"].notna()]''')
rep('''                  dict(estacion=PALOMERA["nombre"], variables=sorted(t["var"].unique()),''',
    '''                  dict(estacion=estacion["nombre"], variables=sorted(t["var"].unique()),''')
rep('''            inventario.append(dict(variable=v, archivo=a.name, parametro=g.parametro.iloc[0],''',
    '''            inventario.append(dict(estacion=estacion["nombre"], variable=v, archivo=a.name, parametro=g.parametro.iloc[0],''')
rep('''pal_dhime, DHIME_INV = cargar_dhime()''',
    '''pal_dhime, inv_pal = cargar_dhime(DHIME_DIR, PALOMERA)
marg_dhime, inv_marg = cargar_dhime(DHIME_MARG, MARGARITAS)     # brillo solar regional (sección 3.3)
DHIME_INV = pd.concat([inv_pal, inv_marg], ignore_index=True)
print("Las Margaritas, brillo solar DHIME:", "disponible" if "bs_dhime" in marg_dhime else "no disponible")''')
rep('''faltan = [v for v in ("bs", "hr", "prec", "tmax", "tmin", "tmed") if f"{v}_dhime" not in pal_dhime]
print("Variables DHIME disponibles:", [c.replace("_dhime", "") for c in pal_dhime.columns] or "ninguna")
if faltan:
    print("Faltan en", DHIME_DIR, "→", faltan, "(descárguelas de DHIME siguiendo la tabla de arriba)")''',
    '''print("Variables DHIME de La Palomera:", [c.replace("_dhime", "") for c in pal_dhime.columns] or "ninguna")''')

# ---------------------------------------------------------------- 3.3: nueva sección (reemplaza la figura 3.4 anterior)
i = s.index('md(r"""\n### Figura 3.4 – Brillo solar: La Palomera (DHIME) vs. ERA5')
j = s.index('guardar(fig, "3_4_brillo_solar_dhime_era5")\nelse:\n    print("Sin archivo DHIME de brillo solar: no se dibuja la figura.")\n""")')
j = s.index('""")', j) + len('""")')
s = s[:i] + r'''md(r"""
## 3.3 Brillo solar: validación regional de ERA5 con Hacienda Las Margaritas

**Problema.** La Palomera, la única estación climática cerca del lote, **no mide brillo solar**. La estación más cercana que sí lo mide es **Hacienda Las Margaritas AUT [35125010]** (Puerto López), a ~40 km del lote, en la misma sabana y a una altitud parecida (178 m).

**Qué se hace.** ERA5 se valida **en la celda de Las Margaritas** contra lo que midió esa estación (DHIME, brillo solar total diario). Así la comparación mide el desempeño de ERA5 y no la distancia. Si ERA5 reproduce bien la variación del brillo solar allá, hay respaldo para usar ERA5 en el lote. Además se comprueba si el brillo solar de ERA5 en el lote y en Las Margaritas varía igual (coherencia regional).

**Limitación.** Es una validación **regional, no local**. La nubosidad convectiva puede diferir a 40 km de un día a otro, así que el acuerdo diario esperado es menor que a 8 días o mensual. Las relaciones del brillo solar con la enfermedad se reportan como **exploratorias**.

**Un sesgo constante no afecta la correlación de Spearman**, que solo usa el orden de los valores. Por eso no hace falta corregir el sesgo de ERA5 para las secciones 8 y 9. Lo que importa es que ERA5 siga los cambios de un periodo a otro (r).
""")
code(r"""
VALID_BS = pd.DataFrame()
if "bs_dhime" in marg_dhime:
    bm = pd.DataFrame({"obs": marg_dhime["bs_dhime"], "era5": era5d["margaritas"]["bs"],
                       "era5_lote": era5d["sancarlos"]["bs"]}).reindex(idx_dia)
    filas = []
    for ventana, sel in [("Ene–Abr", bm.index.month.isin(VENTANA_MESES)), ("Año completo", slice(None))]:
        for escala in ["diaria", "8 días", "mensual"]:
            a = agregar(bm[sel][["obs", "era5"]], escala, False)
            filas.append(dict(ventana=ventana, escala=escala, comparacion="ERA5 vs. estación (celda Las Margaritas)",
                              **metricas(a["obs"], a["era5"])))
            c = agregar(bm[sel][["era5", "era5_lote"]], escala, False)
            filas.append(dict(ventana=ventana, escala=escala, comparacion="ERA5 lote vs. ERA5 Las Margaritas (coherencia)",
                              **metricas(c["era5"], c["era5_lote"])))
    VALID_BS = pd.DataFrame(filas).round(3)
    print(f"Las Margaritas: {bm.obs.notna().sum()} días con brillo solar ({bm.obs.first_valid_index():%Y-%m-%d} a "
          f"{bm.obs.last_valid_index():%Y-%m-%d}); distancia al lote {DIST_MARG:.1f} km")
    print(VALID_BS[VALID_BS.ventana == "Ene–Abr"][["escala", "comparacion", "n", "media_obs", "media_prod", "sesgo",
                                                  "r_pearson", "rho_spearman"]].to_string(index=False))
else:
    print("No está el archivo DHIME de brillo solar de Las Margaritas en", DHIME_MARG)
VALID_BS
""")

md(r"""
### Figura 3.4 – Brillo solar: ERA5 vs. Hacienda Las Margaritas
Izquierda: ciclo anual medio de la estación, de ERA5 en su celda y de ERA5 en el lote, solo con días que tienen dato en la estación. Derecha: enero–abril, cada punto es un día (gris) o un periodo de 8 días (color).
""")
code(r"""
if len(VALID_BS):
    b2 = bm.dropna(subset=["obs", "era5"])
    cl = b2.groupby(b2.index.month).mean()
    fig, axs = plt.subplots(1, 2, figsize=(11.5, 3.9))
    ax = axs[0]; ax.axvspan(0.5, 4.5, color="#f0f0f0", zorder=0)
    ax.plot(cl.index, cl.obs, marker="o", ms=4, color="#2b2b2b", label="Las Margaritas (DHIME)")
    ax.plot(cl.index, cl.era5, marker="o", ms=4, color=COL_FUENTE["ERA5"], label="ERA5, celda Las Margaritas")
    ax.plot(cl.index, cl.era5_lote, marker="o", ms=3, ls="--", color="#eb6834", label="ERA5, celda del lote")
    ax.set_xticks(range(1, 13)); ax.set_xticklabels([MESES[i] for i in range(1, 13)])
    ax.set_ylabel("horas de sol por día"); ax.set_ylim(0, None); ax.legend(fontsize=8); ax.set_title("Ciclo anual medio")
    ax = axs[1]
    v = bm[bm.index.month.isin(VENTANA_MESES)]
    d1 = v[["obs", "era5"]].dropna(); a8 = agregar(v[["obs", "era5"]], "8 días", False).dropna()
    ax.scatter(d1.obs, d1.era5, s=6, color="#bdbdbd", alpha=0.5, label="diaria")
    ax.scatter(a8.obs, a8.era5, s=14, color=COL_FUENTE["ERA5"], label="8 días")
    ax.plot([0, 12], [0, 12], "--", color="#555", lw=1)
    ax.text(0.03, 0.97, f"r diaria = {d1.obs.corr(d1.era5):.2f}\nr 8 días = {a8.obs.corr(a8.era5):.2f}",
            transform=ax.transAxes, va="top", fontsize=8.5)
    ax.set_xlabel("Las Margaritas, DHIME (h/día)"); ax.set_ylabel("ERA5 (h/día)"); ax.legend(loc="lower right")
    ax.set_title("Enero–abril")
    fig.suptitle(f"Brillo solar: validación regional de ERA5 (Las Margaritas, a {DIST_MARG:.0f} km del lote)", y=1.03)
    guardar(fig, "3_4_brillo_solar_margaritas_era5")
else:
    print("Sin brillo solar de Las Margaritas: no se dibuja la figura.")
""")''' + s[j:]

# ---------------------------------------------------------------- limitación, exportar y resumen
rep('''El brillo solar viene solo de ERA5 y no se validó localmente; la estación más cercana que lo mide (Hacienda Las Margaritas) está a 39.9 km. Por eso las relaciones con el brillo solar son exploratorias.''',
    '''El brillo solar viene de ERA5 y se validó de forma **regional** con Hacienda Las Margaritas (Puerto López), la estación más cercana que lo mide, a ~40 km del lote (sección 3.3). La validación se hizo en la celda de Las Margaritas, así que mide el desempeño de ERA5 y no el clima del lote. A 40 km la nubosidad diaria puede diferir; por eso las relaciones del brillo solar con la enfermedad son exploratorias.''')
rep('''    ("dhime_inventario", "Archivos DHIME cargados: variable, parámetro, periodo y % de datos por nivel de aprobación."),''',
    '''    ("dhime_inventario", "Archivos DHIME cargados (La Palomera y Las Margaritas): variable, parámetro, periodo y % de datos por nivel de aprobación."),
    ("validacion_brillo_solar", "Brillo solar de ERA5 vs. estación Hacienda Las Margaritas (validación regional, a ~40 km del lote) y coherencia ERA5 lote vs. Las Margaritas."),''')
rep('''("validacion_dhime", VALID_DHIME)]:''',
    '''("validacion_dhime", VALID_DHIME), ("validacion_brillo_solar", VALID_BS)]:''')
rep('''if len(VALID_DHIME):''',
    '''if len(VALID_BS):
    vb = VALID_BS[(VALID_BS.ventana == "Ene–Abr") & VALID_BS.comparacion.str.startswith("ERA5 vs.")].set_index("escala")
    linea(f"Ene–abr brillo solar ERA5 vs. Las Margaritas ({DIST_MARG:.0f} km): r diaria {vb.loc['diaria', 'r_pearson']:.2f} · "
          f"8 días {vb.loc['8 días', 'r_pearson']:.2f} · mensual {vb.loc['mensual', 'r_pearson']:.2f}; "
          f"sesgo {vb.loc['diaria', 'sesgo']:+.1f} h/día")
if len(VALID_DHIME):''')

RUTA.write_text(s)
print("Parche 5 aplicado.")
