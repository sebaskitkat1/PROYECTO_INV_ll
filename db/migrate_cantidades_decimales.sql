-- Permite vender cantidades decimales (medios kilos, 0.250 L, etc.).
-- `detalle_ventas.cantidad` era SMALLINT UNSIGNED y truncaba cualquier decimal.
-- Idempotente: se puede ejecutar varias veces.
-- Uso: mysql -u root -p < db/migrate_cantidades_decimales.sql
USE frutidata;

-- Registro idempotente de la migracion (version = nombre sin .sql).
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     VARCHAR(64) NOT NULL PRIMARY KEY,
    aplicada_en DATETIME    NOT NULL
) ENGINE=InnoDB;


ALTER TABLE detalle_ventas
    MODIFY COLUMN cantidad DECIMAL(10,3) NOT NULL;

-- Verificacion: debe reportar decimal(10,3).
SELECT COLUMN_TYPE AS tipo_cantidad
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'detalle_ventas'
  AND COLUMN_NAME = 'cantidad';

-- Registrar la migracion aplicada.
INSERT IGNORE INTO schema_migrations (version, aplicada_en)
VALUES ('migrate_cantidades_decimales', NOW());
