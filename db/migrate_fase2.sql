-- Fase 2: consumo real, lead time y stock de seguridad en inventario/compras.
-- Idempotente: se puede ejecutar varias veces sin duplicar parametros ni vistas.
-- Uso: mysql -u root -p < db/migrate_fase2.sql
USE frutidata;

-- ---------------------------------------------------------------------
-- 1. parametros nuevos (no pisa valores ya configurados)
-- ---------------------------------------------------------------------
INSERT INTO parametros_sistema (clave, valor, descripcion) VALUES
    ('ventana_consumo_dias', '30', 'Dias hacia atras para calcular el consumo diario'),
    ('lead_time_default',    '2',  'Dias de entrega si el ingrediente no tiene proveedor principal'),
    ('dias_seguridad',       '1',  'Dias de consumo que se guardan como stock de seguridad'),
    ('dias_cobertura',       '7',  'Dias de cobertura objetivo para la cantidad sugerida')
ON DUPLICATE KEY UPDATE descripcion = VALUES(descripcion);

-- ---------------------------------------------------------------------
-- 2. consumo diario real
--    - ventas: total de recetas / dias con venta (no /30 fijo)
--    - merma: MERMA y CADUCIDAD / ventana de consumo
--    - lead time: proveedor principal o parametro por defecto
--    - punto de reorden: maximo manual o consumo x (lead + seguridad)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_estado_inventario AS
SELECT id_sucursal, id_ingrediente, nombre, unidad,
       stock_actual, stock_minimo, consumo_diario,
       CASE WHEN stock_actual <= 0 THEN 0
            WHEN consumo_diario > 0
            THEN ROUND(stock_actual / consumo_diario, 1)
       END AS dias_agotar,
       CASE WHEN stock_actual <= 0 THEN 'critico'
            WHEN stock_minimo <= 0 THEN 'sin_minimo'
            WHEN stock_actual < stock_minimo THEN 'critico'
            WHEN stock_actual < stock_minimo * umbral THEN 'advertencia'
            ELSE 'optimo'
       END AS estado,
       dias_con_datos, consumo_venta, merma_ventana, lead_time_dias,
       ROUND(consumo_diario * seguridad, 3) AS stock_seguridad,
       GREATEST(stock_minimo,
                consumo_diario * (lead_time_dias + seguridad)) AS punto_reorden
FROM (
    SELECT inv.id_sucursal,
           i.id_ingrediente,
           i.nombre,
           um.clave AS unidad,
           inv.stock_actual,
           inv.stock_minimo,
           ROUND(COALESCE(vta.consumo_venta / NULLIF(vta.dias_con_datos, 0), 0)
                 + COALESCE(mer.consumo_merma / NULLIF(prm.ventana, 0), 0), 3)
                                                    AS consumo_diario,
           COALESCE(vta.dias_con_datos, 0)          AS dias_con_datos,
           ROUND(COALESCE(vta.consumo_venta, 0), 3) AS consumo_venta,
           ROUND(COALESCE(mer.consumo_merma, 0), 3) AS merma_ventana,
           COALESCE(p.dias_entrega, prm.lead_time_default) AS lead_time_dias,
           prm.dias_seguridad                       AS seguridad,
           prm.umbral                               AS umbral
    FROM inventario inv
    JOIN ingredientes i     ON i.id_ingrediente = inv.id_ingrediente AND i.activo = 1
    JOIN unidades_medida um ON um.id_unidad = i.id_unidad
    LEFT JOIN (
        SELECT v.id_sucursal, r.id_ingrediente,
               SUM(d.cantidad * r.cantidad)       AS consumo_venta,
               COUNT(DISTINCT DATE(v.fecha_hora)) AS dias_con_datos
        FROM detalle_ventas d
        JOIN ventas v  ON v.id_venta = d.id_venta AND v.estado = 'completada'
        JOIN recetas r ON r.id_producto = d.id_producto
        WHERE v.fecha_hora >= DATE_SUB(CURDATE(), INTERVAL COALESCE(
                  (SELECT CAST(valor AS UNSIGNED) FROM parametros_sistema
                    WHERE clave = 'ventana_consumo_dias'), 30) DAY)
        GROUP BY v.id_sucursal, r.id_ingrediente
    ) vta ON vta.id_sucursal = inv.id_sucursal
         AND vta.id_ingrediente = inv.id_ingrediente
    LEFT JOIN (
        SELECT m.id_sucursal, m.id_ingrediente,
               SUM(m.cantidad) AS consumo_merma
        FROM movimientos_inventario m
        JOIN tipos_movimiento t ON t.id_tipo_mov = m.id_tipo_mov
        WHERE t.clave IN ('MERMA', 'CADUCIDAD')
          AND m.fecha_hora >= DATE_SUB(CURDATE(), INTERVAL COALESCE(
                  (SELECT CAST(valor AS UNSIGNED) FROM parametros_sistema
                    WHERE clave = 'ventana_consumo_dias'), 30) DAY)
        GROUP BY m.id_sucursal, m.id_ingrediente
    ) mer ON mer.id_sucursal = inv.id_sucursal
         AND mer.id_ingrediente = inv.id_ingrediente
    CROSS JOIN (
        SELECT COALESCE(MAX(CASE WHEN clave = 'ventana_consumo_dias'
                                 THEN CAST(valor AS DECIMAL(6,2)) END), 30) AS ventana,
               COALESCE(MAX(CASE WHEN clave = 'lead_time_default'
                                 THEN CAST(valor AS DECIMAL(6,2)) END), 2)  AS lead_time_default,
               COALESCE(MAX(CASE WHEN clave = 'dias_seguridad'
                                 THEN CAST(valor AS DECIMAL(6,2)) END), 1)  AS dias_seguridad,
               COALESCE(MAX(CASE WHEN clave = 'umbral_advertencia'
                                 THEN CAST(valor AS DECIMAL(6,2)) END), 1.25) AS umbral
        FROM parametros_sistema
    ) prm
    LEFT JOIN ingrediente_proveedor ip
           ON ip.id_ingrediente = i.id_ingrediente AND ip.es_principal = 1
    LEFT JOIN proveedores p ON p.id_proveedor = ip.id_proveedor
) t;

