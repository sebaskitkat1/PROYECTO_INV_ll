# cosecha — tu frutería en números (Escritorio)

App de escritorio en Python + PySide6 para ver ventas, inventario y pronóstico
de una frutería. Lee de MySQL si hay conexión y usa el ejemplo si no;
los números salen de los datos, no hay cifras escritas a mano.

## Instalación

Requiere Python 3.10+.

```powershell
# desde la carpeta del proyecto
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecución

```powershell
# desde la carpeta del proyecto
python main.py
```

## Pruebas y calidad

```powershell
python -m unittest discover tests   # 123 pruebas
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
# portable: dist\cosecha\cosecha.exe
.\scripts\build_installer.ps1 -Version 1.0.0
# instalador: dist\installer\Cosecha-Setup-1.0.0.exe
```

El instalador requiere Inno Setup 6
(`winget install --id JRSoftware.InnoSetup -e`). Instala por usuario en
`%LOCALAPPDATA%\Programs\Cosecha` sin pedir administrador, incluye el
schema y crea `.env` desde `.env.example` la primera vez. El portable
necesita que copies tu `.env` junto al `.exe` (la app lo busca ahí primero).
El build usa `cosecha.spec` y `main.py` como entrada.

## Registro y diagnóstico

La app escribe eventos, fallos de conexión y errores no controlados en:

```text
%LOCALAPPDATA%\Cosecha\cosecha.log
```

No guarda contraseñas ni datos del `.env`. En modo ejemplo el log también
se crea, pero la app funciona sin MySQL. Las pantallas cargan los datos en
segundo plano cuando hay base real; si una consulta falla, muestran el
ejemplo y dejan el detalle en el log.

## Base de datos

```powershell
# 1. Cargar el schema (la base con datos se llama frutidata)
mysql -u root -p < db/frutidata_schema.sql
#    Si la base ya existe, aplicar las migraciones sin borrar datos:
mysql -u root -p < db/migrate_ordenes_pendientes.sql
mysql -u root -p < db/migrate_catalogo_pos.sql
mysql -u root -p < db/migrate_fix_totales_ventas.sql
mysql -u root -p < db/migrate_cantidades_decimales.sql
mysql -u root -p < db/migrate_inventario_recetas.sql
mysql -u root -p < db/migrate_kpi_precio_unidad.sql
mysql -u root -p < db/migrate_fase0.sql
mysql -u root -p < db/migrate_fase2.sql
mysql -u root -p < db/migrate_fase5.sql
# 2. Copiar .env.example como .env y poner tus valores (nunca se sube)
# 3. Datos de prueba:  CALL sp_generar_ventas_demo(60);
# 4. Dar de alta tu contraseña:
python -c "import bcrypt; print(bcrypt.hashpw(b'TU_CLAVE', bcrypt.gensalt()).decode())"
#    UPDATE frutidata.usuarios SET password_hash='<hash>' WHERE correo='caja@frutidata.local';
```

Los umbrales de inventario (advertencia, reorden, caducidad, días de
alerta, cortes ABC, ventana de consumo, lead time por defecto, días de
seguridad y cobertura, ventana/cortes XYZ y factores z) se leen de
`parametros_sistema`; sin base se usan los mismos valores por defecto.
Los roles salen de `roles`: Administrador ve todo y consulta la bitácora;
Gerente no ve bitácora;
Cajero registra ventas en Caja y no ve pronóstico ni compras. Sin base se
entra en modo Ejemplo: se puede recorrer la app, pero no comprar ni escribir.

Sin MySQL a la mano la app abre igual con el ejemplo. El status de
Ventas indica la fuente ("base de datos" o "ejemplo"). Ver
`db/README_datos.md` para el mapeo vista↔pantalla.

### Datos reales vs simulados

Cada venta guarda `origen` (`real` o `simulado`). El cajero automático marca
sus tickets como simulados; la caja y las acciones manuales registran reales.
Dashboard y Pronóstico muestran la etiqueta. Si hay menos de 14 ventas reales,
el pronóstico usa toda la serie y lo dice ("simulados" o "mixtos"). La
migración `migrate_fase0.sql` agrega la columna, los índices y la vista
`v_ventas_diarias_origen`; el pronóstico guarda además WAPE y sesgo.

### Cajero al encender el equipo

El cajero diario se lanza solo al iniciar sesión, de dos formas que se
complementan:

- Tarea programada `CosechaCajeroAlEncender` (se registra con
  `scripts\registrar_al_encender.ps1`): arranca 15 s después del login,
  reintenta si el equipo estaba apagado (`StartWhenAvailable`) y tiene un
  límite de 15 min.
- Acceso en la carpeta Inicio de Windows
  (`CosechaCajeroAlEncender.bat`), que lanza el mismo
  `scripts\al_encender.ps1` como respaldo.

El script espera hasta ~2 minutos a que MySQL esté disponible, así que puede
tardar un poco en generar las ventas del día. Un candado
(`%LOCALAPPDATA%\Cosecha\cajero.lock`) impide que la tarea y el acceso del
Startup corran el cajero a la vez. El resultado se consulta en:

- `scripts\cajero_diario.log` (UTF-8): detalle de la corrida.
- `%LOCALAPPDATA%\Cosecha\cajero_ultimo_estado.txt`: estado corto
  (`ok (codigo 0, N s)` o `error: ...`).

Si ya hay ventas simuladas del día, el cajero no repite la corrida; usa
`python scripts\cajero_diario.py --force` para forzarla manualmente.

## Simulación con-vs-sin app

```powershell
python scripts/simulacion/run_simulacion.py   # tabla + resultados/utilidad_acumulada.png
python scripts/simulacion/run_producto.py --producto "Jugo Verde" --dias 21
# -> resultados/jugo_verde_21d.png + .csv
```
Walk-forward semanal, políticas de pedido (ojo del dueño vs pronóstico +
newsvendor), inventario FIFO con caducidad real y Monte Carlo con ruido
por día de semana. El segundo comando hace la comparación de un solo
producto en una temporada corta: utilidad, merma y venta perdida, con la
misma demanda real para las dos políticas. Detalles y supuestos en
`scripts/simulacion/README.md`.

## Estructura

```
main.py
app/
  main_window.py          Ventana y navegación (QStackedWidget + guard de sesión)
  styles.py               Sistema visual fresco (papel, verde, menta)
  logging_setup.py        Log local y errores no controlados
  data/
    mock_data.py          Datos de ejemplo: frutas, verduras y jugos (listas de dicts)
    store.py              Datos compartidos en memoria (sobrevive a la navegación)
    analytics.py          Cálculos: totales, KPIs, ABC/XYZ y pronóstico (solo stdlib)
    app_state.py          Sesión: usuario, rol y sucursal actuales
    roles.py              Permisos por rol (admin, gerente, cajero)
    params.py             Umbrales por defecto y parseo de parametros_sistema
    db.py                 Conexión MySQL desde .env (sin credenciales en código)
    repository.py         Puerta a la base con la forma del mock + auth + kardex
    async_loader.py       Consultas en segundo plano para no congelar la UI
    export_csv.py         Export a CSV legible en Excel (BOM, anti-fórmulas)
  widgets/
    kpi_card.py           KPI minimalista con píldora de cambio
    nav_bar.py            Topbar 60px + nav segmentada
    mpl_canvas.py         Canvas matplotlib tono papel + formato $ miles
    chart_card.py         Tarjeta de gráfica con vista previa y ventana ampliada
    table_items.py        Items que ordenan por valor, no por texto
  screens/
    login_screen.py       Acceso contra usuarios (bcrypt) o modo ejemplo
    dashboard_screen.py   Hoy, KPIs y 3 gráficas con vista previa ampliable
    pos_screen.py         Caja: catálogo, ticket y registro de venta
    sales_screen.py       Filtro por categoría, buscador, tabla e ingresos por categoría
    inventory_screen.py   Stock editable, alertas, caducidad, merma y ABC/XYZ
    purchases_screen.py   Órdenes de compra, detalle y recepción
    prediction_screen.py  Histórico vs pronóstico 30 días y guardado
    bitacora_screen.py    Accesos consultables (solo Administrador)
