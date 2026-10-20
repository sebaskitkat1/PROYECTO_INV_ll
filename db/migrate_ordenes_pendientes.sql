-- Actualiza una base existente sin borrar datos.
-- Evita que "Generar órdenes" duplique pedidos abiertos.
USE frutidata;

CREATE OR REPLACE VIEW v_orden_compra_sugerida AS
SELECT e.id_sucursal, e.id_ingrediente, e.nombre, e.unidad,
       e.stock_actual, e.stock_minimo, e.estado,
       GREATEST(0, CEIL(e.stock_minimo * prm.objetivo - e.stock_actual
                        - COALESCE(pend.pendiente, 0))) AS sugerido,
       ip.id_proveedor, p.nombre AS proveedor, ip.precio_compra,
       GREATEST(0, CEIL(e.stock_minimo * prm.objetivo - e.stock_actual
                        - COALESCE(pend.pendiente, 0))) * ip.precio_compra AS costo_estimado
FROM v_estado_inventario e
CROSS JOIN (SELECT CAST(valor AS DECIMAL(6,2)) AS objetivo
            FROM parametros_sistema WHERE clave = 'objetivo_reorden') prm
LEFT JOIN (
    SELECT o.id_sucursal, d.id_ingrediente,
           SUM(GREATEST(0, d.cantidad_solicitada - COALESCE(d.cantidad_recibida, 0))) AS pendiente
      FROM detalle_ordenes_compra d
      JOIN ordenes_compra o ON o.id_orden = d.id_orden
     WHERE o.estado IN ('borrador', 'enviada')
     GROUP BY o.id_sucursal, d.id_ingrediente
) pend ON pend.id_sucursal = e.id_sucursal AND pend.id_ingrediente = e.id_ingrediente
LEFT JOIN ingrediente_proveedor ip ON ip.id_ingrediente = e.id_ingrediente AND ip.es_principal = 1
LEFT JOIN proveedores p            ON p.id_proveedor = ip.id_proveedor
WHERE e.estado IN ('critico', 'advertencia');
