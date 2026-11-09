-- Amplia el catalogo para el punto de venta sin borrar datos.
-- Idempotente: se puede ejecutar varias veces.
-- Uso: mysql -u root -p < db/migrate_catalogo_pos.sql
USE frutidata;

INSERT INTO categorias_producto (nombre) VALUES
    ('Frutas'), ('Verduras'), ('Jugos'), ('Bebidas'), ('Snacks'), ('Abarrotes')
ON DUPLICATE KEY UPDATE nombre = VALUES(nombre);

INSERT INTO productos (id_categoria, id_unidad, nombre, precio_venta, costo_unitario,
                       vida_anaquel_dias, requiere_refrigeracion, mes_inicio_temporada, mes_fin_temporada)
SELECT c.id_categoria, u.id_unidad, x.nombre, x.precio, x.costo, x.vida, x.frio, x.ini, x.fin
FROM (
    SELECT 'Mango' AS nombre, 'Frutas' AS cat, 'kg' AS uni, 28.00 AS precio, 14.84 AS costo, 6 AS vida, 0 AS frio, 4 AS ini, 9 AS fin UNION ALL
    SELECT 'Manzana Roja' AS nombre, 'Frutas' AS cat, 'kg' AS uni, 18.00 AS precio, 9.90 AS costo, 45 AS vida, 1 AS frio, 8 AS ini, 11 AS fin UNION ALL
    SELECT 'Uva' AS nombre, 'Frutas' AS cat, 'kg' AS uni, 32.00 AS precio, 20.48 AS costo, 6 AS vida, 1 AS frio, 5 AS ini, 8 AS fin UNION ALL
    SELECT 'Naranja' AS nombre, 'Frutas' AS cat, 'kg' AS uni, 14.00 AS precio, 5.88 AS costo, 18 AS vida, 0 AS frio, 10 AS ini, 3 AS fin UNION ALL
    SELECT 'Fresa' AS nombre, 'Frutas' AS cat, 'kg' AS uni, 35.00 AS precio, 23.45 AS costo, 4 AS vida, 1 AS frio, 11 AS ini, 4 AS fin UNION ALL
    SELECT 'Plátano' AS nombre, 'Frutas' AS cat, 'kg' AS uni, 12.00 AS precio, 5.76 AS costo, 6 AS vida, 0 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Piña' AS nombre, 'Frutas' AS cat, 'pzas' AS uni, 25.00 AS precio, 12.75 AS costo, 6 AS vida, 0 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Sandía' AS nombre, 'Frutas' AS cat, 'pzas' AS uni, 60.00 AS precio, 33.60 AS costo, 10 AS vida, 0 AS frio, 4 AS ini, 8 AS fin UNION ALL
    SELECT 'Papaya' AS nombre, 'Frutas' AS cat, 'kg' AS uni, 22.00 AS precio, 11.00 AS costo, 5 AS vida, 0 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Limón' AS nombre, 'Frutas' AS cat, 'kg' AS uni, 18.00 AS precio, 7.20 AS costo, 18 AS vida, 0 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Aguacate' AS nombre, 'Frutas' AS cat, 'kg' AS uni, 45.00 AS precio, 27.00 AS costo, 5 AS vida, 0 AS frio, 8 AS ini, 2 AS fin UNION ALL
    SELECT 'Durazno' AS nombre, 'Frutas' AS cat, 'kg' AS uni, 38.00 AS precio, 22.04 AS costo, 4 AS vida, 1 AS frio, 6 AS ini, 9 AS fin UNION ALL
    SELECT 'Melón' AS nombre, 'Frutas' AS cat, 'pzas' AS uni, 30.00 AS precio, 16.20 AS costo, 8 AS vida, 0 AS frio, 4 AS ini, 8 AS fin UNION ALL
    SELECT 'Pera' AS nombre, 'Frutas' AS cat, 'kg' AS uni, 38.00 AS precio, 22.80 AS costo, 20 AS vida, 1 AS frio, 7 AS ini, 10 AS fin UNION ALL
    SELECT 'Manzana Verde' AS nombre, 'Frutas' AS cat, 'kg' AS uni, 22.00 AS precio, 12.10 AS costo, 45 AS vida, 1 AS frio, 8 AS ini, 11 AS fin UNION ALL
    SELECT 'Mandarina' AS nombre, 'Frutas' AS cat, 'kg' AS uni, 16.00 AS precio, 7.20 AS costo, 14 AS vida, 0 AS frio, 11 AS ini, 2 AS fin UNION ALL
    SELECT 'Toronja' AS nombre, 'Frutas' AS cat, 'kg' AS uni, 15.00 AS precio, 6.60 AS costo, 21 AS vida, 0 AS frio, 10 AS ini, 3 AS fin UNION ALL
    SELECT 'Guayaba' AS nombre, 'Frutas' AS cat, 'kg' AS uni, 24.00 AS precio, 12.00 AS costo, 5 AS vida, 0 AS frio, 8 AS ini, 11 AS fin UNION ALL
    SELECT 'Kiwi' AS nombre, 'Frutas' AS cat, 'kg' AS uni, 45.00 AS precio, 27.00 AS costo, 20 AS vida, 1 AS frio, 5 AS ini, 9 AS fin UNION ALL
    SELECT 'Ciruela' AS nombre, 'Frutas' AS cat, 'kg' AS uni, 36.00 AS precio, 21.60 AS costo, 5 AS vida, 1 AS frio, 5 AS ini, 8 AS fin UNION ALL
    SELECT 'Coco' AS nombre, 'Frutas' AS cat, 'pzas' AS uni, 20.00 AS precio, 10.00 AS costo, 20 AS vida, 0 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Mamey' AS nombre, 'Frutas' AS cat, 'kg' AS uni, 40.00 AS precio, 24.00 AS costo, 5 AS vida, 0 AS frio, 3 AS ini, 7 AS fin UNION ALL
    SELECT 'Zarzamora' AS nombre, 'Frutas' AS cat, 'kg' AS uni, 90.00 AS precio, 54.00 AS costo, 3 AS vida, 1 AS frio, 5 AS ini, 8 AS fin UNION ALL
    SELECT 'Granada' AS nombre, 'Frutas' AS cat, 'kg' AS uni, 35.00 AS precio, 21.00 AS costo, 15 AS vida, 0 AS frio, 8 AS ini, 11 AS fin UNION ALL
    SELECT 'Jitomate' AS nombre, 'Verduras' AS cat, 'kg' AS uni, 16.00 AS precio, 7.20 AS costo, 6 AS vida, 0 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Cebolla' AS nombre, 'Verduras' AS cat, 'kg' AS uni, 16.00 AS precio, 7.20 AS costo, 45 AS vida, 0 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Papa' AS nombre, 'Verduras' AS cat, 'kg' AS uni, 14.00 AS precio, 5.88 AS costo, 45 AS vida, 0 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Tomate Verde' AS nombre, 'Verduras' AS cat, 'kg' AS uni, 18.00 AS precio, 8.10 AS costo, 10 AS vida, 0 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Chile Jalapeño' AS nombre, 'Verduras' AS cat, 'kg' AS uni, 22.00 AS precio, 9.90 AS costo, 14 AS vida, 1 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Chile Serrano' AS nombre, 'Verduras' AS cat, 'kg' AS uni, 20.00 AS precio, 9.00 AS costo, 14 AS vida, 1 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Pimiento Morrón' AS nombre, 'Verduras' AS cat, 'kg' AS uni, 32.00 AS precio, 16.00 AS costo, 10 AS vida, 1 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Zanahoria' AS nombre, 'Verduras' AS cat, 'kg' AS uni, 12.00 AS precio, 5.40 AS costo, 30 AS vida, 1 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Calabacita' AS nombre, 'Verduras' AS cat, 'kg' AS uni, 16.00 AS precio, 7.20 AS costo, 7 AS vida, 1 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Pepino' AS nombre, 'Verduras' AS cat, 'kg' AS uni, 14.00 AS precio, 6.30 AS costo, 10 AS vida, 1 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Lechuga Romana' AS nombre, 'Verduras' AS cat, 'pzas' AS uni, 18.00 AS precio, 9.00 AS costo, 5 AS vida, 1 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Espinaca' AS nombre, 'Verduras' AS cat, 'pzas' AS uni, 20.00 AS precio, 10.00 AS costo, 4 AS vida, 1 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Brócoli' AS nombre, 'Verduras' AS cat, 'pzas' AS uni, 25.00 AS precio, 12.50 AS costo, 7 AS vida, 1 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Coliflor' AS nombre, 'Verduras' AS cat, 'pzas' AS uni, 22.00 AS precio, 11.00 AS costo, 7 AS vida, 1 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Repollo' AS nombre, 'Verduras' AS cat, 'pzas' AS uni, 16.00 AS precio, 8.00 AS costo, 14 AS vida, 1 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Betabel' AS nombre, 'Verduras' AS cat, 'kg' AS uni, 18.00 AS precio, 8.10 AS costo, 20 AS vida, 1 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Apio' AS nombre, 'Verduras' AS cat, 'pzas' AS uni, 20.00 AS precio, 10.00 AS costo, 10 AS vida, 1 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Elote' AS nombre, 'Verduras' AS cat, 'pzas' AS uni, 10.00 AS precio, 4.00 AS costo, 4 AS vida, 1 AS frio, 5 AS ini, 10 AS fin UNION ALL
    SELECT 'Camote' AS nombre, 'Verduras' AS cat, 'kg' AS uni, 18.00 AS precio, 8.10 AS costo, 30 AS vida, 0 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Nopal' AS nombre, 'Verduras' AS cat, 'kg' AS uni, 16.00 AS precio, 7.20 AS costo, 7 AS vida, 1 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Jugo de Naranja' AS nombre, 'Jugos' AS cat, 'L' AS uni, 20.00 AS precio, 7.80 AS costo, 2 AS vida, 1 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Jugo Verde' AS nombre, 'Jugos' AS cat, 'L' AS uni, 25.00 AS precio, 11.25 AS costo, 2 AS vida, 1 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Jugo de Betabel' AS nombre, 'Jugos' AS cat, 'L' AS uni, 28.00 AS precio, 12.60 AS costo, 2 AS vida, 1 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Jugo de Zanahoria' AS nombre, 'Jugos' AS cat, 'L' AS uni, 24.00 AS precio, 10.80 AS costo, 2 AS vida, 1 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Limonada' AS nombre, 'Jugos' AS cat, 'L' AS uni, 18.00 AS precio, 6.30 AS costo, 2 AS vida, 1 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Smoothie de Fresa' AS nombre, 'Jugos' AS cat, 'L' AS uni, 35.00 AS precio, 17.50 AS costo, 2 AS vida, 1 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Agua de Horchata' AS nombre, 'Bebidas' AS cat, 'L' AS uni, 20.00 AS precio, 7.00 AS costo, 2 AS vida, 1 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Agua de Jamaica' AS nombre, 'Bebidas' AS cat, 'L' AS uni, 18.00 AS precio, 5.40 AS costo, 2 AS vida, 1 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Agua Natural' AS nombre, 'Bebidas' AS cat, 'pzas' AS uni, 12.00 AS precio, 5.00 AS costo, 180 AS vida, 0 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Refresco de Cola' AS nombre, 'Bebidas' AS cat, 'pzas' AS uni, 20.00 AS precio, 12.00 AS costo, 180 AS vida, 0 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Té Helado' AS nombre, 'Bebidas' AS cat, 'pzas' AS uni, 22.00 AS precio, 10.00 AS costo, 90 AS vida, 1 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Café Americano' AS nombre, 'Bebidas' AS cat, 'pzas' AS uni, 25.00 AS precio, 8.00 AS costo, 1 AS vida, 0 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Papas Fritas' AS nombre, 'Snacks' AS cat, 'pzas' AS uni, 18.00 AS precio, 10.00 AS costo, 90 AS vida, 0 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Cacahuates' AS nombre, 'Snacks' AS cat, 'pzas' AS uni, 15.00 AS precio, 7.00 AS costo, 120 AS vida, 0 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Granola' AS nombre, 'Snacks' AS cat, 'pzas' AS uni, 35.00 AS precio, 18.00 AS costo, 90 AS vida, 0 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Barra de Cereal' AS nombre, 'Snacks' AS cat, 'pzas' AS uni, 15.00 AS precio, 8.00 AS costo, 180 AS vida, 0 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Galletas de Avena' AS nombre, 'Snacks' AS cat, 'pzas' AS uni, 20.00 AS precio, 10.00 AS costo, 60 AS vida, 0 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Chocolate Amargo' AS nombre, 'Snacks' AS cat, 'pzas' AS uni, 30.00 AS precio, 18.00 AS costo, 180 AS vida, 0 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Miel' AS nombre, 'Abarrotes' AS cat, 'pzas' AS uni, 80.00 AS precio, 48.00 AS costo, 365 AS vida, 0 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Mermelada de Fresa' AS nombre, 'Abarrotes' AS cat, 'pzas' AS uni, 55.00 AS precio, 30.00 AS costo, 180 AS vida, 0 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Semillas de Chía' AS nombre, 'Abarrotes' AS cat, 'pzas' AS uni, 45.00 AS precio, 25.00 AS costo, 365 AS vida, 0 AS frio, 1 AS ini, 12 AS fin UNION ALL
    SELECT 'Avena' AS nombre, 'Abarrotes' AS cat, 'kg' AS uni, 35.00 AS precio, 18.00 AS costo, 180 AS vida, 0 AS frio, 1 AS ini, 12 AS fin
) x
JOIN categorias_producto c ON c.nombre = x.cat
JOIN unidades_medida u     ON u.clave  = x.uni
ON DUPLICATE KEY UPDATE
    id_categoria           = VALUES(id_categoria),
    id_unidad              = VALUES(id_unidad),
    precio_venta           = VALUES(precio_venta),
    costo_unitario         = VALUES(costo_unitario),
    vida_anaquel_dias      = VALUES(vida_anaquel_dias),
    requiere_refrigeracion = VALUES(requiere_refrigeracion),
    mes_inicio_temporada   = VALUES(mes_inicio_temporada),
    mes_fin_temporada      = VALUES(mes_fin_temporada),
    activo                 = 1;

-- Verificacion: deben ser 66 productos activos en 6 categorias.
SELECT COUNT(*) AS productos_activos FROM productos WHERE activo = 1;
SELECT c.nombre AS categoria, COUNT(*) AS productos
FROM productos p
JOIN categorias_producto c ON c.id_categoria = p.id_categoria
WHERE p.activo = 1
GROUP BY c.nombre
ORDER BY c.nombre;
