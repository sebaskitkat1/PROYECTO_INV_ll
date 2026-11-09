-- Permite vender cantidades decimales (medios kilos, 0.250 L, etc.).
-- `detalle_ventas.cantidad` era SMALLINT UNSIGNED y truncaba cualquier decimal.
-- Idempotente: se puede ejecutar varias veces.
-- Uso: mysql -u root -p < db/migrate_cantidades_decimales.sql
USE frutidata;

ALTER TABLE detalle_ventas
    MODIFY COLUMN cantidad DECIMAL(10,3) NOT NULL;

-- Verificacion: debe reportar decimal(10,3).
SELECT COLUMN_TYPE AS tipo_cantidad
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'detalle_ventas'
  AND COLUMN_NAME = 'cantidad';
