-- =====================================================================
--  Usuario de aplicacion con permisos minimos.
--  Ejecutar como root una sola vez, despues de db/init_schema.sql:
--      mysql -u root -p < db/crear_usuario_app.sql
--
--  Cambia CAMBIAR_CONTRASENA_SEGURA por una contrasena propia y usa el
--  mismo valor en DB_PASSWORD del .env. La app nunca debe usar root.
--
--  Si MySQL no esta en el mismo equipo, cambia 'localhost' por el host
--  desde el que se conecta la app.
-- =====================================================================

CREATE USER IF NOT EXISTS 'cosecha_app'@'localhost'
    IDENTIFIED BY 'CAMBIAR_CONTRASENA_SEGURA';

-- Sin DELETE ni DROP: la app solo lee, inserta, actualiza y ejecuta SP.
GRANT SELECT, INSERT, UPDATE, EXECUTE ON frutidata.* TO 'cosecha_app'@'localhost';

FLUSH PRIVILEGES;