db/
  frutidata_schema.sql    Schema MySQL validado (tablas, vistas, triggers, SP)
  migrate_ordenes_pendientes.sql  Vista de compras sin pedidos duplicados
  migrate_catalogo_pos.sql        Catálogo de 66 productos para la caja
  migrate_fix_totales_ventas.sql  Trigger y totales históricos corregidos
  migrate_cantidades_decimales.sql Cantidades decimales (kg/L) en detalle_ventas
  migrate_inventario_recetas.sql  Recetas, inventario y proveedor para los 66 productos
  migrate_kpi_precio_unidad.sql   KPI de precio promedio por unidad corregido
  migrate_fase0.sql               Origen real/simulado, WAPE/sesgo y vista por origen
  migrate_fase2.sql               Consumo real, merma, lead time y stock de seguridad
  migrate_fase5.sql               Clase XYZ y stock de seguridad estadístico
  diagrama_er.*           Diagrama entidad-relación (general y por módulo)
  README_datos.md         Mapeo vista↔pantalla y contratos
scripts/
  build.ps1               Empaquetado con PyInstaller (cosecha.spec)
  build_installer.ps1     Instalador Inno Setup por usuario
  cajero_diario.py        Cajero automático: ventas simuladas, órdenes y reabasto
  al_encender.ps1         Ejecuta el cajero al iniciar sesión sin ventanas modales
  registrar_al_encender.ps1  Registra la tarea de inicio de sesión
  registrar_tarea.ps1     Registra el cajero diario a una hora fija
  run_cajero_diario.bat   Lanzador del cajero diario
  simulacion/             Walk-forward, newsvendor, FIFO, Monte Carlo y reporte por producto
