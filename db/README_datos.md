# Base de datos `frutidata`

Schema versionado en `db/frutidata_schema.sql` (MySQL 8.0.19+).

```powershell
mysql -u root -p < db/frutidata_schema.sql
CALL sp_generar_ventas_demo(60);   # datos de prueba, no toca inventario
```

## Mapeo vista ↔ pantalla

| Vista / objeto | La usa |
|---|---|
| `v_kpi_dashboard` (ticket real, variación, críticos) | Dashboard |
| `v_ventas_diarias` (serie diaria con fecha) | Dashboard, Pronóstico |
| `v_ventas_por_producto` (categoría como dato) | Ventas |
| `v_tendencia_producto` (30d vs 30d previos) | Ventas |
| `v_estado_inventario` (estado, consumo, días, `sin_minimo`) | Inventario |
| `v_orden_compra_sugerida` (+ proveedor y costo) | Botón orden de compra |
| `v_pareto_abc` | Gráfica ABC |
| `v_lotes_por_caducar` | Alerta de caducidad |
| `v_productos_temporada`, `v_vida_util_clima` | Compras (qué pedir según mes y calor) |
| `pronosticos` + `pronostico_diario` + `pronostico_producto` | Persistir pronóstico y backtest |
| `sp_ajustar_stock`, `sp_recibir_orden_compra`, `sp_purgar_caducados`, `sp_registrar_merma` | Acciones de la app |
| `bitacora_accesos`, `usuarios.password_hash` (bcrypt) | Login |

## Contratos que la app asume

- `unidad` en `kg`/`L`/`pzas` (igual que `ENTERO_UNIDADES`).
- `estado` incluye `sin_minimo`; `dias_agotar` puede ser NULL ("—").
- Umbrales en `parametros_sistema` (`umbral_advertencia`, `objetivo_reorden`,
  `alerta_caducidad_dias`, `factor_calor_35/30`); la app no hardcodea nada nuevo.
- Clima de `clima_torreon` son promedios de referencia, no medición en vivo.
