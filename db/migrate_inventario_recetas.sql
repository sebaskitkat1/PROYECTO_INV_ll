-- Completa ingredientes, recetas, inventario y proveedores para los 66 productos.
-- Sin esto, los productos nuevos se venden pero no descuentan existencias.
-- Idempotente: se puede ejecutar varias veces sin duplicar filas.
-- Uso: mysql -u root -p < db/migrate_inventario_recetas.sql
USE frutidata;

-- 1. Categorias de ingrediente que faltan para bebidas, snacks y abarrotes.
INSERT INTO categorias_ingrediente (nombre) VALUES
    ('Bebidas'), ('Snacks'), ('Abarrotes')
ON DUPLICATE KEY UPDATE nombre = VALUES(nombre);

-- 2. Un ingrediente por producto. "Manzana Roja" reutiliza el ingrediente
--    historico "Manzana" para no duplicar existencias.
INSERT INTO ingredientes (id_categoria_ing, id_unidad, nombre, costo_unitario,
                          vida_anaquel_dias, requiere_refrigeracion,
                          mes_inicio_temporada, mes_fin_temporada)
SELECT ci.id_categoria_ing, u.id_unidad, p.nombre, p.costo_unitario,
       p.vida_anaquel_dias, p.requiere_refrigeracion,
       p.mes_inicio_temporada, p.mes_fin_temporada
FROM productos p
JOIN categorias_producto cp ON cp.id_categoria = p.id_categoria
JOIN categorias_ingrediente ci
  ON ci.nombre = CASE cp.nombre
                     WHEN 'Jugos' THEN 'Jugos y preparados'
                     ELSE cp.nombre
                 END
JOIN unidades_medida u ON u.id_unidad = p.id_unidad
LEFT JOIN ingredientes i ON i.nombre = p.nombre
WHERE p.activo = 1
  AND p.nombre <> 'Manzana Roja'
  AND i.id_ingrediente IS NULL;

-- 3. Receta 1:1 para todo producto que aun no tenga receta.
--    Las recetas detalladas existentes (jugos) se conservan.
INSERT INTO recetas (id_producto, id_ingrediente, cantidad)
SELECT p.id_producto, i.id_ingrediente, 1.0000
FROM productos p
JOIN ingredientes i
  ON i.nombre = CASE p.nombre
                    WHEN 'Manzana Roja' THEN 'Manzana'
                    ELSE p.nombre
                END
WHERE p.activo = 1
  AND NOT EXISTS (SELECT 1 FROM recetas r WHERE r.id_producto = p.id_producto);

-- 4. Existencias iniciales de ejemplo para los ingredientes nuevos.
--    No toca las existencias que ya tenia la base.
INSERT INTO inventario (id_sucursal, id_ingrediente, stock_actual, stock_minimo)
SELECT s.id_sucursal, i.id_ingrediente, 20.000, 10.000
FROM ingredientes i
CROSS JOIN (SELECT id_sucursal FROM sucursales ORDER BY id_sucursal LIMIT 1) s
LEFT JOIN inventario inv
  ON inv.id_sucursal = s.id_sucursal
 AND inv.id_ingrediente = i.id_ingrediente
WHERE i.activo = 1
  AND inv.id_ingrediente IS NULL;

-- 5. Proveedor principal para que las ordenes sugeridas tengan datos.
INSERT INTO ingrediente_proveedor (id_ingrediente, id_proveedor, precio_compra, es_principal)
SELECT i.id_ingrediente, p.id_proveedor, i.costo_unitario, 1
FROM ingredientes i
JOIN (SELECT id_proveedor FROM proveedores ORDER BY id_proveedor LIMIT 1) p
LEFT JOIN ingrediente_proveedor ip
  ON ip.id_ingrediente = i.id_ingrediente
 AND ip.es_principal = 1
WHERE i.activo = 1
  AND ip.id_ingrediente IS NULL;

-- Verificacion: los tres conteos deben dar 0.
SELECT COUNT(*) AS productos_sin_receta
FROM productos p
WHERE p.activo = 1
  AND NOT EXISTS (SELECT 1 FROM recetas r WHERE r.id_producto = p.id_producto);

SELECT COUNT(*) AS ingredientes_sin_inventario
FROM ingredientes i
WHERE i.activo = 1
  AND NOT EXISTS (SELECT 1 FROM inventario inv WHERE inv.id_ingrediente = i.id_ingrediente);

SELECT COUNT(*) AS ingredientes_sin_proveedor
FROM ingredientes i
WHERE i.activo = 1
  AND NOT EXISTS (
      SELECT 1 FROM ingrediente_proveedor ip
      WHERE ip.id_ingrediente = i.id_ingrediente AND ip.es_principal = 1
  );