installer/
  cosecha.iss             Definicion del instalador Windows
  LEEME_INSTALACION.txt   Pasos de base de datos y respaldo
tests/
  test_inventory_table.py Tabla sin corrupción ni cruces (F01)
  test_stock_status.py    Reglas de estado y mock alineado (F05)
  test_forecast.py        Pronóstico, backtest y reparto (F02/F06)
  test_forecast_persist.py Guardado transaccional en pronosticos*
  test_repository.py      Mapeo, fallback y auth (rechazo + bitácora)
  test_roles.py           Permisos, nav filtrada, compras y bitácora
  test_orders.py          Órdenes de compra: mapeo, detalle y ejemplo
  test_pos.py             Catálogo, carrito, validaciones y navegación de caja
  test_charts.py          Resúmenes de gráficas y tarjeta con vista ampliada
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
  precio por unidad, unidades totales, críticos en stock) y tres gráficas
  en vista previa: ventas de 7 días, top de productos y cobertura de
  inventario. Al hacer clic en cualquiera se abre en grande con todos los
  datos y etiquetas. Con base, el precio promedio por unidad es real
  (ventas/unidades con centavos).
- **Caja:** catálogo de 66 productos con buscador y filtro por categoría;
  el catálogo se carga una sola vez y el filtro trabaja en memoria (sin
  consultar la base en cada tecla); ticket con cantidades decimales
  (0.5 kg, 0.25 L) o enteras (piezas), total y método de pago; al cobrar
  inserta la venta y sus renglones en `ventas`/`detalle_ventas` dentro de
  una transacción, releyendo precio y costo de la base y validando
  existencias con bloqueo. Muestra el folio.
