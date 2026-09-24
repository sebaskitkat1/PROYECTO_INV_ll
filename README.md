# cafédata 

App de escritorio en Python + PySide6 para ver ventas, inventario y pronóstico
sin pelearte con hojas de cálculo. Funciona con datos de ejemplo y, si cargas
un CSV, lo usa de verdad en resumen y ventas.

Rama actual: `muse-spark/mejoras-p1` — prototipo V2 con UI cálida minimalista
y corrección de errores de la V1.

## Instalación

Requiere Python 3.10+.

```powershell
cd "C:\Users\fcoan\Downloads\CafeData-Desktop\CafeData-Desktop"
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecución

```powershell
python main.py
```

Sin CSV entra con datos de ejemplo. Con CSV (`Login > Cargar CSV`) el resumen
y ventas calculan desde tu archivo.

Formato CSV esperado (nombres flexibles, minúsculas):
`nombre / producto`, `cantidad`, `total / ingresos / ventas / monto`,
opcional `categoria`, `margen`, `precio`, `fecha`.

## Estructura

```
main.py
app/
  main_window.py          Ventana y navegación (QStackedWidget)
  styles.py               Sistema visual cálido (papel, espresso, caramelo)
  data/
    mock_data.py          Datos de ejemplo
    app_state.py          Sesión: df, usuario, última carga (singleton)
  widgets/
    kpi_card.py           KPI minimalista con píldora de cambio
    nav_bar.py            Topbar 60px + nav segmentada
    mpl_canvas.py         Canvas matplotlib tono papel
  screens/
    login_screen.py       Acceso + carga CSV con validación
    dashboard_screen.py   Hoy, KPIs y 2 gráficas
    sales_screen.py       Filtros, buscador, tabla y dispersión
    inventory_screen.py   Stock editable, alertas y ABC real
    prediction_screen.py  Histórico vs pronóstico 30 días
```

## Qué hace la V2

- **Sesión real:** `AppState` guarda el CSV y el usuario. Ya no se pierde
  el DataFrame del login. El footer muestra la fuente (`ejemplo` o `tu.csv (N filas)`).
- **Resumen:** si hay CSV, ventas hoy, ticket y conteo salen de tu columna
  `total/ingresos/ventas`; si no, usa el ejemplo.
- **Ventas:** filtro por categoría + buscador que sí filtran tabla y gráfica,
  tabla ordenable, exportación del filtrado a CSV, dispersión con top anotado.
  Categorías del ejemplo: Bebidas / Alimentos / Postres. Período cableado
  para CSV con fecha.
- **Inventario:** stock actual/mínimo editable con doble clic, estado
  recalculado (`critico < minimo`, `advertencia < minimo*1.25`), resumen y
  alerta `X por pedir` al día, orden de compra en CSV, restablecer a ejemplo.
  Sorting numérico real, rotación con alta rotación marcada y Pareto ABC con
  % acumulado, línea 80% y clases A/B/C.
- **Pronóstico:** serie ordenada sin duplicados ni espacios
  (`25 Sep … Hoy … 25 Oct`), línea histórica espresso + pronóstico caramelo
  punteado, tabla con `+X%` en salvia.
- **UI nueva:** papel `#F7F3ED`, tinta espresso, acento caramelo. Sin azul
  `#1F4E78`, sin mayúsculas gritadas, sin iconos unicode. Topbar fina,
  nav en píldora, cards radio 14px sin sombra, tablas con hairline cálida,
  botones 34px en sentence case.

## Lo que sigue

1. Auth real con hash + roles (hoy solo valida no vacío).
2. Filtro por fecha real en ventas cuando el CSV traiga `fecha`.
3. Modelo de pronóstico sobre tu CSV (promedio móvil / regresión).
4. Módulo `db_source.py` para MySQL/Postgres con la misma interfaz que `mock_data`.
5. Empaquetado con `pyinstaller` desde `main.py`.
