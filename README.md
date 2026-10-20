# cosecha — tu frutería en números (Escritorio)

App de escritorio en Python + PySide6 para ver ventas, inventario y pronóstico
de una frutería. Lee de MySQL si hay conexión y usa el ejemplo si no;
los números salen de los datos, no hay cifras escritas a mano.

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
cd "C:\Users\fcoan\Downloads\CafeData-Desktop\CafeData-Desktop"
python main.py
```

## Pruebas y calidad

```powershell
python -m unittest discover tests   # 67 pruebas
python -m ruff check .
python -m mypy app/data
```
Las pruebas usan datos de ejemplo (`CAFE_DATOS=mock` interno) para ser
deterministas, incluidas las de UI (offscreen, sin ventana). CI corre lo
mismo en `.github/workflows/ci.yml`.

## Empaquetado

```powershell
pip install -r requirements-dev.txt
.\scripts\build.ps1
# queda en dist\cosecha\cosecha.exe
```
Copia tu `.env` junto al `.exe` (la app lo busca ahí primero). El build
usa `cosecha.spec` y `main.py` como entrada.

## Base de datos

```powershell
# 1. Cargar el schema (la base con datos se llama frutidata)
mysql -u root -p < db/frutidata_schema.sql
#    Si la base ya existe, aplicar solo la migración de compras:
mysql -u root -p < db/migrate_ordenes_pendientes.sql
# 2. Copiar .env.example como .env y poner tus valores (nunca se sube)
# 3. Datos de prueba:  CALL sp_generar_ventas_demo(60);
# 4. Dar de alta tu contraseña:
python -c "import bcrypt; print(bcrypt.hashpw(b'TU_CLAVE', bcrypt.gensalt()).decode())"
#    UPDATE frutidata.usuarios SET password_hash='<hash>' WHERE correo='caja@frutidata.local';
```

Los umbrales de inventario (advertencia, reorden, caducidad, días de
alerta y cortes ABC) se leen de `parametros_sistema`; sin base se usan
los mismos valores por defecto. Los roles salen de `roles`:
Administrador ve todo y consulta la bitácora; Gerente no ve bitácora;
Cajero no ve pronóstico ni compras.

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
    app_state.py          Sesión: usuario, rol y sucursal actuales
    roles.py              Permisos por rol (admin, gerente, cajero)
    params.py             Umbrales por defecto y parseo de parametros_sistema
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
    purchases_screen.py   Órdenes de compra, detalle y recepción
    prediction_screen.py  Histórico vs pronóstico 30 días
    bitacora_screen.py    Accesos consultables (solo Administrador)
db/
  frutidata_schema.sql    Schema MySQL validado (tablas, vistas, triggers, SP)
  migrate_ordenes_pendientes.sql  Vista de compras sin pedidos duplicados
  README_datos.md         Mapeo vista↔pantalla y contratos
scripts/
  build.ps1               Empaquetado con PyInstaller (cosecha.spec)
  simulacion/             Walk-forward, newsvendor, FIFO y Monte Carlo + README
tests/
  test_inventory_table.py Tabla sin corrupción ni cruces (F01)
  test_stock_status.py    Reglas de estado y mock alineado (F05)
  test_forecast.py        Pronóstico, backtest y reparto (F02/F06)
  test_repository.py      Mapeo, fallback y auth (rechazo + bitácora)
  test_roles.py           Permisos, nav filtrada, compras y bitácora
  test_orders.py          Órdenes de compra: mapeo, detalle y ejemplo
  test_params.py          Umbrales desde parametros_sistema y defaults
  test_simulacion.py      FIFO, políticas, walk-forward y newsvendor
  test_ui_fixes.py        Orden numérico, formato miles, export, caducidad
cosecha.spec              Receta de PyInstaller
pyproject.toml            Configuración de ruff y mypy
requirements-dev.txt      Dependencias de desarrollo y build
.github/workflows/ci.yml  CI: ruff, mypy y pruebas
```

## Qué hace

- **Acceso:** contra `usuarios` con bcrypt (bitácora + último acceso); sin
  base entra en modo ejemplo con validación de formato. Enter funciona.
  Al salir la sesión se borra y el login vuelve limpio. El rol se muestra
  en la barra y filtra la navegación.
- **Bitácora:** pantalla de accesos (fecha, usuario, correo, resultado y
  equipo) visible para Administrador, con botón para actualizar.
- **Resumen:** KPIs calculados (ventas del último día + variación vs ayer,
  precio por unidad, unidades totales, críticos en stock) y top 5 real.
  Con base, el ticket es real (ventas/tickets con centavos).
- **Ventas:** filtro por categoría (Frutas, Verduras, Jugos) + buscador,
  tabla con orden numérico y por texto sin acentos, dispersión anotada.
  Exporta a CSV que Excel abre bien. El status muestra totales y fuente.
- **Inventario:** stock editable con doble clic (decimales en kg/L, enteros
  en pzas; con base guarda en kardex), estado y cobertura recalculados con
  umbrales de `parametros_sistema`, alerta de críticos + alerta de lotes
  por caducar con purga, orden de compra con cantidad sugerida y Pareto
  ABC con cortes configurables. Con base, el botón genera las órdenes con
  `sp_generar_ordenes_compra`; sin conexión exporta el CSV de siempre.
- **Compras:** lista las órdenes por estado, muestra proveedor, fecha, total
  y detalle; genera las sugeridas y recibe una orden completa con
  `sp_recibir_orden_compra`, refrescando el inventario. Sin base muestra
  órdenes de ejemplo en solo lectura.
- **Pronóstico:** regresión sobre fecha real con nivel en el último punto,
  estacionalidad semanal con 28+ días, 30 pasos diarios, backtest contra
  ingenuo y media móvil (si no gana, se marca preliminar) y reparto por
  participación de ingresos.
- **Interfaz:** solo títulos, tablas, gráficas y botones. Sin textos de
  ayuda, sin banners, sin pies de página. Roles: Administrador (todo y
  bitácora), Gerente (sin bitácora) y Cajero (sin pronóstico ni compras).

## Lo que sigue

1. Persistir pronósticos, backtest y reparto en `pronosticos*`.
2. Instalador (MSI/Inno Setup) y firma del ejecutable.
