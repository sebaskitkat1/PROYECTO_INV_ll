-- Fase 5: stock de seguridad estadistico ajustado por clasificacion XYZ.
-- Idempotente: se puede ejecutar varias veces sin duplicar parametros ni vistas.
-- Uso: mysql -u root -p < db/migrate_fase5.sql
USE frutidata;

-- ---------------------------------------------------------------------
-- 1. parametros nuevos (no pisa valores ya configurados)
--    La clasificacion XYZ usa la demanda diaria de ventas en una ventana
--    calendario. Con pocos dias con venta se usa el respaldo por dias.
-- ---------------------------------------------------------------------
INSERT INTO parametros_sistema (clave, valor, descripcion) VALUES
    ('xyz_ventana_dias', '90',  'Dias hacia atras para clasificar la variabilidad XYZ'),
    ('xyz_min_dias',     '7',   'Dias con venta necesarios para usar el stock estadistico'),
    ('xyz_corte_x',      '0.5', 'Coeficiente de variacion maximo para la clase X'),
    ('xyz_corte_y',      '1.0', 'Coeficiente de variacion maximo para la clase Y'),
    ('z_xyz_x',          '1.28', 'Factor z de servicio para clase X (90%)'),
    ('z_xyz_y',          '1.65', 'Factor z de servicio para clase Y (95%)'),
    ('z_xyz_z',          '2.33', 'Factor z de servicio para clase Z (99%)')
ON DUPLICATE KEY UPDATE descripcion = VALUES(descripcion);

-- ---------------------------------------------------------------------
-- 2. estado de inventario con XYZ y stock de seguridad estadistico
--    - consumo diario: igual que fase 2 (ventas / dias con venta + merma).
--    - XYZ: media y desviacion de la demanda diaria en la ventana calendario;
--      los dias sin venta cuentan como cero. CV = sigma / media.
--    - colchon: z(clase) * sigma * sqrt(lead time).
--    - respaldo: consumo_diario * dias_seguridad si no hay datos suficientes.
--    - punto de reorden: demanda durante lead time + colchon (o minimo manual).
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
       xyz_dias_con_datos, xyz_media, xyz_sigma, xyz_cv, xyz_clase,
       CASE WHEN xyz_clase IS NULL
            THEN ROUND(consumo_diario * seguridad, 3)
            ELSE ROUND(xyz_z * xyz_sigma * SQRT(GREATEST(lead_time_dias, 1)), 3)
       END AS stock_seguridad,
       ROUND(GREATEST(stock_minimo,
                consumo_diario * lead_time_dias
                + CASE WHEN xyz_clase IS NULL
                       THEN consumo_diario * seguridad
                       ELSE xyz_z * xyz_sigma * SQRT(GREATEST(lead_time_dias, 1))
                  END), 3) AS punto_reorden
