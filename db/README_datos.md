# Base de datos `frutidata`

Schema versionado en `db/frutidata_schema.sql` (MySQL 8.0.19+).

```powershell
mysql -u root -p < db/frutidata_schema.sql
CALL sp_generar_ventas_demo(60);   # datos de prueba, no toca inventario
```

Para una base ya creada, actualiza solo la vista de compras sin borrar datos:

```powershell
mysql -u root -p < db/migrate_ordenes_pendientes.sql
```

## Mapeo vista ↔ pantalla

| Vista / objeto | La usa |
|---|---|
| `v_kpi_dashboard` (ticket real, variación, críticos) | Dashboard |
| `v_ventas_diarias` (serie diaria con fecha) | Dashboard, Pronóstico |
| `v_ventas_por_producto` (categoría como dato) | Ventas |
| `v_tendencia_producto` (30d vs 30d previos) | Ventas |
| `v_estado_inventario` (estado, consumo, días, `sin_minimo`) | Inventario |
| `v_orden_compra_sugerida` (+ proveedor y costo) | Botón orden de compra, Compras |
| `v_pareto_abc` (cortes A/B desde parámetros) | Gráfica ABC |
| `v_lotes_por_caducar` | Alerta de caducidad |
| `v_productos_temporada`, `v_vida_util_clima` | Compras (qué pedir según mes y calor) |
| `ordenes_compra`, `detalle_ordenes_compra`, `proveedores` | Compras (lista y detalle) |
| `pronosticos` + `pronostico_diario` + `pronostico_producto` | Persistir pronóstico y backtest |
| `sp_generar_ordenes_compra`, `sp_recibir_orden_compra` | Compras (generar y recibir) |
| `sp_ajustar_stock`, `sp_purgar_caducados`, `sp_registrar_merma` | Acciones de la app |
| `bitacora_accesos`, `usuarios.password_hash` (bcrypt) | Login |

## Contratos que la app asume

- `unidad` en `kg`/`L`/`pzas` (igual que `ENTERO_UNIDADES`).
- `estado` incluye `sin_minimo`; `dias_agotar` puede ser NULL ("—").
- `ordenes_compra.estado` usa `borrador`, `enviada`, `recibida` o `cancelada`;
  solo se reciben las dos primeras. `sp_recibir_orden_compra` recibe todo
  cuando `cantidad_recibida` es NULL y registra el kardex.
- `v_orden_compra_sugerida` descuenta lo pendiente de órdenes abiertas
  (`borrador`/`enviada`), así generar dos veces no duplica pedidos.
- Umbrales en `parametros_sistema` (`umbral_advertencia`, `objetivo_reorden`,
  `alerta_caducidad_dias`, `dias_alerta_agotar`, `abc_corte_a/b`,
  `factor_calor_35/30`); la app los lee al abrir inventario y usa defaults
  equivalentes si no hay base.
- Clima de `clima_torreon` son promedios de referencia, no medición en vivo.
