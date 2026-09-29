# cafédata — tu café en números (Escritorio)

App de escritorio en Python + PySide6 para ver ventas, inventario y pronóstico.
Los números salen de los datos (dicts de ejemplo hoy, base de datos después),
no hay cifras escritas a mano en las pantallas.

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

## Estructura

```
main.py
app/
  main_window.py          Ventana y navegación (QStackedWidget + guard de sesión)
  styles.py               Sistema visual cálido (papel, espresso, caramelo)
  data/
    mock_data.py          Datos de ejemplo (listas de dicts)
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
```

## Qué hace

- **Acceso:** usuario y contraseña con validación de formato. Entrar con
  Enter funciona. Al salir la sesión se borra y el login vuelve limpio.
  Sin login no se puede entrar a las demás pantallas.
- **Resumen:** KPIs calculados (ventas del último día + variación vs ayer,
  ticket = ingresos/unidades, unidades totales, críticos en stock) y top 5
  real por ingresos.
- **Ventas:** filtro por categoría + buscador, tabla ordenable y dispersión
  con el top anotado. El status muestra totales del filtro
  (productos, ingresos y margen ponderado).
- **Inventario:** stock editable con doble clic, estado recalculado,
  resumen y alerta desde la lista compartida (no se pierde al navegar),
  orden de compra con cantidad sugerida y Pareto ABC con línea 80%.
- **Pronóstico:** futuro = promedio de últimos 3 + pendiente de la recta,
  repartido por producto según margen. Método simple y visible en el código.
- **Interfaz:** solo títulos, tablas, gráficas y botones. Sin textos de
  ayuda, sin banners, sin pies de página.

## Lo que sigue

1. Conexión a base de datos (`db_source.py` con la misma forma que `mock_data`;
   `store.py` es el punto de cambio, las pantallas no se tocan).
2. Auth real con hash + roles.
3. Backtesting y estacionalidad en el pronóstico.
4. Tests de humo + CI.
5. Empaquetado con `pyinstaller` desde `main.py`.
