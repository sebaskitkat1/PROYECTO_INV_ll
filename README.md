# cosecha — tu frutería en números (Escritorio)

App de escritorio en Python + PySide6 para ver ventas, inventario y pronóstico
de una frutería. Lee de MySQL si hay conexión y usa el ejemplo si no;
los números salen de los datos, no hay cifras escritas a mano.

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
python -m unittest discover tests   # 41 pruebas
```
Usan datos de ejemplo (`CAFE_DATOS=mock` interno) para ser deterministas,
incluidas las de UI (offscreen, sin ventana).

## Base de datos

```powershell
# 1. Cargar el schema (la base con datos se llama frutidata)
mysql -u root -p < db/frutidata_schema.sql
# 2. Copiar .env.example como .env y poner tus valores (nunca se sube)
# 3. Datos de prueba:  CALL sp_generar_ventas_demo(60);
# 4. Dar de alta tu contraseña:
python -c "import bcrypt; print(bcrypt.hashpw(b'TU_CLAVE', bcrypt.gensalt()).decode())"
#    UPDATE frutidata.usuarios SET password_hash='<hash>' WHERE correo='caja@frutidata.local';
```

Sin MySQL a la mano la app abre igual con el ejemplo. El status de
Ventas indica la fuente ("base de datos" o "ejemplo"). Ver
`db/README_datos.md` para el mapeo vista↔pantalla.

## Simulación con-vs-sin app

```powershell
python scripts/simulacion/run_simulacion.py   # tabla + resultados/utilidad_acumulada.png
```
Walk-forward semanal, políticas de pedido (ojo del dueño vs pronóstico +
newsvendor), inventario FIFO con caducidad real y Monte Carlo con ruido
por día de semana. Detalles y supuestos en `scripts/simulacion/README.md`.

## Estructura

```
main.py
app/
  main_window.py          Ventana y navegación (QStackedWidget + guard de sesión)
  styles.py               Sistema visual fresco (papel, verde, menta)
  data/
    mock_data.py          Datos de ejemplo: frutas, verduras y jugos (listas de dicts)
    store.py              Datos compartidos en memoria (sobrevive a la navegación)
    analytics.py          Cálculos: totales, KPIs, ABC, pronóstico (solo stdlib)
    app_state.py          Sesión: usuario actual
    db.py                 Conexión MySQL desde .env (sin credenciales en código)
    repository.py         Puerta a la base con la forma del mock + auth + kardex
    export_csv.py         Export a CSV legible en Excel (BOM, anti-fórmulas)
  widgets/
    kpi_card.py           KPI minimalista con píldora de cambio
    nav_bar.py            Topbar 60px + nav segmentada
    mpl_canvas.py         Canvas matplotlib tono papel + formato $ miles
    table_items.py        Items que ordenan por valor, no por texto
  screens/
    login_screen.py       Acceso contra usuarios (bcrypt) o modo ejemplo
    dashboard_screen.py   Hoy, KPIs y 2 gráficas
    sales_screen.py       Filtro por categoría, buscador, tabla y dispersión
    inventory_screen.py   Stock editable, alertas, caducidad y ABC real
    prediction_screen.py  Histórico vs pronóstico 30 días
db/
  frutidata_schema.sql    Schema MySQL validado (tablas, vistas, triggers, SP)
  README_datos.md         Mapeo vista↔pantalla y contratos
scripts/
  simulacion/             Walk-forward, newsvendor, FIFO y Monte Carlo + README
tests/
  test_inventory_table.py Tabla sin corrupción ni cruces (F01)
  test_stock_status.py    Reglas de estado y mock alineado (F05)
  test_forecast.py        Pronóstico, backtest y reparto (F02/F06)
  test_repository.py      Mapeo, fallback y auth (rechazo + bitácora)
  test_simulacion.py      FIFO, políticas, walk-forward y newsvendor
  test_ui_fixes.py        Orden numérico, formato miles, export, caducidad
```

## Qué hace

- **Acceso:** contra `usuarios` con bcrypt (bitácora + último acceso); sin
  base entra en modo ejemplo con validación de formato. Enter funciona.
  Al salir la sesión se borra y el login vuelve limpio.
- **Resumen:** KPIs calculados (ventas del último día + variación vs ayer,
  precio por unidad, unidades totales, críticos en stock) y top 5 real.
  Con base, el ticket es real (ventas/tickets con centavos).
- **Ventas:** filtro por categoría (Frutas, Verduras, Jugos) + buscador,
  tabla con orden numérico y por texto sin acentos, dispersión anotada.
  Exporta a CSV que Excel abre bien. El status muestra totales y fuente.
- **Inventario:** stock editable con doble clic (decimales en kg/L, enteros
  en pzas; con base guarda en kardex), estado y cobertura recalculados,
  alerta de críticos + alerta de lotes por caducar con purga, orden de
  compra con cantidad sugerida y Pareto ABC con línea 80%.
- **Pronóstico:** regresión sobre fecha real con nivel en el último punto,
  30 pasos diarios, backtest contra ingenuo y media móvil (si no gana,
  se marca preliminar) y reparto por participación de ingresos.
- **Interfaz:** solo títulos, tablas, gráficas y botones. Sin textos de
  ayuda, sin banners, sin pies de página.

## Lo que sigue

1. Estacionalidad semanal en el pronóstico (entra sola con 28+ días).
2. Roles visibles en UI (cajero sin compras/pronóstico) + bitácora consultable.
3. Umbrales desde `parametros_sistema` en vez de hardcodeados.
4. CI + ruff/mypy.
5. Empaquetado con `pyinstaller` desde `main.py`.