- **Ventas:** filtro por categoría (Frutas, Verduras, Jugos, Bebidas,
  Snacks y Abarrotes) + buscador, tabla con orden numérico y por texto sin
  acentos, y gráfica de ingresos por categoría (legible con 66 productos).
  Exporta a CSV que Excel abre bien. El status muestra totales y fuente.
  Incluye un **reporte por producto y periodo**: se eligen uno o varios
  productos (vacío = todos), fecha desde/hasta y origen (todos, real o
  simulado). Muestra totales de unidades, ingresos y margen, la evolución
  diaria en una gráfica con fechas reales (los huecos de días no se
  disimulan) y el detalle por producto en tabla; si hay datos del año
  anterior, agrega la variación contra el mismo periodo. El botón Exportar
  CSV guarda ese detalle con el mismo formato seguro para Excel.
- **Inventario:** stock editable con doble clic (decimales en kg/L, enteros
  en pzas; con base guarda en kardex), estado y cobertura recalculados con
  umbrales de `parametros_sistema`, alerta de críticos + alerta de lotes
  por caducar con purga, orden de compra con cantidad sugerida, cobertura
  de los 10 ingredientes más urgentes, distribución ABC (A/B/C) con cortes
  configurables y variabilidad XYZ de la demanda (X estable, Y media,
  Z errática) sobre 90 días. La tabla muestra la **clase XYZ**, el **CV** y
  la **merma** de la ventana de consumo; la tarjeta **Riesgo calor** cuenta
  los productos sin refrigeración que el clima del mes puede dañar. El
  consumo diario usa los días con venta (no un divisor fijo de 30) y suma
  merma/caducidad. El **stock de seguridad** se calcula con
  `z(clase) × sigma × sqrt(lead time)` y, si no hay días suficientes, con
  el respaldo por días; la columna **Sugerido** y el punto de reorden
  incluyen el lead time del proveedor, ese colchón y la cobertura objetivo.
  Con base, el botón genera las órdenes con `sp_generar_ordenes_compra`;
  sin conexión exporta el CSV con consumo, clase XYZ, colchón, lead time y
  punto de reorden.
- **Compras:** lista las órdenes por estado, muestra proveedor, fecha, total
  y detalle; genera las sugeridas y recibe una orden completa con
  `sp_recibir_orden_compra`, refrescando el inventario. La cantidad sugerida
  descuenta pedidos abiertos y cubre lead time + seguridad + cobertura
  objetivo. Sin base muestra órdenes de ejemplo en solo lectura.
- **Pronóstico:** regresión sobre fecha real con nivel en el último punto,
  estacionalidad semanal con 28+ días y 30 pasos diarios que arrancan hoy
  (no en el pasado). La gráfica muestra los últimos 30 días calendario,
  corta la línea en huecos largos y marca aparte los picos fuera de escala
  para que un día atípico no aplaste el resto de la serie. El backtest usa
  el horizonte real en días calendario y reporta WAPE, sesgo y cobertura
  contra ingenuo y media móvil; si no gana, se marca preliminar. El reparto
  por producto compara 30 días contra 30 días y avisa cuántos días tuvieron
  venta. La pantalla etiqueta si los datos son reales, simulados o mixtos.
  Con base, Guardar pronóstico registra cabecera, 30 días, reparto, WAPE y
  sesgo; sin conexión solo se ve.
- **Interfaz:** títulos, tablas, gráficas y botones; la caja solo muestra
  un aviso si no hay conexión. Roles: Administrador (todo y bitácora),
  Gerente (sin bitácora) y Cajero (caja, ventas e inventario, sin
  pronóstico ni compras).

## Lo que sigue

1. Firmar `cosecha.exe` y el instalador con un certificado de código.
2. Respaldo/restauración de MySQL y validación de recepción de compras
   end-to-end en un equipo destino.
3. Impresión de ticket y corte de caja para la operación diaria.
4. Programación de envíos automáticos del reporte de ventas (correo o
   carpeta compartida); la comparación contra el año anterior ya está.
5. Acumular más ventas reales para que la clase XYZ y el stock de
   seguridad dejen de depender de los datos simulados, y validar con el
   dueño los niveles de servicio (`z`) por clase.
