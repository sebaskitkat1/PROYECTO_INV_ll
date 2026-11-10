-- Fase 0/1: separa ventas reales de simuladas, guarda WAPE/sesgo del
-- pronostico y expone la serie diaria por origen.
-- Idempotente: se puede ejecutar varias veces sin duplicar columnas ni indices.
-- Uso: mysql -u root -p < db/migrate_fase0.sql
USE frutidata;

-- ---------------------------------------------------------------------
-- 1. ventas.origen
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS _fase0_add_column;
DELIMITER $$
CREATE PROCEDURE _fase0_add_column(
    IN p_tabla VARCHAR(64),
    IN p_columna VARCHAR(64),
    IN p_definicion VARCHAR(255))
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = p_tabla
          AND COLUMN_NAME = p_columna
    ) THEN
        SET @sql = CONCAT('ALTER TABLE `', p_tabla, '` ADD COLUMN `',
                          p_columna, '` ', p_definicion);
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END$$
DELIMITER ;

-- Si la columna no existia, todo lo cargado hasta ahora es simulado.
SET @tenia_origen = (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'ventas'
      AND COLUMN_NAME = 'origen'
);

CALL _fase0_add_column('ventas', 'origen',
    "ENUM('real','simulado') NOT NULL DEFAULT 'real'");

UPDATE ventas SET origen = 'simulado' WHERE @tenia_origen = 0;

-- Indice para filtrar la serie por origen y fecha.
SET @tenia_indice = (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'ventas'
      AND INDEX_NAME = 'idx_ventas_origen_fecha'
);
SET @sql = IF(@tenia_indice = 0,
    'ALTER TABLE ventas ADD KEY idx_ventas_origen_fecha (origen, fecha_hora)',
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ---------------------------------------------------------------------
-- 2. metricas del backtest en pronosticos
-- ---------------------------------------------------------------------
CALL _fase0_add_column('pronosticos', 'wape_modelo', 'DECIMAL(7,2) NULL');
CALL _fase0_add_column('pronosticos', 'sesgo_modelo', 'DECIMAL(7,2) NULL');

DROP PROCEDURE IF EXISTS _fase0_add_column;

-- Indice para contar intentos fallidos de login por correo y fecha.
SET @tenia_indice_bitacora = (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'bitacora_accesos'
      AND INDEX_NAME = 'idx_bitacora_correo_fecha'
);
SET @sql = IF(@tenia_indice_bitacora = 0,
    'ALTER TABLE bitacora_accesos ADD KEY idx_bitacora_correo_fecha (correo_intentado, fecha_hora)',
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ---------------------------------------------------------------------
-- 3. vista diaria por origen
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_ventas_diarias_origen AS
SELECT DATE(v.fecha_hora)            AS fecha,
       v.id_sucursal,
       v.origen,
       COUNT(DISTINCT v.id_venta)    AS tickets,
       SUM(d.cantidad)               AS unidades,
       SUM(d.subtotal)               AS ventas
FROM ventas v
JOIN detalle_ventas d ON d.id_venta = v.id_venta
WHERE v.estado = 'completada'
GROUP BY DATE(v.fecha_hora), v.id_sucursal, v.origen;

-- ---------------------------------------------------------------------
-- 4. el generador de demo marca sus ventas como simuladas
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_generar_ventas_demo;

DELIMITER $$
CREATE PROCEDURE sp_generar_ventas_demo(IN p_dias INT)
BEGIN
    DECLARE v_dia      INT;
    DECLARE v_tickets  INT;
    DECLARE v_t        INT;
    DECLARE v_items    INT;
    DECLARE v_id       BIGINT UNSIGNED;
    DECLARE v_suc      INT UNSIGNED;
    DECLARE v_usr      INT UNSIGNED;
    DECLARE v_fecha    DATE;

    SELECT MIN(id_sucursal) INTO v_suc FROM sucursales;
    SELECT MIN(id_usuario)  INTO v_usr FROM usuarios;

    SET @omitir_inventario = 1;
    SET v_dia = p_dias - 1;

    WHILE v_dia >= 0 DO
        SET v_fecha = CURDATE() - INTERVAL v_dia DAY;
        -- mas movimiento jueves a sabado
        SET v_tickets = 25 + FLOOR(RAND() * 20)
                        + IF(DAYOFWEEK(v_fecha) IN (5, 6, 7), 12, 0);
        SET v_t = 0;
        WHILE v_t < v_tickets DO
            INSERT INTO ventas (id_sucursal, id_usuario, id_metodo_pago, fecha_hora, origen)
            VALUES (v_suc, v_usr, 1 + FLOOR(RAND() * 3),
                    TIMESTAMP(v_fecha, SEC_TO_TIME(7 * 3600 + FLOOR(RAND() * 13 * 3600))),
                    'simulado');
            SET v_id    = LAST_INSERT_ID();
            SET v_items = 1 + FLOOR(RAND() * 3);

            INSERT INTO detalle_ventas (id_venta, id_producto, cantidad)
            SELECT v_id, id_producto, 1 + FLOOR(RAND() * 2)
              FROM productos WHERE activo = 1
             ORDER BY RAND() LIMIT v_items;

            SET v_t = v_t + 1;
        END WHILE;
        SET v_dia = v_dia - 1;
    END WHILE;

    SET @omitir_inventario = 0;
END$$
DELIMITER ;

-- ---------------------------------------------------------------------
-- 5. verificacion
-- ---------------------------------------------------------------------
SELECT 'ventas.origen' AS revision, COLUMN_TYPE AS detalle
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'ventas'
  AND COLUMN_NAME = 'origen';

SELECT 'pronosticos.wape_modelo' AS revision, COLUMN_TYPE AS detalle
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'pronosticos'
  AND COLUMN_NAME = 'wape_modelo';

SELECT origen, COUNT(*) AS ventas FROM ventas GROUP BY origen;
