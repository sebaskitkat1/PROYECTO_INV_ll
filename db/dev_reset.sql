-- =====================================================================
--  PELIGRO: BORRA TODA LA BASE frutidata (tablas, datos y migraciones).
--  SOLO PARA DESARROLLO LOCAL. NO SE DISTRIBUYE EN EL INSTALADOR.
--
--  Uso desde la raiz del repositorio:
--      mysql -u root -p < db/dev_reset.sql
--
--  Luego vuelve a crear el usuario de la app con db/crear_usuario_app.sql.
-- =====================================================================
DROP DATABASE IF EXISTS frutidata;
SOURCE db/init_schema.sql;
