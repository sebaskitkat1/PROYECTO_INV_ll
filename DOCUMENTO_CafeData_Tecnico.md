# Cosecha (frutería) — Documento Técnico a Profundidad
### Arquitectura, Framework, Análisis de Datos, Motor de Predicción y Automatización del Cajero

**Proyecto:** `CafeData-Desktop` — *tu frutería en números*
**Stack:** Python 3.10+ + PySide6 (Qt 6) + Matplotlib — solo stdlib para cálculos
**Entrada:** `main.py` — **Versión analizada:** escritorio conectado a MySQL (`frutidata`) con modo ejemplo (`CAFE_DATOS=mock`)

---

## Índice

1. [Visión general y principios de diseño](#1-visión-general-y-principios-de-diseño)
2. [Stack tecnológico](#2-stack-tecnológico)
3. [Arquitectura general](#3-arquitectura-general)
4. [Framework utilizado (PySide6 / Qt)](#4-framework-utilizado-pyside6--qt)
5. [Capa de datos: base real, mock y sesión](#5-capa-de-datos-base-real-mock-y-sesión)
6. [Seguridad, roles y bitácora](#6-seguridad-roles-y-bitácora)
7. [Análisis de datos en la app](#7-análisis-de-datos-en-la-app)
8. [Motor de predicción (modelo de DA)](#8-motor-de-predicción-modelo-de-da)
9. [Flujos de datos end-to-end](#9-flujos-de-datos-end-to-end)
10. [Interfaz y visualización](#10-interfaz-y-visualización)
11. [Calidad, tests y limitaciones](#11-calidad-tests-y-limitaciones)
12. [Base de datos (schema y procedimientos)](#12-base-de-datos-schema-y-procedimientos)
13. [Cajero automático diario y automatización](#13-cajero-automático-diario-y-automatización)
14. [Anexo: mapa de archivos](#14-anexo-mapa-de-archivos)

---

## 1. Visión general y principios de diseño

Cosecha es una app de escritorio para una **frutería** que responde 4 preguntas:

1. **¿Cómo vendimos?** (Dashboard + Ventas)
2. **¿Qué nos falta?** (Inventario)
3. **¿Qué vamos a necesitar?** (Compras)
4. **¿Qué va a pasar?** (Pronóstico 30 días)

Principios que se cumplen en todo el código:

| Principio | Cómo se aplica |
|-----------|----------------|
| **Números que salen de los datos, nada a mano** | Ninguna pantalla tiene cifras hardcodeadas. Todo KPI, gráfica y tabla se calcula desde `app/data/analytics.py` o desde la base. |
| **Funciones puras sin dependencias** | `analytics.py` solo usa `math` + `datetime` del stdlib. Recibe `list[dict]` y devuelve cuentas. Testeable sin Qt ni DB. |
| **Contrato `list[dict]`** | `mock_data.py` devuelve datos de ejemplo; `repository.py` devuelve la misma forma desde MySQL. Las pantallas no cambian. |
| **Estado en memoria** | `store.py` conserva el inventario editado al navegar. `app_state.py` conserva usuario, rol y sucursal. |
| **Método simple y visible** | El pronóstico es regresión lineal + estacionalidad semanal explícita, con backtest honesto. Nada de caja negra. |
| **Sin ORM ni frameworks pesados** | Solo `mysql-connector-python`. Las consultas son SQL directo en `repository.py`. |

Pantallas (8):

* `login_screen.py` — acceso contra `usuarios` con bcrypt (o modo ejemplo).
* `dashboard_screen.py` — Hoy, 4 KPIs y 3 gráficas en vista previa que se amplían al hacer clic.
* `pos_screen.py` — Caja: catálogo de 66 productos, cantidades decimales, ticket y cobro.
* `sales_screen.py` — filtro por categoría + buscador, tabla ordenable, ingresos por categoría.
* `inventory_screen.py` — stock editable, alertas, caducidad, cobertura de los 10 más urgentes, distribución ABC y orden de compra.
* `purchases_screen.py` — órdenes de compra, detalle, recepción.
* `prediction_screen.py` — histórico vs pronóstico 30 días y guardado.
* `bitacora_screen.py` — accesos (solo Administrador).

---

## 2. Stack tecnológico

```
Python 3.10+  (typing X|Y, future annotations)
  ├─ PySide6 >= 6.6   → Qt 6: ventanas, widgets, signals/slots, QSS
  ├─ matplotlib >= 3.8 → gráficas embebidas vía FigureCanvasQTAgg
  ├─ mysql-connector-python → conexión a MySQL (frutidata)
  ├─ bcrypt → hash de contraseñas
  └─ stdlib → math, datetime, csv, unittest, socket, decimal
```

`requirements.txt` tiene solo 2 líneas a propósito (`PySide6`, `matplotlib`); `mysql-connector-python` y `bcrypt` se agregan para la base real. No hay pandas, numpy, sklearn ni ORM. Esto es una decisión arquitectónica:

* **Ventaja:** instalador ligero, arranque rápido, `pyinstaller` simple desde `main.py`, lógica auditable.
* **Costo:** todo estadístico se implementa a mano (regresión, MAPE, Pareto). Es viable porque n < 10.000 filas.

---

## 3. Arquitectura general

### 3.1 Diagrama de capas

```
┌──────────────────────────────────────────────────────────────┐
│ main.py: QApplication + GLOBAL_STYLESHEET +                  │
│          MainWindow().show() + app.exec()                     │
└──────────────────────┬───────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────┐
│ app/main_window.py: QStackedWidget + guard de sesión + nav   │
│  login / dashboard / pos / sales / inventory / purchases /    │
│  prediction / bitacora                                       │
└──────────────────────┬───────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────┐
│ app/data/repository.py: puerta a la base (misma forma mock)  │
│  auth, dashboard_kpis, sales_detail, inventory_rows,          │
│  pos_products, register_sale, purchase_orders, ...           │
└──────────────────────┬───────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────┐
│ app/data/db.py: conexión MySQL desde .env (mysql-connector)  │
│ app/data/analytics.py: cálculos puros (stdlib)               │
│ app/data/store.py: estado en memoria (inventario editado)    │
│ app/data/app_state.py: sesión (usuario, rol, sucursal)        │
│ app/data/params.py: umbrales por defecto                     │
│ app/data/roles.py: permisos por rol                          │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 Punto de entrada `main.py`

`QApplication(sys.argv)` → aplica `GLOBAL_STYLESHEET` → `MainWindow()` → `show()` → `app.exec()`. Sin lógica de negocio; solo bootstrap.

### 3.3 Navegación `app/main_window.py`

`QStackedWidget` con 8 pantallas. Un guard de sesión redirige al login si no hay usuario. La nav se filtra por rol (Cajero no ve Pronóstico ni Compras ni Bitácora).

### 3.4 Separación de responsabilidades

* **Pantallas (`screens/`)**: solo UI y eventos. No calculan; llaman a `repository` o `analytics`.
* **`repository.py`**: única puerta a la base. Devuelve la misma forma que el mock.
* **`analytics.py`**: cálculos puros (sin Qt, sin DB).
* **`store.py`**: estado en memoria para inventario editado.
* **`db.py`**: conexión MySQL desde `.env`.

---

## 4. Framework utilizado (PySide6 / Qt)

### 4.1 Qt como framework de eventos

Qt es un framework de UI basado en **señales y slots**, **event loop** y **widgets jerárquicos**. PySide6 es el binding oficial de Qt para Python.

### 4.2 Widgets usados

`QMainWindow`, `QStackedWidget`, `QPushButton`, `QTableWidget`, `QLineEdit`, `QComboBox`, `QMessageBox`, `QLabel`, `QDoubleSpinBox`, `QTabWidget`, `QScrollArea`, `QFrame`.

### 4.3 Estilos QSS (`styles.py`)

Hoja de estilos global (paleta papel, verde, menta) aplicada con `app.setStyleSheet()`.

### 4.4 Matplotlib embebido (`widgets/mpl_canvas.py`)

`FigureCanvasQTAgg` embebe figuras matplotlib en widgets Qt.

### 4.5 Detalles finos

* `QApplication` único; `sys.exit(app.exec())`.
* Validación de entrada en la UI antes de llamar a la base.
* Roles filtran la navegación.

---

## 5. Capa de datos: base real, mock y sesión

### 5.1 `db.py` — conexión MySQL

Lee `.env` (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`). Funciones: `available()`, `connect()`, `fetchall()`, `execute()`, `callproc()`, `transaction()` (context manager). Sin credenciales en código.

### 5.2 `repository.py` — puerta a la base

Cada función devuelve la misma forma que usaban los dicts del mock. Si no hay base (o `CAFE_DATOS=mock`), lanza `DBError` y la pantalla usa el ejemplo. Incluye:

* `auth(correo, password)` → valida contra `usuarios` con bcrypt, registra bitácora.
* `dashboard_kpis()`, `sales_detail()`, `sales_history()`, `sales_last_7_days()`.
* `inventory_rows()`, `save_stock()`, `update_minimo()`, `expiry_rows()`, `purge_expired()`.
* `pareto_data()`.
* `purchase_orders()`, `purchase_order_detail()`, `generate_purchase_orders()`, `receive_purchase_order()`.
* `pos_categories()`, `pos_products()`, `pos_payment_methods()`, `register_sale()`.
* `save_forecast()`.
* `system_params()` (umbrales de `parametros_sistema`).

### 5.3 `mock_data.py` — contrato `list[dict]`

Datos de ejemplo (frutas, verduras, jugos, bebidas, snacks, abarrotes) usados en modo ejemplo y en tests.

### 5.4 `store.py` — singleton en memoria

Conserva el inventario editado al navegar entre pantallas.

### 5.5 `app_state.py` — sesión

Guarda `user_id`, `user_name`, `user_email`, `user_role`, `sucursal_id`.

---

## 6. Seguridad, roles y bitácora

### 6.1 Autenticación

`repository.auth()` valida contra `usuarios.password_hash` con bcrypt. Registra cada intento en `bitacora_accesos` (éxito/fracaso, equipo, fecha). Actualiza `ultimo_acceso`.

### 6.2 Roles

| Rol | Permisos |
|-----|----------|
| Administrador | Todo + bitácora |
| Gerente | Todo excepto bitácora |
| Cajero | Caja, Ventas, Inventario (sin pronóstico ni compras ni bitácora) |

`roles.py` define los permisos; `main_window.py` filtra la navegación.

### 6.3 Bitácora

Pantalla `bitacora_screen.py` (solo Administrador): fecha, usuario, correo, resultado, equipo.

---

## 7. Análisis de datos en la app

### 7.1 Ventas

`analytics.py` calcula: totales por día, precio promedio por unidad (ingresos / unidades), unidades, top 5 por ingresos, margen %, tendencia (up/down vs período anterior) e ingresos por categoría.

### 7.2 Inventario

* Estado: óptimo / advertencia / crítico / sin mínimo.
* Cobertura: `dias_agotar = stock / consumo_diario`.
* Alerta de críticos + lotes por caducar.
* Distribución ABC por clase (A/B/C) con cortes configurables
  (`abc_corte_a`, `abc_corte_b`); la tabla conserva el detalle por producto.
* Cobertura de los 10 ingredientes más urgentes (el resto queda en la tabla).
* Orden de compra con cantidad sugerida (`v_orden_compra_sugerida`).

### 7.3 Ventas: filtros e ingresos por categoría

Filtro por categoría + buscador, tabla ordenable y gráfica de ingresos por
categoría (6 barras legibles aun con 66 productos). La dispersión anterior
se retiró porque se amontonaba con el catálogo completo.

### 7.4 Compras

Lista órdenes por estado, muestra proveedor, fecha, total y detalle. Genera sugeridas y recibe con `sp_recibir_orden_compra`.

---

## 8. Motor de predicción (modelo de DA)

### 8.1 Datos de entrada

Serie diaria de ventas (`v_ventas_diarias`): fecha + total. Mínimo 28 días para estacionalidad semanal.

### 8.2 Paso 1 — Tendencia lineal sobre ordinal (`fit_trend`)

Regresión lineal `y = a·x + b` sobre el índice del día. Calcula pendiente e intercepto.

### 8.3 Paso 2 — Estacionalidad semanal (`dow_factors`)

Factor por día de la semana = promedio del día / promedio general. Se aplica solo con 28+ días.

### 8.4 Paso 3 — Proyección 30 días (`forecast_daily`)

Extrapola la tendencia y multiplica por el factor del día de la semana. Nivel en el último punto.

### 8.5 Paso 4 — Backtest honesto (`backtest`)

Compara MAE del modelo vs ingenuo y media móvil de 7. Si no gana, se marca preliminar.

### 8.6 Paso 5 — Reparto por producto (`product_forecast_share`)

Reparte el total proyectado por participación de ingresos de cada producto.

### 8.7 Persistencia

`save_forecast()` guarda cabecera, 30 días y reparto por producto en `pronosticos`, `pronostico_diario`, `pronostico_producto`.

### 8.8 Limitaciones

* Regresión lineal simple (no captura tendencias no lineales).
* Estacionalidad solo semanal (no mensual/anual).
* Backtest con pocos datos puede ser inestable.

---

## 9. Flujos de datos end-to-end

### A. Venta en caja (POS)

1. Cajero selecciona productos y cantidades.
2. `repository.register_sale()` relee precios/costos de la base.
3. Verifica stock por receta (`FOR UPDATE`).
4. Inserta `ventas` + `detalle_ventas` en transacción.
5. Trigger `trg_detalle_ventas_ai` actualiza totales y decrementa inventario (kardex).
6. Devuelve folio.

### B. Generar y recibir orden de compra

1. `generate_purchase_orders()` llama a `sp_generar_ordenes_compra`.
2. El SP recorre `v_orden_compra_sugerida` y crea órdenes por proveedor.
3. `receive_purchase_order()` llama a `sp_recibir_orden_compra`, que da entrada al inventario y cierra la orden.

### C. Pronóstico completo

1. `sales_history(90)` obtiene la serie diaria.
2. `fit_trend` + `dow_factors` + `forecast_daily`.
3. `backtest` compara con ingenuo y media móvil.
4. `product_forecast_share` reparte por producto.
5. `save_forecast()` persiste en la base.

### D. Cajero automático diario

Ver sección 13.

---

## 10. Interfaz y visualización

* Títulos, tablas, gráficas y botones con QSS.
* Canvas matplotlib tono papel + formato $ miles.
* Export a CSV con BOM y anti-fórmulas.
* Orden numérico en tablas (items que ordenan por valor).

---

## 11. Calidad, tests y limitaciones

### Tests (91 en verde)

`unittest discover tests` cubre: inventario, stock, pronóstico, persistencia, repositorio, roles, órdenes, POS, params, simulación, gráficas y UI.

### Lint y tipos

`ruff check .` y `mypy app/data` sin errores.

### Limitaciones

* `detalle_ventas.cantidad` es `DECIMAL(10,3)`: acepta medios kilos y
  litros fraccionados además de piezas enteras.
* Clima de `clima_torreon` son promedios de referencia.
* Pronóstico lineal simple.

---

## 12. Base de datos (schema y procedimientos)

### Tablas principales

`roles`, `usuarios`, `bitacora_accesos`, `sucursales`, `unidades_medida`, `metodos_pago`, `clientes`, `parametros_sistema`, `clima_torreon`, `categorias_producto`, `productos`, `historial_precios`, `categorias_ingrediente`, `ingredientes`, `proveedores`, `recetas`, `inventario`, `movimientos_inventario`, `lotes`, `ventas`, `detalle_ventas`, `ordenes_compra`, `detalle_ordenes_compra`, `pronosticos`, `pronostico_diario`, `pronostico_producto`, `modelos_pronostico`.

### Vistas

`v_kpi_dashboard`, `v_ventas_diarias`, `v_ventas_por_producto`, `v_tendencia_producto`, `v_estado_inventario`, `v_orden_compra_sugerida`, `v_pareto_abc`, `v_lotes_por_caducar`, `v_productos_temporada`, `v_vida_util_clima`.

### Procedimientos

`sp_ajustar_stock`, `sp_registrar_merma`, `sp_purgar_caducados`, `sp_generar_ordenes_compra`, `sp_recibir_orden_compra`, `sp_generar_ventas_demo`.

### Migraciones

`migrate_ordenes_pendientes.sql`, `migrate_catalogo_pos.sql`, `migrate_fix_totales_ventas.sql`, `migrate_cantidades_decimales.sql`, `migrate_inventario_recetas.sql`, `migrate_kpi_precio_unidad.sql`.

---

## 13. Cajero automático diario y automatización

### 13.1 Objetivo

El modelo de DA necesita datos frescos cada día. El cajero automático simula la operación diaria de la frutería y alimenta la base sin intervención manual.

### 13.2 Componentes

| Archivo | Función |
|---|---|
| `scripts/cajero_diario.py` | Script principal. `--tickets N`, `--seed N`, `--dry-run`. |
| `scripts/run_cajero_diario.bat` | Wrapper para programar la ejecución. |
| `scripts/al_encender.ps1` | Al encender: recordatorio MySQL, intenta levantar `MySQL80`, espera base, ejecuta cajero. |
| `scripts/registrar_al_encender.ps1` | Registra tarea al iniciar sesión (requiere admin). |
| `.opencode/agents/cajero.md` | Agente "cajero" desplegado en el proyecto. |
| Carpeta Inicio Windows | `CosechaCajeroAlEncender.bat` lanza `al_encender.ps1` al encender. |

### 13.3 Flujo diario

1. Al encender aparece aviso recordando abrir MySQL.
2. Se intenta iniciar `MySQL80` si está detenido.
3. Se espera hasta ~1 minuto a que `db.available()` sea verdadero.
4. Si no hay conexión, se avisa al usuario.
5. Si hay conexión: recibir pendientes → simular ventas → generar órdenes → recibir nuevas → purgar caducados.
6. El resumen se escribe en `scripts/cajero_diario.log`.

### 13.4 Requisitos

- MySQL (servicio `MySQL80`) disponible al encender.
- Usuario `Cajero Demo` (id 2) en la base.
- Python 3.10+ con dependencias.

### 13.5 Cómo ver los resultados

- **Log diario**: `scripts/cajero_diario.log`.
- **App Cosecha**: Dashboard, Ventas, Inventario, Compras, Pronóstico.
- **Manual**: `python scripts/cajero_diario.py --tickets 50 --seed 42`.

### 13.6 Modelo gratuito de OpenCode recomendado

- Principal: `opencode/deepseek-v4.1-flash-free`.
- Alternativa: `opencode/glm-5.3-flash-free`.
- Evitar los *alpha* en producción diaria.

### 13.7 Cómo explicarlo a los compañeros

- "El cajero automático simula un día de ventas real, actualiza inventario y genera compras, dejando datos listos para el modelo de DA."
- "Al encender aparece un aviso para abrir MySQL; si no se puede conectar, avisa para hacerlo manual."
- "Los resultados se ven en el log y en la app."
- "No se modifican precios ni stock a mano: todo pasa por `register_sale`, `generate_purchase_orders` y `receive_purchase_order`."

---

## 14. Anexo: mapa de archivos

```
main.py
app/
  main_window.py          Ventana y navegación (QStackedWidget + guard de sesión)
  styles.py               Sistema visual (papel, verde, menta)
  data/
    mock_data.py          Datos de ejemplo
    store.py              Datos compartidos en memoria
    analytics.py          Cálculos: totales, KPIs, ABC, pronóstico (stdlib)
    app_state.py          Sesión: usuario, rol y sucursal
    roles.py              Permisos por rol
    params.py             Umbrales por defecto y parseo
    db.py                 Conexión MySQL desde .env
    repository.py         Puerta a la base + auth + kardex
    export_csv.py         Export a CSV (BOM, anti-fórmulas)
  widgets/
    kpi_card.py, nav_bar.py, mpl_canvas.py, chart_card.py, table_items.py
  screens/
    login, dashboard, pos, sales, inventory, purchases, prediction, bitacora
db/
  frutidata_schema.sql    Schema MySQL (tablas, vistas, triggers, SP)
  migrate_*.sql           Migraciones
  README_datos.md         Mapeo vista-pantalla y contratos
scripts/
  cajero_diario.py        Cajero automático diario
  al_encender.ps1         Automatización al encender
  run_cajero_diario.bat   Wrapper
  simulacion/             Walk-forward, newsvendor, FIFO, Monte Carlo
tests/                    91 pruebas
.opencode/agents/cajero.md  Agente cajero
```
'''
print('ready')