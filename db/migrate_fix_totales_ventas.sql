-- Corrige el trigger de totales de venta y repara las cabeceras historicas.
-- El trigger anterior hacia total = subtotal + ultimo_renglon porque MySQL
-- ya veia la columna subtotal actualizada dentro del mismo SET.
-- Uso: mysql -u root -p < db/migrate_fix_totales_ventas.sql
USE frutidata;

DROP TRIGGER IF EXISTS trg_detalle_ventas_ai;

DELIMITER $$

CREATE TRIGGER trg_detalle_ventas_ai
AFTER INSERT ON detalle_ventas
FOR EACH ROW
BEGIN
    -- Guarda el subtotal anterior en una variable para no depender del orden
    -- de evaluacion del SET. Asi total = subtotal - descuento.
    DECLARE v_subtotal DECIMAL(12,2);
    SELECT subtotal INTO v_subtotal FROM ventas WHERE id_venta = NEW.id_venta;
    UPDATE ventas
       SET subtotal = v_subtotal + NEW.subtotal,
           total    = GREATEST(v_subtotal + NEW.subtotal - descuento, 0)
     WHERE id_venta = NEW.id_venta;

    IF COALESCE(@omitir_inventario, 0) = 0 THEN
        INSERT INTO movimientos_inventario
               (id_sucursal, id_ingrediente, id_tipo_mov, cantidad, fecha_hora, id_usuario, id_venta)
        SELECT v.id_sucursal, r.id_ingrediente,
               (SELECT id_tipo_mov FROM tipos_movimiento WHERE clave = 'SALIDA_VENTA'),
               r.cantidad * NEW.cantidad, v.fecha_hora, v.id_usuario, v.id_venta
          FROM ventas v
          JOIN recetas r ON r.id_producto = NEW.id_producto
         WHERE v.id_venta = NEW.id_venta;
    END IF;
END$$

DELIMITER ;

-- Repara las 2,332 ventas historicas que quedaron con el total duplicado.
UPDATE ventas v
LEFT JOIN (
    SELECT id_venta, SUM(subtotal) AS subtotal_real
    FROM detalle_ventas
    GROUP BY id_venta
) d ON d.id_venta = v.id_venta
SET v.subtotal = COALESCE(d.subtotal_real, 0),
    v.total = GREATEST(COALESCE(d.subtotal_real, 0) - v.descuento, 0);

SELECT COUNT(*) AS ventas_con_total_incorrecto
FROM ventas
WHERE total <> GREATEST(subtotal - descuento, 0);
