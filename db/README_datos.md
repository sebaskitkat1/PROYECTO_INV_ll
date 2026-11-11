# Base de datos `frutidata`

Schema versionado en `db/frutidata_schema.sql` (MySQL 8.0.19+).

```powershell
mysql -u root -p < db/frutidata_schema.sql
CALL sp_generar_ventas_demo(60);   # datos de prueba, no toca inventario
```

Para una base ya creada, aplica las migraciones sin borrar datos:

```powershell
mysql -u root -p < db/migrate_ordenes_pendientes.sql
mysql -u root -p < db/migrate_catalogo_pos.sql
mysql -u root -p < db/migrate_fix_totales_ventas.sql
mysql -u root -p < db/migrate_cantidades_decimales.sql
mysql -u root -p < db/migrate_inventario_recetas.sql
mysql -u root -p < db/migrate_kpi_precio_unidad.sql
mysql -u root -p < db/migrate_fase0.sql
mysql -u root -p < db/migrate_fase2.sql
```

`migrate_catalogo_pos.sql` deja 66 productos activos en 6 categorías.
`migrate_fix_totales_ventas.sql` corrige el trigger de totales y repara las
cabeceras históricas de `ventas`.
`migrate_cantidades_decimales.sql` cambia `detalle_ventas.cantidad` a
`DECIMAL(10,3)` para vender medios kilos y litros fraccionados.
`migrate_inventario_recetas.sql` crea un ingrediente, una receta 1:1, una
fila de inventario y un proveedor principal para cada producto que aún no
los tenía (los jugos conservan sus recetas detalladas).
`migrate_kpi_precio_unidad.sql` corrige `v_kpi_dashboard` para que el KPI
sea ingresos / unidades vendidas, no ingresos / tickets.
`migrate_fase0.sql` agrega `ventas.origen` (`real`/`simulado`), los índices
por origen y fecha, `pronosticos.wape_modelo`/`sesgo_modelo` y la vista
`v_ventas_diarias_origen`. Las ventas que ya existían quedan como simuladas.
Es idempotente.
`migrate_fase2.sql` agrega los parámetros de consumo (`ventana_consumo_dias`,
`lead_time_default`, `dias_seguridad`, `dias_cobertura`) y reemplaza
`v_estado_inventario`/`v_orden_compra_sugerida`: el consumo diario divide
entre los días con venta (no entre 30 fijo), suma merma/caducidad y el
sugerido incluye el lead time del proveedor principal y el stock de
seguridad. También es idempotente.

## Mapeo vista ↔ pantalla

| Vista / objeto | La usa |
|---|---|
| `v_kpi_dashboard` (ticket real, variación, críticos) | Dashboard |
| `v_ventas_diarias` (serie diaria con fecha) | Dashboard, Pronóstico |
| `v_ventas_diarias_origen` (serie diaria por `origen`) | Pronóstico (reales vs simuladas) |
| `v_ventas_por_producto` (categoría como dato) | Ventas |
| `v_tendencia_producto` (30d vs 30d previos) | Ventas |
| `ventas` + `detalle_ventas` filtradas por fecha/producto/origen | Reporte por producto y periodo (incluye el mismo rango del año anterior) |
| `v_estado_inventario` (estado, consumo, merma, días, lead time, punto de reorden, `sin_minimo`) | Inventario (tabla, ABC/XYZ, merma) |
| `v_orden_compra_sugerida` (sugerido con cobertura, proveedor y costo) | Inventario (columna Sugerido), botón orden de compra, Compras |
| `v_pareto_abc` (cortes A/B desde parámetros) | Gráfica ABC |
| `v_lotes_por_caducar` | Alerta de caducidad |
| `v_productos_temporada`, `v_vida_util_clima` | Compras (qué pedir según mes y calor), Inventario (tarjeta Riesgo calor) |
| `ventas` + `detalle_ventas` (cabecera y renglones) | Caja (registro de venta) |
| `ordenes_compra`, `detalle_ordenes_compra`, `proveedores` | Compras (lista y detalle) |
| `pronosticos` + `pronostico_diario` + `pronostico_producto` | Pronóstico (botón Guardar) |
| `sp_generar_ordenes_compra`, `sp_recibir_orden_compra` | Compras (generar y recibir) |
| `sp_ajustar_stock`, `sp_purgar_caducados`, `sp_registrar_merma` | Acciones de la app |
| `bitacora_accesos`, `usuarios.password_hash` (bcrypt) | Login |

## Contratos que la app asume

- `unidad` en `kg`/`L`/`pzas` (igual que `ENTERO_UNIDADES`).
- `detalle_ventas.cantidad` es `DECIMAL(10,3)`: acepta 0.500 kg o 0.250 L
  y también piezas enteras. La caja redondea a 3 decimales y rechaza
  cantidades menores a 0.001.
- Todo producto activo tiene al menos una receta; `register_sale` valida el
  stock de sus ingredientes con `FOR UPDATE` antes de insertar la venta.
- `ventas.total = subtotal - descuento`; el trigger `trg_detalle_ventas_ai`
  mantiene ambos totales al insertar renglones.
- `ventas.origen` es `real` o `simulado` (default `real`). La caja registra
  real; `sp_generar_ventas_demo` y el cajero diario registran simulado.
- `pronosticos` guarda `mae_*`, `wape_modelo` y `sesgo_modelo`; WAPE y sesgo
  pueden ser NULL si el backtest no tuvo datos suficientes.
- `estado` incluye `sin_minimo`; `dias_agotar` puede ser NULL ("—").
- `consumo_diario` = ventas de recetas / días con venta + merma/caducidad /
  ventana de consumo. Un día sin venta no cuenta como cero; la merma se
  reparte entre la ventana para no inflar un evento aislado.
- `lead_time_dias` sale de `proveedores.dias_entrega` del proveedor principal;
  si no hay principal usa `lead_time_default`.
- `punto_reorden = max(stock_minimo, consumo_diario * (lead_time + dias_seguridad))`.
- `ordenes_compra.estado` usa `borrador`, `enviada`, `recibida` o `cancelada`;
  solo se reciben las dos primeras. `sp_recibir_orden_compra` recibe todo
  cuando `cantidad_recibida` es NULL y registra el kardex.
- `v_orden_compra_sugerida` descuenta lo pendiente de órdenes abiertas
  (`borrador`/`enviada`), así generar dos veces no duplica pedidos. El
  objetivo es `max(stock_minimo * objetivo_reorden, consumo_diario *
  (lead_time + dias_seguridad + dias_cobertura))`.
- Umbrales en `parametros_sistema` (`umbral_advertencia`, `objetivo_reorden`,
  `alerta_caducidad_dias`, `dias_alerta_agotar`, `abc_corte_a/b`,
  `ventana_consumo_dias`, `lead_time_default`, `dias_seguridad`,
  `dias_cobertura`, `factor_calor_35/30`); la app los lee al abrir
  inventario y usa defaults equivalentes si no hay base.
- Clima de `clima_torreon` son promedios de referencia, no medición en vivo.