FROM (
    SELECT raw.*,
           CASE WHEN raw.xyz_cv IS NULL THEN NULL
                WHEN raw.xyz_cv <= raw.xyz_corte_x THEN 'X'
                WHEN raw.xyz_cv <= raw.xyz_corte_y THEN 'Y'
                ELSE 'Z'
           END AS xyz_clase,
           CASE WHEN raw.xyz_cv IS NULL THEN NULL
                WHEN raw.xyz_cv <= raw.xyz_corte_x THEN raw.z_x
                WHEN raw.xyz_cv <= raw.xyz_corte_y THEN raw.z_y
                ELSE raw.z_z
           END AS xyz_z
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
               prm.umbral                               AS umbral,
               COALESCE(xyz.dias_con_venta, 0)          AS xyz_dias_con_datos,
               ROUND(COALESCE(xyz.consumo_xyz, 0)
                     / NULLIF(prm.xyz_ventana, 0), 4)   AS xyz_media,
               ROUND(SQRT(GREATEST(0,
                     COALESCE(xyz.consumo_xyz_sq, 0) / NULLIF(prm.xyz_ventana, 0)
                     - POWER(COALESCE(xyz.consumo_xyz, 0)
                             / NULLIF(prm.xyz_ventana, 0), 2))), 4) AS xyz_sigma,
               CASE WHEN COALESCE(xyz.consumo_xyz, 0) > 0
                    THEN ROUND(
                        SQRT(GREATEST(0,
                            COALESCE(xyz.consumo_xyz_sq, 0) / NULLIF(prm.xyz_ventana, 0)
                            - POWER(COALESCE(xyz.consumo_xyz, 0)
                                    / NULLIF(prm.xyz_ventana, 0), 2)))
                        / (COALESCE(xyz.consumo_xyz, 0)
                           / NULLIF(prm.xyz_ventana, 0)), 4)
               END                                      AS xyz_cv,
               prm.xyz_corte_x,
               prm.xyz_corte_y,
               prm.z_xyz_x                              AS z_x,
               prm.z_xyz_y                              AS z_y,
               prm.z_xyz_z                              AS z_z
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
        LEFT JOIN (
            SELECT dia.id_sucursal, dia.id_ingrediente,
                   COUNT(*)                       AS dias_con_venta,
                   SUM(dia.consumo_dia)           AS consumo_xyz,
                   SUM(dia.consumo_dia * dia.consumo_dia) AS consumo_xyz_sq
            FROM (
                SELECT v.id_sucursal, r.id_ingrediente,
                       DATE(v.fecha_hora) AS fecha,
                       SUM(d.cantidad * r.cantidad) AS consumo_dia
                FROM detalle_ventas d
                JOIN ventas v  ON v.id_venta = d.id_venta AND v.estado = 'completada'
                JOIN recetas r ON r.id_producto = d.id_producto
                WHERE v.fecha_hora >= DATE_SUB(CURDATE(), INTERVAL (COALESCE(
                          (SELECT CAST(valor AS UNSIGNED) FROM parametros_sistema
                            WHERE clave = 'xyz_ventana_dias'), 90) - 1) DAY)
                GROUP BY v.id_sucursal, r.id_ingrediente, DATE(v.fecha_hora)
            ) dia
            GROUP BY dia.id_sucursal, dia.id_ingrediente
        ) xyz ON xyz.id_sucursal = inv.id_sucursal
             AND xyz.id_ingrediente = inv.id_ingrediente
        CROSS JOIN (
            SELECT COALESCE(MAX(CASE WHEN clave = 'ventana_consumo_dias'
                                     THEN CAST(valor AS DECIMAL(6,2)) END), 30) AS ventana,
                   COALESCE(MAX(CASE WHEN clave = 'lead_time_default'
                                     THEN CAST(valor AS DECIMAL(6,2)) END), 2)  AS lead_time_default,
                   COALESCE(MAX(CASE WHEN clave = 'dias_seguridad'
                                     THEN CAST(valor AS DECIMAL(6,2)) END), 1)  AS dias_seguridad,
                   COALESCE(MAX(CASE WHEN clave = 'umbral_advertencia'
                                     THEN CAST(valor AS DECIMAL(6,2)) END), 1.25) AS umbral,
                   COALESCE(MAX(CASE WHEN clave = 'xyz_ventana_dias'
                                     THEN CAST(valor AS DECIMAL(6,2)) END), 90) AS xyz_ventana,
                   COALESCE(MAX(CASE WHEN clave = 'xyz_min_dias'
                                     THEN CAST(valor AS DECIMAL(6,2)) END), 7)  AS xyz_min_dias,
                   COALESCE(MAX(CASE WHEN clave = 'xyz_corte_x'
                                     THEN CAST(valor AS DECIMAL(6,2)) END), 0.5) AS xyz_corte_x,
                   COALESCE(MAX(CASE WHEN clave = 'xyz_corte_y'
                                     THEN CAST(valor AS DECIMAL(6,2)) END), 1.0) AS xyz_corte_y,
                   COALESCE(MAX(CASE WHEN clave = 'z_xyz_x'
                                     THEN CAST(valor AS DECIMAL(6,2)) END), 1.28) AS z_xyz_x,
                   COALESCE(MAX(CASE WHEN clave = 'z_xyz_y'
                                     THEN CAST(valor AS DECIMAL(6,2)) END), 1.65) AS z_xyz_y,
                   COALESCE(MAX(CASE WHEN clave = 'z_xyz_z'
                                     THEN CAST(valor AS DECIMAL(6,2)) END), 2.33) AS z_xyz_z
            FROM parametros_sistema
        ) prm
        LEFT JOIN ingrediente_proveedor ip
               ON ip.id_ingrediente = i.id_ingrediente AND ip.es_principal = 1
        LEFT JOIN proveedores p ON p.id_proveedor = ip.id_proveedor
    ) raw
) base;

-- ---------------------------------------------------------------------
-- 3. cantidad sugerida: el objetivo usa el colchon estadistico, no dias
--    objetivo = max(minimo x factor, consumo x (lead + cobertura) + colchon)
--    sugerido = objetivo - stock - pendiente de ordenes abiertas
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_orden_compra_sugerida AS
SELECT e.id_sucursal, e.id_ingrediente, e.nombre, e.unidad,
       e.stock_actual, e.stock_minimo, e.estado,
       e.consumo_diario, e.dias_agotar, e.lead_time_dias,
       e.stock_seguridad, e.punto_reorden, e.xyz_clase, e.xyz_cv,
       prm.objetivo, prm.cobertura,
       GREATEST(0, CEIL(GREATEST(
           e.stock_minimo * prm.objetivo,
           e.consumo_diario * (e.lead_time_dias + prm.cobertura) + e.stock_seguridad)
           - e.stock_actual - COALESCE(pend.pendiente, 0))) AS sugerido,
       ip.id_proveedor, p.nombre AS proveedor, ip.precio_compra,
       GREATEST(0, CEIL(GREATEST(
           e.stock_minimo * prm.objetivo,
           e.consumo_diario * (e.lead_time_dias + prm.cobertura) + e.stock_seguridad)
           - e.stock_actual - COALESCE(pend.pendiente, 0))) * ip.precio_compra
                                                    AS costo_estimado
FROM v_estado_inventario e
CROSS JOIN (
    SELECT COALESCE(MAX(CASE WHEN clave = 'objetivo_reorden'
                             THEN CAST(valor AS DECIMAL(6,2)) END), 2) AS objetivo,
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
SELECT 'parametros_fase5' AS revision, COUNT(*) AS encontrados
FROM parametros_sistema
WHERE clave IN ('xyz_ventana_dias', 'xyz_min_dias', 'xyz_corte_x',
                'xyz_corte_y', 'z_xyz_x', 'z_xyz_y', 'z_xyz_z');

SELECT 'clases_xyz' AS revision, xyz_clase, COUNT(*) AS ingredientes
FROM v_estado_inventario GROUP BY xyz_clase;

SELECT 'stock_estadistico' AS revision, COUNT(*) AS ingredientes
FROM v_estado_inventario
WHERE xyz_clase IS NOT NULL AND stock_seguridad > 0;

SELECT 'sugeridos_fase5' AS revision, COUNT(*) AS ingredientes
FROM v_orden_compra_sugerida WHERE sugerido > 0;
