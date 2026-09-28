
App de escritorio en Python + PySide6 para ver ventas, inventario y pronóstico
sin pelearte con hojas de cálculo. Funciona con datos de ejemplo y, si cargas
un CSV, lo usa de verdad en resumen y ventas.

Rama actual: `muse-spark/mejoras-p1` — prototipo V2 con UI cálida minimalista
y corrección de errores de la V1.

## Instalación

Requiere Python 3.10+.

```powershell
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

#