-- ---------------------------------------------------------------------
-- 3. cantidad sugerida con cobertura objetivo
--    objetivo = max(minimo x factor, consumo x (lead + seguridad + cobertura))
--    sugerido = objetivo - stock - pendiente de ordenes abiertas
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_orden_compra_sugerida AS
SELECT e.id_sucursal, e.id_ingrediente, e.nombre, e.unidad,
       e.stock_actual, e.stock_minimo, e.estado,
       e.consumo_diario, e.dias_agotar, e.lead_time_dias,
       e.stock_seguridad, e.punto_reorden,
       prm.objetivo, prm.cobertura,
       GREATEST(0, CEIL(GREATEST(
           e.stock_minimo * prm.objetivo,
           e.consumo_diario * (e.lead_time_dias + prm.seguridad + prm.cobertura))
           - e.stock_actual - COALESCE(pend.pendiente, 0))) AS sugerido,
       ip.id_proveedor, p.nombre AS proveedor, ip.precio_compra,
       GREATEST(0, CEIL(GREATEST(
           e.stock_minimo * prm.objetivo,
           e.consumo_diario * (e.lead_time_dias + prm.seguridad + prm.cobertura))
           - e.stock_actual - COALESCE(pend.pendiente, 0))) * ip.precio_compra
                                                    AS costo_estimado
FROM v_estado_inventario e
CROSS JOIN (
    SELECT COALESCE(MAX(CASE WHEN clave = 'objetivo_reorden'
                             THEN CAST(valor AS DECIMAL(6,2)) END), 2) AS objetivo,
           COALESCE(MAX(CASE WHEN clave = 'dias_seguridad'
                             THEN CAST(valor AS DECIMAL(6,2)) END), 1) AS seguridad,
           COALESCE(MAX(CASE WHEN clave = 'dias_cobertura'
                             THEN CAST(valor AS DECIMAL(6,2)) END), 7) AS cobertura
    FROM parametros_sistema
) prm
LEFT JOIN (
    SELECT o.id_sucursal, d.id_ingrediente,
           SUM(GREATEST(0, d.cantidad_solicitada - COALESCE(d.cantidad_recibida, 0))) AS pendiente
      FROM detalle_ordenes_compra d
      JOIN ordenes_compra o ON o.id_orden = d.id_orden
     WHERE o.estado IN ('borrador', 'enviada')
     GROUP BY o.id_sucursal, d.id_ingrediente
) pend ON pend.id_sucursal = e.id_sucursal
       AND pend.id_ingrediente = e.id_ingrediente
LEFT JOIN ingrediente_proveedor ip
       ON ip.id_ingrediente = e.id_ingrediente AND ip.es_principal = 1
LEFT JOIN proveedores p ON p.id_proveedor = ip.id_proveedor
WHERE e.estado IN ('critico', 'advertencia')
   OR (e.estado <> 'sin_minimo' AND e.stock_actual <= e.punto_reorden);

-- ---------------------------------------------------------------------
-- 4. verificacion
-- ---------------------------------------------------------------------
SELECT 'parametros_fase2' AS revision, COUNT(*) AS encontrados
FROM parametros_sistema
WHERE clave IN ('ventana_consumo_dias', 'lead_time_default',
                'dias_seguridad', 'dias_cobertura');

SELECT 'consumo_con_datos' AS revision, COUNT(*) AS ingredientes
FROM v_estado_inventario WHERE dias_con_datos > 0;

SELECT 'sugeridos' AS revision, COUNT(*) AS ingredientes
FROM v_orden_compra_sugerida WHERE sugerido > 0;
