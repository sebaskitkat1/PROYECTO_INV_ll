# cosecha — tu frutería en números (Escritorio)

App de escritorio en Python + PySide6 para ver ventas, inventario y pronóstico
de una frutería. Los números salen de los datos (dicts de ejemplo hoy, base
de datos después), no hay cifras escritas a mano en las pantallas.

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

## Pruebas

```powershell
python -m unittest discover tests
```

## Estructura

```
main.py
app/
  main_window.py          Ventana y navegación (QStackedWidget + guard de sesión)
  styles.py               Sistema visual cálido (papel, espresso, caramelo)
  data/
    mock_data.py          Datos de ejemplo: frutas, verduras y jugos (listas de dicts)
    store.py              Datos compartidos en memoria (sobrevive a la navegación)
    analytics.py          Cálculos: totales, KPIs, ABC, pronóstico (solo stdlib)
    app_state.py          Sesión: usuario actual
  widgets/
    kpi_card.py           KPI minimalista con píldora de cambio
    nav_bar.py            Topbar 60px + nav segmentada
    mpl_canvas.py         Canvas matplotlib tono papel
  screens/
    login_screen.py       Acceso simple con validación mínima
    dashboard_screen.py   Hoy, KPIs y 2 gráficas
    sales_screen.py       Filtro por categoría, buscador, tabla y dispersión
    inventory_screen.py   Stock editable, alertas y ABC real
    prediction_screen.py  Histórico vs pronóstico 30 días
tests/
  test_inventory_table.py Prueba offscreen: tabla sin corrupción ni cruces
  test_stock_status.py    Prueba: reglas de estado y mock alineado
  test_forecast.py        Prueba: pronóstico, backtest y reparto
```

## Qué hace

- **Acceso:** usuario y contraseña con validación de formato. Entrar con
  Enter funciona. Al salir la sesión se borra y el login vuelve limpio.
  Sin login no se puede entrar a las demás pantallas.
- **Resumen:** KPIs calculados (ventas del último día + variación vs ayer,
  precio por unidad = ingresos/unidades, unidades totales, críticos en
  stock) y top 5 real por ingresos.
- **Ventas:** filtro por categoría (Frutas, Verduras, Jugos) + buscador,
  tabla ordenable y dispersión con el top anotado. El status muestra
  totales del filtro (productos, ingresos y margen ponderado).
- **Inventario:** stock editable con doble clic (decimales en kg/L, enteros
  en pzas), estado recalculado con días de cobertura, resumen y alerta
  desde la lista compartida (no se pierde al navegar), orden de compra
  con cantidad sugerida y Pareto ABC con línea 80%.
- **Pronóstico:** regresión sobre fecha real con nivel en el último punto,
  30 pasos diarios, backtest contra ingenuo y media móvil (si no gana,
  se marca preliminar) y reparto por participación de ingresos.
- **Interfaz:** solo títulos, tablas, gráficas y botones. Sin textos de
  ayuda, sin banners, sin pies de página.

## Lo que sigue

1. Conexión a base de datos (`db_source.py` con la misma forma que `mock_data`;
   `store.py` es el punto de cambio, las pantallas no se tocan).
2. Auth real con hash + roles.
3. Estacionalidad semanal en el pronóstico (con 28+ días de datos).
4. CI + ruff/mypy.
5. Empaquetado con `pyinstaller` desde `main.py`.
