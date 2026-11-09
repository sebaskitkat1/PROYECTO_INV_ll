-- Corrige el KPI "Precio por unidad": debe ser ingresos / unidades vendidas,
-- no ingresos / numero de tickets. Idempotente.
-- Uso: mysql -u root -p < db/migrate_kpi_precio_unidad.sql
USE frutidata;

CREATE OR REPLACE VIEW v_kpi_dashboard AS
SELECT s.id_sucursal,
       COALESCE(h.ventas, 0)   AS ventas_hoy,
       COALESCE(a.ventas, 0)   AS ventas_ayer,
       ROUND((COALESCE(h.ventas, 0) - a.ventas) / NULLIF(a.ventas, 0) * 100, 1) AS variacion_pct,
       ROUND(h.ventas / NULLIF(h.unidades, 0), 2) AS ticket_promedio,
       COALESCE(h.unidades, 0) AS unidades_hoy,
       (SELECT COUNT(*) FROM v_estado_inventario e
         WHERE e.id_sucursal = s.id_sucursal AND e.estado = 'critico') AS stock_en_riesgo
FROM sucursales s
LEFT JOIN v_ventas_diarias h ON h.id_sucursal = s.id_sucursal AND h.fecha = CURDATE()
LEFT JOIN v_ventas_diarias a ON a.id_sucursal = s.id_sucursal AND a.fecha = CURDATE() - INTERVAL 1 DAY;

-- Verificacion: precio promedio por unidad de hoy (si hay ventas).
SELECT ticket_promedio, unidades_hoy, ventas_hoy
FROM v_kpi_dashboard
ORDER BY id_sucursal
LIMIT 1;
