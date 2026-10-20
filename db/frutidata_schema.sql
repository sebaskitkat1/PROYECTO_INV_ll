-- =====================================================================
--  Cosecha (frutería) — Base de datos normalizada (3FN) para MySQL 8.0+
--  Catálogo, recetas (jugos), ventas, inventario con kardex + LOTES con
--  caducidad, temporada por producto, clima de Torreón de referencia,
--  proveedores, pronóstico y KPIs.
--
--  Uso:   mysql -u root -p < frutidata_schema.sql
--  Requiere MySQL 8.0.19+
-- =====================================================================

-- PELIGRO: borra y recrea la base. Solo para desarrollo / primera instalación.
DROP DATABASE IF EXISTS frutidata;
CREATE DATABASE frutidata
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;
USE frutidata;
SET NAMES utf8mb4;

-- =====================================================================
-- 1. SEGURIDAD Y ACCESO
-- =====================================================================

CREATE TABLE roles (
    id_rol        TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre        VARCHAR(30)  NOT NULL,
    descripcion   VARCHAR(120) NULL,
    PRIMARY KEY (id_rol),
    UNIQUE KEY uq_roles_nombre (nombre)
) ENGINE=InnoDB;

CREATE TABLE usuarios (
    id_usuario     INT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_rol         TINYINT UNSIGNED NOT NULL,
    nombre         VARCHAR(80)  NOT NULL,
    correo         VARCHAR(120) NOT NULL,
    password_hash  VARCHAR(255) NOT NULL,            -- bcrypt/argon2, nunca texto plano
    activo         TINYINT(1)   NOT NULL DEFAULT 1,
    ultimo_acceso  DATETIME     NULL,
    created_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_usuario),
    UNIQUE KEY uq_usuarios_correo (correo),
    CONSTRAINT fk_usuarios_rol FOREIGN KEY (id_rol) REFERENCES roles (id_rol)
) ENGINE=InnoDB;

CREATE TABLE bitacora_accesos (
    id_acceso        BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_usuario       INT UNSIGNED NULL,               -- NULL si el correo no existe
    correo_intentado VARCHAR(120) NOT NULL,
    exitoso          TINYINT(1)   NOT NULL,
    equipo           VARCHAR(100) NULL,
    fecha_hora       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_acceso),
    KEY idx_bitacora_usuario_fecha (id_usuario, fecha_hora),
    CONSTRAINT fk_bitacora_usuario FOREIGN KEY (id_usuario) REFERENCES usuarios (id_usuario)
        ON DELETE SET NULL
) ENGINE=InnoDB;

-- =====================================================================
-- 2. CATÁLOGOS BASE
-- =====================================================================

CREATE TABLE sucursales (
    id_sucursal  INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre       VARCHAR(80)  NOT NULL,
    direccion    VARCHAR(200) NULL,
    telefono     VARCHAR(20)  NULL,
    activa       TINYINT(1)   NOT NULL DEFAULT 1,
    PRIMARY KEY (id_sucursal),
    UNIQUE KEY uq_sucursales_nombre (nombre)
) ENGINE=InnoDB;

CREATE TABLE unidades_medida (
    id_unidad  TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    clave      VARCHAR(10) NOT NULL,                   -- kg, L, pzas (igual que la app)
    nombre     VARCHAR(40) NOT NULL,
    solo_enteros TINYINT(1) NOT NULL DEFAULT 0,       -- 1 = pzas: sin decimales
    PRIMARY KEY (id_unidad),
    UNIQUE KEY uq_unidades_clave (clave)
) ENGINE=InnoDB;

CREATE TABLE metodos_pago (
    id_metodo_pago  TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre          VARCHAR(30) NOT NULL,
    PRIMARY KEY (id_metodo_pago),
    UNIQUE KEY uq_metodos_pago_nombre (nombre)
) ENGINE=InnoDB;

CREATE TABLE clientes (
    id_cliente      INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre          VARCHAR(100) NOT NULL,
    correo          VARCHAR(120) NULL,
    telefono        VARCHAR(20)  NULL,
    fecha_registro  DATE NOT NULL DEFAULT (CURRENT_DATE),
    PRIMARY KEY (id_cliente),
    UNIQUE KEY uq_clientes_correo (correo)
) ENGINE=InnoDB;

CREATE TABLE parametros_sistema (
    clave        VARCHAR(40)  NOT NULL,
    valor        VARCHAR(40)  NOT NULL,
    descripcion  VARCHAR(160) NULL,
    PRIMARY KEY (clave)
) ENGINE=InnoDB;

-- Clima de referencia: promedios mensuales de Torreón (máx/mín °C).
-- NOTA: valores de referencia aproximados; ajustar con tu fuente.
CREATE TABLE clima_torreon (
    mes            TINYINT UNSIGNED NOT NULL,
    temp_max_prom  DECIMAL(4,1) NOT NULL,
    temp_min_prom  DECIMAL(4,1) NOT NULL,
    PRIMARY KEY (mes),
    CONSTRAINT chk_clima_mes CHECK (mes BETWEEN 1 AND 12)
) ENGINE=InnoDB;

-- =====================================================================
-- 3. PRODUCTOS (lo que se vende)
-- =====================================================================

CREATE TABLE categorias_producto (
    id_categoria  TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre        VARCHAR(40) NOT NULL,                -- Frutas, Verduras, Jugos
    PRIMARY KEY (id_categoria),
    UNIQUE KEY uq_cat_producto_nombre (nombre)
) ENGINE=InnoDB;

CREATE TABLE productos (
    id_producto            INT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_categoria           TINYINT UNSIGNED NOT NULL,
    id_unidad              TINYINT UNSIGNED NOT NULL,
    nombre                 VARCHAR(80)  NOT NULL,
    descripcion            VARCHAR(200) NULL,
    precio_venta           DECIMAL(10,2) NOT NULL,
    costo_unitario         DECIMAL(10,2) NOT NULL DEFAULT 0,
    vida_anaquel_dias      SMALLINT UNSIGNED NOT NULL DEFAULT 7,
    requiere_refrigeracion TINYINT(1) NOT NULL DEFAULT 0,
    mes_inicio_temporada   TINYINT UNSIGNED NOT NULL DEFAULT 1,
    mes_fin_temporada      TINYINT UNSIGNED NOT NULL DEFAULT 12,
    activo                 TINYINT(1)   NOT NULL DEFAULT 1,
    created_at             TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_producto),
    UNIQUE KEY uq_productos_nombre (nombre),
    KEY idx_productos_categoria (id_categoria),
    CONSTRAINT fk_productos_categoria FOREIGN KEY (id_categoria) REFERENCES categorias_producto (id_categoria),
    CONSTRAINT fk_productos_unidad    FOREIGN KEY (id_unidad)    REFERENCES unidades_medida (id_unidad),
    CONSTRAINT chk_productos_precio CHECK (precio_venta >= 0),
    CONSTRAINT chk_productos_costo  CHECK (costo_unitario >= 0),
    CONSTRAINT chk_productos_meses CHECK (mes_inicio_temporada BETWEEN 1 AND 12
                                      AND mes_fin_temporada BETWEEN 1 AND 12)
) ENGINE=InnoDB;

CREATE TABLE historial_precios (
    id_historial     BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_producto      INT UNSIGNED NOT NULL,
    precio_anterior  DECIMAL(10,2) NOT NULL,
    precio_nuevo     DECIMAL(10,2) NOT NULL,
    costo_anterior   DECIMAL(10,2) NOT NULL,
    costo_nuevo      DECIMAL(10,2) NOT NULL,
    id_usuario       INT UNSIGNED NULL,
    fecha_cambio     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_historial),
    KEY idx_hist_precios_producto (id_producto, fecha_cambio),
    CONSTRAINT fk_hist_precios_producto FOREIGN KEY (id_producto) REFERENCES productos (id_producto),
    CONSTRAINT fk_hist_precios_usuario  FOREIGN KEY (id_usuario)  REFERENCES usuarios (id_usuario)
        ON DELETE SET NULL
) ENGINE=InnoDB;

-- =====================================================================
-- 4. INSUMOS, PROVEEDORES Y RECETAS (jugos y preparados)
-- =====================================================================

CREATE TABLE categorias_ingrediente (
    id_categoria_ing  TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre            VARCHAR(40) NOT NULL,
    PRIMARY KEY (id_categoria_ing),
    UNIQUE KEY uq_cat_ingrediente_nombre (nombre)
) ENGINE=InnoDB;

CREATE TABLE ingredientes (
    id_ingrediente         INT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_categoria_ing       TINYINT UNSIGNED NOT NULL,
    id_unidad              TINYINT UNSIGNED NOT NULL,
    nombre                 VARCHAR(80) NOT NULL,
    costo_unitario         DECIMAL(10,2) NOT NULL DEFAULT 0,
    vida_anaquel_dias      SMALLINT UNSIGNED NOT NULL DEFAULT 7,
    requiere_refrigeracion TINYINT(1) NOT NULL DEFAULT 0,
    mes_inicio_temporada   TINYINT UNSIGNED NOT NULL DEFAULT 1,
    mes_fin_temporada      TINYINT UNSIGNED NOT NULL DEFAULT 12,
    activo                 TINYINT(1) NOT NULL DEFAULT 1,
    PRIMARY KEY (id_ingrediente),
    UNIQUE KEY uq_ingredientes_nombre (nombre),
    CONSTRAINT fk_ingredientes_categoria FOREIGN KEY (id_categoria_ing) REFERENCES categorias_ingrediente (id_categoria_ing),
    CONSTRAINT fk_ingredientes_unidad    FOREIGN KEY (id_unidad)        REFERENCES unidades_medida (id_unidad),
    CONSTRAINT chk_ingredientes_costo CHECK (costo_unitario >= 0)
) ENGINE=InnoDB;

CREATE TABLE proveedores (
    id_proveedor   INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre         VARCHAR(100) NOT NULL,
    contacto       VARCHAR(80)  NULL,
    telefono       VARCHAR(20)  NULL,
    correo         VARCHAR(120) NULL,
    dias_entrega   TINYINT UNSIGNED NOT NULL DEFAULT 2,
    activo         TINYINT(1) NOT NULL DEFAULT 1,
    PRIMARY KEY (id_proveedor),
    UNIQUE KEY uq_proveedores_nombre (nombre)
) ENGINE=InnoDB;

CREATE TABLE ingrediente_proveedor (
    id_ingrediente  INT UNSIGNED NOT NULL,
    id_proveedor    INT UNSIGNED NOT NULL,
    precio_compra   DECIMAL(10,2) NOT NULL,
    es_principal    TINYINT(1) NOT NULL DEFAULT 0,
    clave_principal INT UNSIGNED GENERATED ALWAYS AS (IF(es_principal = 1, id_ingrediente, NULL)) STORED,
    PRIMARY KEY (id_ingrediente, id_proveedor),
    UNIQUE KEY uq_ing_prov_principal (clave_principal),
    KEY idx_ing_prov_proveedor (id_proveedor),
    CONSTRAINT fk_ing_prov_ingrediente FOREIGN KEY (id_ingrediente) REFERENCES ingredientes (id_ingrediente),
    CONSTRAINT fk_ing_prov_proveedor   FOREIGN KEY (id_proveedor)   REFERENCES proveedores (id_proveedor),
    CONSTRAINT chk_ing_prov_precio CHECK (precio_compra >= 0)
) ENGINE=InnoDB;

-- Receta: cuánto insumo consume UNA unidad vendida (jugos y preparados)
CREATE TABLE recetas (
    id_producto     INT UNSIGNED NOT NULL,
    id_ingrediente  INT UNSIGNED NOT NULL,
    cantidad        DECIMAL(10,4) NOT NULL,
    PRIMARY KEY (id_producto, id_ingrediente),
    KEY idx_recetas_ingrediente (id_ingrediente),
    CONSTRAINT fk_recetas_producto    FOREIGN KEY (id_producto)    REFERENCES productos (id_producto) ON DELETE CASCADE,
    CONSTRAINT fk_recetas_ingrediente FOREIGN KEY (id_ingrediente) REFERENCES ingredientes (id_ingrediente),
    CONSTRAINT chk_recetas_cantidad CHECK (cantidad > 0)
) ENGINE=InnoDB;

-- =====================================================================
-- 5. INVENTARIO + LOTES CON CADUCIDAD + KARDEX
-- =====================================================================

CREATE TABLE inventario (
    id_sucursal     INT UNSIGNED NOT NULL,
    id_ingrediente  INT UNSIGNED NOT NULL,
    stock_actual    DECIMAL(12,3) NOT NULL DEFAULT 0,
    stock_minimo    DECIMAL(12,3) NOT NULL DEFAULT 0,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_sucursal, id_ingrediente),
    KEY idx_inventario_ingrediente (id_ingrediente),
    CONSTRAINT fk_inventario_sucursal    FOREIGN KEY (id_sucursal)    REFERENCES sucursales (id_sucursal),
    CONSTRAINT fk_inventario_ingrediente FOREIGN KEY (id_ingrediente) REFERENCES ingredientes (id_ingrediente),
    CONSTRAINT chk_inventario_minimo CHECK (stock_minimo >= 0)
) ENGINE=InnoDB;

-- Lotes: cada ingreso perecedero trae su caducidad (FEFO al vender)
CREATE TABLE lotes_inventario (
    id_lote          INT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_sucursal      INT UNSIGNED NOT NULL,
    id_ingrediente   INT UNSIGNED NOT NULL,
    cantidad         DECIMAL(12,3) NOT NULL DEFAULT 0,
    fecha_ingreso    DATE NOT NULL DEFAULT (CURRENT_DATE),
    fecha_caducidad  DATE NOT NULL,
    costo_unitario   DECIMAL(10,2) NOT NULL DEFAULT 0,
    PRIMARY KEY (id_lote),
    KEY idx_lotes_caducidad (fecha_caducidad),
    KEY idx_lotes_ingrediente (id_ingrediente),
    CONSTRAINT fk_lotes_sucursal    FOREIGN KEY (id_sucursal)    REFERENCES sucursales (id_sucursal),
    CONSTRAINT fk_lotes_ingrediente FOREIGN KEY (id_ingrediente) REFERENCES ingredientes (id_ingrediente),
    CONSTRAINT chk_lotes_fechas CHECK (fecha_caducidad >= fecha_ingreso),
    CONSTRAINT chk_lotes_cantidad CHECK (cantidad >= 0)
) ENGINE=InnoDB;

CREATE TABLE tipos_movimiento (
    id_tipo_mov  TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    clave        VARCHAR(30) NOT NULL,
    nombre       VARCHAR(60) NOT NULL,
    signo        TINYINT NOT NULL,
    PRIMARY KEY (id_tipo_mov),
    UNIQUE KEY uq_tipos_mov_clave (clave),
    CONSTRAINT chk_tipos_mov_signo CHECK (signo IN (-1, 1))
) ENGINE=InnoDB;

CREATE TABLE ventas (
    id_venta        BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_sucursal     INT UNSIGNED NOT NULL,
    id_usuario      INT UNSIGNED NOT NULL,
    id_cliente      INT UNSIGNED NULL,
    id_metodo_pago  TINYINT UNSIGNED NOT NULL,
    fecha_hora      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    subtotal        DECIMAL(12,2) NOT NULL DEFAULT 0,
    descuento       DECIMAL(12,2) NOT NULL DEFAULT 0,
    total           DECIMAL(12,2) NOT NULL DEFAULT 0,
    estado          ENUM('completada','cancelada') NOT NULL DEFAULT 'completada',
    PRIMARY KEY (id_venta),
    KEY idx_ventas_fecha (fecha_hora),
    KEY idx_ventas_sucursal_fecha (id_sucursal, fecha_hora),
    KEY idx_ventas_usuario (id_usuario),
    KEY idx_ventas_cliente (id_cliente),
    KEY idx_ventas_metodo (id_metodo_pago),
    CONSTRAINT fk_ventas_sucursal FOREIGN KEY (id_sucursal)    REFERENCES sucursales (id_sucursal),
    CONSTRAINT fk_ventas_usuario  FOREIGN KEY (id_usuario)     REFERENCES usuarios (id_usuario),
    CONSTRAINT fk_ventas_cliente  FOREIGN KEY (id_cliente)     REFERENCES clientes (id_cliente) ON DELETE SET NULL,
    CONSTRAINT fk_ventas_metodo   FOREIGN KEY (id_metodo_pago) REFERENCES metodos_pago (id_metodo_pago),
    CONSTRAINT chk_ventas_montos CHECK (subtotal >= 0 AND descuento >= 0 AND total >= 0)
) ENGINE=InnoDB;

CREATE TABLE detalle_ventas (
    id_detalle       BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_venta         BIGINT UNSIGNED NOT NULL,
    id_producto      INT UNSIGNED NOT NULL,
    cantidad         SMALLINT UNSIGNED NOT NULL,
    precio_unitario  DECIMAL(10,2) NOT NULL DEFAULT 0,
    costo_unitario   DECIMAL(10,2) NOT NULL DEFAULT 0,
    subtotal         DECIMAL(12,2) GENERATED ALWAYS AS (cantidad * precio_unitario) STORED,
    PRIMARY KEY (id_detalle),
    KEY idx_detalle_venta (id_venta),
    KEY idx_detalle_producto (id_producto),
    CONSTRAINT fk_detalle_venta    FOREIGN KEY (id_venta)    REFERENCES ventas (id_venta) ON DELETE CASCADE,
    CONSTRAINT fk_detalle_producto FOREIGN KEY (id_producto) REFERENCES productos (id_producto),
    CONSTRAINT chk_detalle_cantidad CHECK (cantidad > 0)
) ENGINE=InnoDB;

-- =====================================================================
-- 6. COMPRAS
-- =====================================================================

CREATE TABLE ordenes_compra (
    id_orden         INT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_sucursal      INT UNSIGNED NOT NULL,
    id_proveedor     INT UNSIGNED NOT NULL,
    id_usuario       INT UNSIGNED NOT NULL,
    fecha_creacion   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_recepcion  DATETIME NULL,
    estado           ENUM('borrador','enviada','recibida','cancelada') NOT NULL DEFAULT 'borrador',
    total            DECIMAL(12,2) NOT NULL DEFAULT 0,
    PRIMARY KEY (id_orden),
    KEY idx_oc_sucursal (id_sucursal),
    KEY idx_oc_proveedor (id_proveedor),
    KEY idx_oc_usuario (id_usuario),
    KEY idx_oc_estado_fecha (estado, fecha_creacion),
    CONSTRAINT fk_oc_sucursal  FOREIGN KEY (id_sucursal)  REFERENCES sucursales (id_sucursal),
    CONSTRAINT fk_oc_proveedor FOREIGN KEY (id_proveedor) REFERENCES proveedores (id_proveedor),
    CONSTRAINT fk_oc_usuario   FOREIGN KEY (id_usuario)   REFERENCES usuarios (id_usuario)
) ENGINE=InnoDB;

CREATE TABLE detalle_ordenes_compra (
    id_detalle           INT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_orden             INT UNSIGNED NOT NULL,
    id_ingrediente       INT UNSIGNED NOT NULL,
    cantidad_solicitada  DECIMAL(12,3) NOT NULL,
    cantidad_recibida    DECIMAL(12,3) NULL,
    precio_unitario      DECIMAL(10,2) NOT NULL,
    PRIMARY KEY (id_detalle),
    UNIQUE KEY uq_doc_orden_ingrediente (id_orden, id_ingrediente),
    KEY idx_doc_ingrediente (id_ingrediente),
    CONSTRAINT fk_doc_orden       FOREIGN KEY (id_orden)       REFERENCES ordenes_compra (id_orden) ON DELETE CASCADE,
    CONSTRAINT fk_doc_ingrediente FOREIGN KEY (id_ingrediente) REFERENCES ingredientes (id_ingrediente),
    CONSTRAINT chk_doc_cantidad CHECK (cantidad_solicitada > 0)
) ENGINE=InnoDB;

CREATE TABLE movimientos_inventario (
    id_movimiento    BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_sucursal      INT UNSIGNED NOT NULL,
    id_ingrediente   INT UNSIGNED NOT NULL,
    id_tipo_mov      TINYINT UNSIGNED NOT NULL,
    cantidad         DECIMAL(12,3) NOT NULL,
    fecha_hora       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    id_usuario       INT UNSIGNED NULL,
    id_venta         BIGINT UNSIGNED NULL,
    id_orden         INT UNSIGNED NULL,
    observaciones    VARCHAR(200) NULL,
    PRIMARY KEY (id_movimiento),
    KEY idx_mov_ingrediente_fecha (id_ingrediente, fecha_hora),
    KEY idx_mov_sucursal_fecha (id_sucursal, fecha_hora),
    KEY idx_mov_tipo (id_tipo_mov),
    KEY idx_mov_venta (id_venta),
    KEY idx_mov_orden (id_orden),
    KEY idx_mov_usuario (id_usuario),
    CONSTRAINT fk_mov_sucursal    FOREIGN KEY (id_sucursal)    REFERENCES sucursales (id_sucursal),
    CONSTRAINT fk_mov_ingrediente FOREIGN KEY (id_ingrediente) REFERENCES ingredientes (id_ingrediente),
    CONSTRAINT fk_mov_tipo        FOREIGN KEY (id_tipo_mov)    REFERENCES tipos_movimiento (id_tipo_mov),
    CONSTRAINT fk_mov_usuario     FOREIGN KEY (id_usuario)     REFERENCES usuarios (id_usuario) ON DELETE SET NULL,
    CONSTRAINT fk_mov_venta       FOREIGN KEY (id_venta)       REFERENCES ventas (id_venta) ON DELETE SET NULL,
    CONSTRAINT fk_mov_orden       FOREIGN KEY (id_orden)       REFERENCES ordenes_compra (id_orden) ON DELETE SET NULL,
    CONSTRAINT chk_mov_cantidad CHECK (cantidad > 0)
) ENGINE=InnoDB;

-- =====================================================================
-- 7. PRONÓSTICO
-- =====================================================================

CREATE TABLE modelos_pronostico (
    id_modelo    TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre       VARCHAR(60) NOT NULL,
    descripcion  VARCHAR(250) NULL,
    parametros   JSON NULL,
    PRIMARY KEY (id_modelo),
    UNIQUE KEY uq_modelos_nombre (nombre)
) ENGINE=InnoDB;

CREATE TABLE pronosticos (
    id_pronostico     INT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_modelo         TINYINT UNSIGNED NOT NULL,
    id_sucursal       INT UNSIGNED NOT NULL,
    id_usuario        INT UNSIGNED NULL,
    fecha_generacion  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    horizonte_dias    SMALLINT UNSIGNED NOT NULL DEFAULT 30,
    crecimiento_pct   DECIMAL(7,2) NULL,
    mae_modelo        DECIMAL(12,2) NULL,
    mae_naive         DECIMAL(12,2) NULL,
    mae_ma7           DECIMAL(12,2) NULL,
    es_preliminar     TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id_pronostico),
    KEY idx_pron_modelo (id_modelo),
    KEY idx_pron_sucursal_fecha (id_sucursal, fecha_generacion),
    CONSTRAINT fk_pron_modelo   FOREIGN KEY (id_modelo)   REFERENCES modelos_pronostico (id_modelo),
    CONSTRAINT fk_pron_sucursal FOREIGN KEY (id_sucursal) REFERENCES sucursales (id_sucursal),
    CONSTRAINT fk_pron_usuario  FOREIGN KEY (id_usuario)  REFERENCES usuarios (id_usuario) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE pronostico_diario (
    id_pronostico      INT UNSIGNED NOT NULL,
    fecha              DATE NOT NULL,
    ventas_estimadas   DECIMAL(12,2) NOT NULL,
    PRIMARY KEY (id_pronostico, fecha),
    CONSTRAINT fk_pron_diario FOREIGN KEY (id_pronostico) REFERENCES pronosticos (id_pronostico) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE pronostico_producto (
    id_pronostico     INT UNSIGNED NOT NULL,
    id_producto       INT UNSIGNED NOT NULL,
    ingresos_actual   DECIMAL(12,2) NOT NULL,
    ingresos_predicho DECIMAL(12,2) NOT NULL,
    crecimiento_pct   DECIMAL(7,2) NOT NULL,
    PRIMARY KEY (id_pronostico, id_producto),
    KEY idx_pron_prod_producto (id_producto),
    CONSTRAINT fk_pron_prod_pron     FOREIGN KEY (id_pronostico) REFERENCES pronosticos (id_pronostico) ON DELETE CASCADE,
    CONSTRAINT fk_pron_prod_producto FOREIGN KEY (id_producto)   REFERENCES productos (id_producto)
) ENGINE=InnoDB;

-- =====================================================================
-- 8. DATOS INICIALES
-- =====================================================================

INSERT INTO roles (nombre, descripcion) VALUES
    ('Administrador', 'Acceso total, usuarios y configuración'),
    ('Gerente',       'Reportes, inventario, compras y pronóstico'),
    ('Cajero',        'Registro de ventas');

-- IMPORTANTE: reemplaza password_hash por un hash real (bcrypt/argon2) generado desde la app.
INSERT INTO usuarios (id_rol, nombre, correo, password_hash) VALUES
    (1, 'Administrador', 'admin@frutidata.local', 'CAMBIAR_POR_HASH_BCRYPT'),
    (3, 'Cajero Demo',   'caja@frutidata.local',  'CAMBIAR_POR_HASH_BCRYPT');

INSERT INTO sucursales (nombre, direccion) VALUES
    ('Sucursal Principal', 'Av. Juárez, Torreón, Coah.');

INSERT INTO unidades_medida (clave, nombre, solo_enteros) VALUES
    ('kg', 'Kilogramo', 0), ('L', 'Litro', 0), ('pzas', 'Pieza', 1);

INSERT INTO metodos_pago (nombre) VALUES ('Efectivo'), ('Tarjeta'), ('Transferencia');

INSERT INTO parametros_sistema (clave, valor, descripcion) VALUES
    ('umbral_advertencia', '1.25', 'Stock < mínimo × este factor => estado advertencia'),
    ('objetivo_reorden',   '2.00', 'Cantidad sugerida = mínimo × este factor − stock actual'),
    ('alerta_caducidad_dias', '7', 'Lotes que caducan dentro de estos días salen en la alerta'),
    ('dias_alerta_agotar', '5', 'Días de cobertura que resaltan la fila en inventario'),
    ('abc_corte_a', '80', 'Pareto: acumulado hasta este % es clase A'),
    ('abc_corte_b', '95', 'Pareto: acumulado hasta este % es clase B'),
    ('factor_calor_35', '0.60', 'Vida útil sin refrigeración si el mes pega 35 °C o más'),
    ('factor_calor_30', '0.80', 'Vida útil sin refrigeración si el mes pega 30 °C o más');

-- Clima de Torreón: promedios mensuales de referencia (máx/mín °C). Ajustar con tu fuente.
INSERT INTO clima_torreon (mes, temp_max_prom, temp_min_prom) VALUES
    (1, 22.0,  6.0), (2, 25.0,  8.0), (3, 29.0, 12.0), (4, 33.0, 16.0),
    (5, 36.0, 20.0), (6, 37.0, 22.0), (7, 37.0, 23.0), (8, 36.0, 22.0),
    (9, 33.0, 20.0), (10, 30.0, 15.0), (11, 26.0, 10.0), (12, 22.0, 6.0);

INSERT INTO tipos_movimiento (clave, nombre, signo) VALUES
    ('ENTRADA_COMPRA',   'Entrada por compra',          1),
    ('SALIDA_VENTA',     'Salida por venta',           -1),
    ('DEVOLUCION_VENTA', 'Reingreso por venta cancelada', 1),
    ('MERMA',            'Merma / desperdicio',        -1),
    ('CADUCIDAD',        'Baja por caducidad',         -1),
    ('AJUSTE_POSITIVO',  'Ajuste de inventario (+)',    1),
    ('AJUSTE_NEGATIVO',  'Ajuste de inventario (−)',   -1);

INSERT INTO categorias_producto (nombre) VALUES ('Frutas'), ('Verduras'), ('Jugos');

-- 18 productos. Precio = ingresos/cantidad del mock de la app; costo = precio × (1 − margen).
INSERT INTO productos (id_categoria, id_unidad, nombre, precio_venta, costo_unitario,
                       vida_anaquel_dias, requiere_refrigeracion, mes_inicio_temporada, mes_fin_temporada)
SELECT c.id_categoria, u.id_unidad, x.nombre, x.precio, x.costo, x.vida, x.frio, x.ini, x.fin
FROM (
    SELECT 'Mango'           AS nombre, 'Frutas' AS cat, 'kg'  AS uni, 28.00 AS precio, 14.84 AS costo,  6 AS vida, 0 AS frio,  4 AS ini,  9 AS fin UNION ALL
    SELECT 'Manzana Roja',               'Frutas',   'kg',    18.00,  9.90, 45, 1,  8, 11 UNION ALL
    SELECT 'Uva',                        'Frutas',   'kg',    32.00, 20.48,  6, 1,  5,  8 UNION ALL
    SELECT 'Naranja',                    'Frutas',   'kg',    14.00,  5.88, 18, 0, 10,  3 UNION ALL
    SELECT 'Fresa',                      'Frutas',   'kg',    35.00, 23.45,  4, 1, 11,  4 UNION ALL
    SELECT 'Plátano',                    'Frutas',   'kg',    12.00,  5.76,  6, 0,  1, 12 UNION ALL
    SELECT 'Piña',                       'Frutas',   'pzas',  25.00, 12.75,  6, 0,  1, 12 UNION ALL
    SELECT 'Sandía',                     'Frutas',   'pzas',  60.00, 33.60, 10, 0,  4,  8 UNION ALL
    SELECT 'Papaya',                     'Frutas',   'kg',    22.00, 11.00,  5, 0,  1, 12 UNION ALL
    SELECT 'Limón',                      'Frutas',   'kg',    18.00,  7.20, 18, 0,  1, 12 UNION ALL
    SELECT 'Aguacate',                   'Frutas',   'kg',    45.00, 27.00,  5, 0,  8,  2 UNION ALL
    SELECT 'Durazno',                    'Frutas',   'kg',    38.00, 22.04,  4, 1,  6,  9 UNION ALL
    SELECT 'Melón',                      'Frutas',   'pzas',  30.00, 16.20,  8, 0,  4,  8 UNION ALL
    SELECT 'Jitomate',                   'Verduras', 'kg',    16.00,  7.20,  6, 0,  1, 12 UNION ALL
    SELECT 'Cebolla',                    'Verduras', 'kg',    16.00,  7.20, 45, 0,  1, 12 UNION ALL
    SELECT 'Papa',                       'Verduras', 'kg',    14.00,  5.88, 45, 0,  1, 12 UNION ALL
    SELECT 'Jugo de Naranja',            'Jugos',    'L',     20.00,  7.80,  2, 1,  1, 12 UNION ALL
    SELECT 'Jugo Verde',                 'Jugos',    'L',     25.00, 11.25,  2, 1,  1, 12
) x
JOIN categorias_producto c ON c.nombre = x.cat
JOIN unidades_medida u     ON u.clave  = x.uni;

INSERT INTO categorias_ingrediente (nombre) VALUES
    ('Frutas'), ('Verduras'), ('Jugos y preparados');

INSERT INTO ingredientes (id_categoria_ing, id_unidad, nombre, costo_unitario,
                          vida_anaquel_dias, requiere_refrigeracion, mes_inicio_temporada, mes_fin_temporada)
SELECT ci.id_categoria_ing, u.id_unidad, x.nombre, x.costo, x.vida, x.frio, x.ini, x.fin
FROM (
    SELECT 'Mango'    AS nombre, 'Frutas' AS cat, 'kg' AS uni, 14.84 AS costo,  6 AS vida, 0 AS frio,  4 AS ini,  9 AS fin UNION ALL
    SELECT 'Manzana',            'Frutas',   'kg',    9.90, 45, 1,  8, 11 UNION ALL
    SELECT 'Uva',                'Frutas',   'kg',   20.48,  6, 1,  5,  8 UNION ALL
    SELECT 'Naranja',            'Frutas',   'kg',    5.88, 18, 0, 10,  3 UNION ALL
    SELECT 'Fresa',              'Frutas',   'kg',   23.45,  4, 1, 11,  4 UNION ALL
    SELECT 'Plátano',            'Frutas',   'kg',    5.76,  6, 0,  1, 12 UNION ALL
    SELECT 'Piña',               'Frutas',   'pzas', 12.75,  6, 0,  1, 12 UNION ALL
    SELECT 'Sandía',             'Frutas',   'pzas', 33.60, 10, 0,  4,  8 UNION ALL
    SELECT 'Papaya',             'Frutas',   'kg',   11.00,  5, 0,  1, 12 UNION ALL
    SELECT 'Limón',              'Frutas',   'kg',    7.20, 18, 0,  1, 12 UNION ALL
    SELECT 'Aguacate',           'Frutas',   'kg',   27.00,  5, 0,  8,  2 UNION ALL
    SELECT 'Durazno',            'Frutas',   'kg',   22.04,  4, 1,  6,  9 UNION ALL
    SELECT 'Melón',              'Frutas',   'pzas', 16.20,  8, 0,  4,  8 UNION ALL
    SELECT 'Jitomate',           'Verduras', 'kg',    7.20,  6, 0,  1, 12 UNION ALL
    SELECT 'Cebolla',            'Verduras', 'kg',    7.20, 45, 0,  1, 12 UNION ALL
    SELECT 'Papa',               'Verduras', 'kg',    5.88, 45, 0,  1, 12 UNION ALL
    SELECT 'Jugo de Naranja',    'Jugos y preparados', 'L',  7.80,  2, 1,  1, 12 UNION ALL
    SELECT 'Jugo Verde',         'Jugos y preparados', 'L', 11.25,  2, 1,  1, 12
) x
JOIN categorias_ingrediente ci ON ci.nombre = x.cat
JOIN unidades_medida u         ON u.clave  = x.uni;

INSERT INTO proveedores (nombre, contacto, dias_entrega) VALUES
    ('Central de Abastos de Torreón', 'Compras',  1),
    ('Huerta Los Nogales',            'Ventas',   2),
    ('Empaques del Bajío',            'Pedidos',  4),
    ('Jugos y Desechables del Norte', 'Pedidos',  1);

INSERT INTO ingrediente_proveedor (id_ingrediente, id_proveedor, precio_compra, es_principal)
SELECT i.id_ingrediente, p.id_proveedor, x.precio, 1
FROM (
    SELECT 'Mango'    AS ing, 'Central de Abastos de Torreón' AS prov, 14.84 AS precio UNION ALL
    SELECT 'Manzana',            'Empaques del Bajío',                 9.90 UNION ALL
    SELECT 'Uva',                'Empaques del Bajío',                20.48 UNION ALL
    SELECT 'Naranja',            'Central de Abastos de Torreón',      5.88 UNION ALL
    SELECT 'Fresa',              'Huerta Los Nogales',                23.45 UNION ALL
    SELECT 'Plátano',            'Central de Abastos de Torreón',      5.76 UNION ALL
    SELECT 'Piña',               'Central de Abastos de Torreón',     12.75 UNION ALL
    SELECT 'Sandía',             'Huerta Los Nogales',                33.60 UNION ALL
    SELECT 'Papaya',             'Central de Abastos de Torreón',     11.00 UNION ALL
    SELECT 'Limón',              'Central de Abastos de Torreón',      7.20 UNION ALL
    SELECT 'Aguacate',           'Huerta Los Nogales',                27.00 UNION ALL
    SELECT 'Durazno',            'Huerta Los Nogales',                22.04 UNION ALL
    SELECT 'Melón',              'Huerta Los Nogales',                16.20 UNION ALL
    SELECT 'Jitomate',           'Central de Abastos de Torreón',      7.20 UNION ALL
    SELECT 'Cebolla',            'Central de Abastos de Torreón',      7.20 UNION ALL
    SELECT 'Papa',               'Central de Abastos de Torreón',      5.88
) x
JOIN ingredientes i ON i.nombre = x.ing
JOIN proveedores  p ON p.nombre = x.prov;

-- Recetas ilustrativas (kg de fruta por litro de jugo)
INSERT INTO recetas (id_producto, id_ingrediente, cantidad)
SELECT p.id_producto, i.id_ingrediente, x.cant
FROM (
    SELECT 'Jugo de Naranja' AS prod, 'Naranja' AS ing, 0.4000 AS cant UNION ALL
    SELECT 'Jugo Verde',               'Piña',           0.1500 UNION ALL
    SELECT 'Jugo Verde',               'Naranja',        0.1000 UNION ALL
    SELECT 'Jugo Verde',               'Mango',          0.0500
) x
JOIN productos    p ON p.nombre = x.prod
JOIN ingredientes i ON i.nombre = x.ing;

-- Existencias iniciales (las 10 del mock de la app + el resto del catálogo).
-- NOTA: 'Jugo de Naranja' 20/18 corresponde a 'Jugo natural (L)' del mock.
INSERT INTO inventario (id_sucursal, id_ingrediente, stock_actual, stock_minimo)
SELECT s.id_sucursal, i.id_ingrediente, x.actual, x.minimo
FROM (
    SELECT 'Manzana' AS ing, 25 AS actual, 20 AS minimo UNION ALL
    SELECT 'Plátano',                30, 22 UNION ALL
    SELECT 'Naranja',                18, 20 UNION ALL
    SELECT 'Mango',                  12, 10 UNION ALL
    SELECT 'Fresa',                   6,  8 UNION ALL
    SELECT 'Uva',                     9,  8 UNION ALL
    SELECT 'Piña',                   40, 30 UNION ALL
    SELECT 'Sandía',                 15, 12 UNION ALL
    SELECT 'Jitomate',               14, 16 UNION ALL
    SELECT 'Jugo de Naranja',        20, 18 UNION ALL
    SELECT 'Papaya',                 10,  8 UNION ALL
    SELECT 'Limón',                  15, 12 UNION ALL
    SELECT 'Aguacate',                8,  6 UNION ALL
    SELECT 'Durazno',                 7,  5 UNION ALL
    SELECT 'Melón',                  12, 10 UNION ALL
    SELECT 'Cebolla',                30, 25 UNION ALL
    SELECT 'Papa',                   35, 30 UNION ALL
    SELECT 'Jugo Verde',             12, 10
) x
JOIN ingredientes i ON i.nombre = x.ing
CROSS JOIN (SELECT id_sucursal FROM sucursales ORDER BY id_sucursal LIMIT 1) s;

-- Lotes de simulación con caducidad relativa a hoy (siempre vigentes al correr).
INSERT INTO lotes_inventario (id_sucursal, id_ingrediente, cantidad, fecha_ingreso, fecha_caducidad, costo_unitario)
SELECT s.id_sucursal, i.id_ingrediente, x.cant,
       CURDATE() - INTERVAL x.hace DAY, CURDATE() + INTERVAL x.caduca DAY, i.costo_unitario
FROM (
    SELECT 'Fresa'           AS ing, 2 AS hace, 2 AS caduca,   6.0 AS cant UNION ALL
    SELECT 'Jugo de Naranja',        0,        1,             20.0 UNION ALL
    SELECT 'Jugo Verde',             0,        2,             12.0 UNION ALL
    SELECT 'Mango',                  1,        4,             12.0 UNION ALL
    SELECT 'Durazno',                0,        3,              7.0 UNION ALL
    SELECT 'Papaya',                 1,        3,             10.0 UNION ALL
    SELECT 'Sandía',                 1,        6,             15.0 UNION ALL
    SELECT 'Naranja',                3,       12,             18.0
) x
JOIN ingredientes i ON i.nombre = x.ing
CROSS JOIN (SELECT id_sucursal FROM sucursales ORDER BY id_sucursal LIMIT 1) s;

INSERT INTO modelos_pronostico (nombre, descripcion, parametros) VALUES
    ('Regresion sobre fecha + reparto por participacion',
     'Nivel = valor ajustado en el ultimo punto + pendiente diaria x k (30 dias). El total se reparte por participacion de ingresos; la suma cuadra. Backtest rolling-origin contra ingenuo y media movil 7: si el modelo no gana, es preliminar.',
     JSON_OBJECT('horizonte_dias', 30, 'reparto_por', 'participacion_ingresos', 'nivel', 'valor_ajustado_ultimo_punto'));

-- =====================================================================
-- 9. TRIGGERS  (consistencia automática)
-- =====================================================================

DELIMITER $$

CREATE TRIGGER trg_detalle_ventas_bi
BEFORE INSERT ON detalle_ventas
FOR EACH ROW
BEGIN
    IF NEW.precio_unitario IS NULL OR NEW.precio_unitario = 0 THEN
        SET NEW.precio_unitario = (SELECT precio_venta FROM productos WHERE id_producto = NEW.id_producto);
    END IF;
    IF NEW.costo_unitario IS NULL OR NEW.costo_unitario = 0 THEN
        SET NEW.costo_unitario = (SELECT costo_unitario FROM productos WHERE id_producto = NEW.id_producto);
    END IF;
END$$

CREATE TRIGGER trg_detalle_ventas_ai
AFTER INSERT ON detalle_ventas
FOR EACH ROW
BEGIN
    -- Cálculo explícito (no depende del orden de evaluación del SET)
    UPDATE ventas
       SET subtotal = subtotal + NEW.subtotal,
           total    = GREATEST(subtotal + NEW.subtotal - descuento, 0)
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

CREATE TRIGGER trg_movimientos_ai
AFTER INSERT ON movimientos_inventario
FOR EACH ROW
BEGIN
    DECLARE v_signo TINYINT;
    SELECT signo INTO v_signo FROM tipos_movimiento WHERE id_tipo_mov = NEW.id_tipo_mov;

    INSERT INTO inventario (id_sucursal, id_ingrediente, stock_actual)
    VALUES (NEW.id_sucursal, NEW.id_ingrediente, NEW.cantidad * v_signo)
    ON DUPLICATE KEY UPDATE stock_actual = stock_actual + (NEW.cantidad * v_signo);
END$$

CREATE TRIGGER trg_ventas_au
AFTER UPDATE ON ventas
FOR EACH ROW
BEGIN
    IF OLD.estado = 'completada' AND NEW.estado = 'cancelada' THEN
        INSERT INTO movimientos_inventario
               (id_sucursal, id_ingrediente, id_tipo_mov, cantidad, id_usuario, id_venta, observaciones)
        SELECT m.id_sucursal, m.id_ingrediente,
               (SELECT id_tipo_mov FROM tipos_movimiento WHERE clave = 'DEVOLUCION_VENTA'),
               m.cantidad, NEW.id_usuario, m.id_venta,
               CONCAT('Cancelación de venta #', NEW.id_venta)
          FROM movimientos_inventario m
          JOIN tipos_movimiento t ON t.id_tipo_mov = m.id_tipo_mov
         WHERE m.id_venta = NEW.id_venta AND t.clave = 'SALIDA_VENTA';
    END IF;
END$$

CREATE TRIGGER trg_productos_au
AFTER UPDATE ON productos
FOR EACH ROW
BEGIN
    IF OLD.precio_venta <> NEW.precio_venta OR OLD.costo_unitario <> NEW.costo_unitario THEN
        INSERT INTO historial_precios
               (id_producto, precio_anterior, precio_nuevo, costo_anterior, costo_nuevo)
        VALUES (NEW.id_producto, OLD.precio_venta, NEW.precio_venta, OLD.costo_unitario, NEW.costo_unitario);
    END IF;
END$$

DELIMITER ;

-- =====================================================================
-- 10. VISTAS
-- =====================================================================

CREATE OR REPLACE VIEW v_ventas_diarias AS
SELECT DATE(v.fecha_hora)            AS fecha,
       v.id_sucursal,
       COUNT(DISTINCT v.id_venta)    AS tickets,
       SUM(d.cantidad)               AS unidades,
       SUM(d.subtotal)               AS ventas
FROM ventas v
JOIN detalle_ventas d ON d.id_venta = v.id_venta
WHERE v.estado = 'completada'
GROUP BY DATE(v.fecha_hora), v.id_sucursal;

CREATE OR REPLACE VIEW v_tendencia_producto AS
SELECT t.id_producto, t.ingresos_ult30, t.ingresos_prev30,
       CASE WHEN t.ingresos_ult30 >= t.ingresos_prev30 THEN 'up' ELSE 'down' END AS tendencia
FROM (
    SELECT d.id_producto,
           SUM(CASE WHEN v.fecha_hora >= NOW() - INTERVAL 30 DAY
                    THEN d.subtotal ELSE 0 END) AS ingresos_ult30,
           SUM(CASE WHEN v.fecha_hora <  NOW() - INTERVAL 30 DAY
                     AND v.fecha_hora >= NOW() - INTERVAL 60 DAY
                    THEN d.subtotal ELSE 0 END) AS ingresos_prev30
    FROM detalle_ventas d
    JOIN ventas v ON v.id_venta = d.id_venta AND v.estado = 'completada'
    GROUP BY d.id_producto
) t;

CREATE OR REPLACE VIEW v_ventas_por_producto AS
SELECT p.id_producto,
       p.nombre,
       c.nombre                                   AS categoria,
       SUM(d.cantidad)                            AS cantidad,
       SUM(d.subtotal)                            AS ingresos,
       SUM(d.cantidad * d.costo_unitario)         AS costo,
       ROUND((SUM(d.subtotal) - SUM(d.cantidad * d.costo_unitario))
             / NULLIF(SUM(d.subtotal), 0) * 100, 1) AS margen_pct,
       COALESCE(tp.tendencia, 'down')             AS tendencia
FROM detalle_ventas d
JOIN ventas v             ON v.id_venta = d.id_venta AND v.estado = 'completada'
JOIN productos p          ON p.id_producto = d.id_producto
JOIN categorias_producto c ON c.id_categoria = p.id_categoria
LEFT JOIN v_tendencia_producto tp ON tp.id_producto = p.id_producto
GROUP BY p.id_producto, p.nombre, c.nombre, tp.tendencia;

-- Estado con las reglas de la app: stock 0 siempre crítico; mínimo 0 = sin_minimo.
CREATE OR REPLACE VIEW v_estado_inventario AS
SELECT inv.id_sucursal,
       i.id_ingrediente,
       i.nombre,
       um.clave                                        AS unidad,
       inv.stock_actual,
       inv.stock_minimo,
       ROUND(COALESCE(c.consumo_diario, 0), 3)         AS consumo_diario,
       CASE WHEN inv.stock_actual <= 0 THEN 0
            WHEN COALESCE(c.consumo_diario, 0) > 0
            THEN ROUND(inv.stock_actual / c.consumo_diario, 1) END AS dias_agotar,
       CASE
            WHEN inv.stock_actual <= 0 THEN 'critico'
            WHEN inv.stock_minimo <= 0 THEN 'sin_minimo'
            WHEN inv.stock_actual < inv.stock_minimo THEN 'critico'
            WHEN inv.stock_actual < inv.stock_minimo *
                 (SELECT CAST(valor AS DECIMAL(6,2)) FROM parametros_sistema WHERE clave = 'umbral_advertencia')
                 THEN 'advertencia'
            ELSE 'optimo'
       END                                             AS estado
FROM inventario inv
JOIN ingredientes i      ON i.id_ingrediente = inv.id_ingrediente AND i.activo = 1
JOIN unidades_medida um  ON um.id_unidad = i.id_unidad
LEFT JOIN (
    SELECT v.id_sucursal, r.id_ingrediente,
           SUM(d.cantidad * r.cantidad) / 30 AS consumo_diario
    FROM detalle_ventas d
    JOIN ventas v  ON v.id_venta = d.id_venta AND v.estado = 'completada'
    JOIN recetas r ON r.id_producto = d.id_producto
    WHERE v.fecha_hora >= NOW() - INTERVAL 30 DAY
    GROUP BY v.id_sucursal, r.id_ingrediente
) c ON c.id_sucursal = inv.id_sucursal AND c.id_ingrediente = inv.id_ingrediente;

-- Sugerido neto: descuenta lo pendiente de órdenes en borrador/enviada
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

CREATE OR REPLACE VIEW v_pareto_abc AS
SELECT t.id_producto, t.nombre, t.ingresos, t.acum_pct,
       CASE WHEN t.acum_pct <= COALESCE(prm.corte_a, 80) THEN 'A'
            WHEN t.acum_pct <= COALESCE(prm.corte_b, 95) THEN 'B'
            ELSE 'C' END AS clase
FROM (
    SELECT p.id_producto, p.nombre,
           SUM(d.subtotal) AS ingresos,
           ROUND(SUM(SUM(d.subtotal)) OVER (ORDER BY SUM(d.subtotal) DESC, p.id_producto)
                 / SUM(SUM(d.subtotal)) OVER () * 100, 2) AS acum_pct
    FROM detalle_ventas d
    JOIN ventas v    ON v.id_venta = d.id_venta AND v.estado = 'completada'
    JOIN productos p ON p.id_producto = d.id_producto
    GROUP BY p.id_producto, p.nombre
) t
CROSS JOIN (
    SELECT CAST(MAX(CASE WHEN clave = 'abc_corte_a' THEN valor END) AS DECIMAL(6,2)) AS corte_a,
           CAST(MAX(CASE WHEN clave = 'abc_corte_b' THEN valor END) AS DECIMAL(6,2)) AS corte_b
    FROM parametros_sistema
) prm;

CREATE OR REPLACE VIEW v_costo_receta AS
SELECT p.id_producto, p.nombre, p.precio_venta, p.costo_unitario AS costo_estandar,
       ROUND(SUM(r.cantidad * i.costo_unitario), 2) AS costo_receta
FROM productos p
JOIN recetas r      ON r.id_producto = p.id_producto
JOIN ingredientes i ON i.id_ingrediente = r.id_ingrediente
GROUP BY p.id_producto, p.nombre, p.precio_venta, p.costo_unitario;

CREATE OR REPLACE VIEW v_kpi_dashboard AS
SELECT s.id_sucursal,
       COALESCE(h.ventas, 0)   AS ventas_hoy,
       COALESCE(a.ventas, 0)   AS ventas_ayer,
       ROUND((COALESCE(h.ventas, 0) - a.ventas) / NULLIF(a.ventas, 0) * 100, 1) AS variacion_pct,
       ROUND(h.ventas / NULLIF(h.tickets, 0), 2) AS ticket_promedio,
       COALESCE(h.unidades, 0) AS unidades_hoy,
       (SELECT COUNT(*) FROM v_estado_inventario e
         WHERE e.id_sucursal = s.id_sucursal AND e.estado = 'critico') AS stock_en_riesgo
FROM sucursales s
LEFT JOIN v_ventas_diarias h ON h.id_sucursal = s.id_sucursal AND h.fecha = CURDATE()
LEFT JOIN v_ventas_diarias a ON a.id_sucursal = s.id_sucursal AND a.fecha = CURDATE() - INTERVAL 1 DAY;

-- =====================================================================
-- 11. TEMPORADA, CLIMA Y CADUCIDAD
-- =====================================================================

-- Productos en temporada este mes (maneja rangos que cruzan el año, ej. oct–mar)
CREATE OR REPLACE VIEW v_productos_temporada AS
SELECT p.id_producto, p.nombre, c.nombre AS categoria,
       p.mes_inicio_temporada, p.mes_fin_temporada
FROM productos p
JOIN categorias_producto c ON c.id_categoria = p.id_categoria
WHERE p.activo = 1 AND (
    (p.mes_inicio_temporada <= p.mes_fin_temporada
     AND MONTH(CURDATE()) BETWEEN p.mes_inicio_temporada AND p.mes_fin_temporada)
    OR
    (p.mes_inicio_temporada > p.mes_fin_temporada
     AND (MONTH(CURDATE()) >= p.mes_inicio_temporada OR MONTH(CURDATE()) <= p.mes_fin_temporada))
);

-- Vida útil ajustada por el calor de Torreón (solo sin refrigeración)
CREATE OR REPLACE VIEW v_vida_util_clima AS
SELECT p.id_producto, p.nombre, p.vida_anaquel_dias AS vida_base_dias,
       p.requiere_refrigeracion, cl.temp_max_prom AS max_mes_actual,
       CASE WHEN p.requiere_refrigeracion = 1 THEN 1.0
            WHEN cl.temp_max_prom >= 35 THEN
                 CAST((SELECT valor FROM parametros_sistema WHERE clave = 'factor_calor_35') AS DECIMAL(4,2))
            WHEN cl.temp_max_prom >= 30 THEN
                 CAST((SELECT valor FROM parametros_sistema WHERE clave = 'factor_calor_30') AS DECIMAL(4,2))
            ELSE 1.0 END AS factor_clima,
       ROUND(p.vida_anaquel_dias * CASE
            WHEN p.requiere_refrigeracion = 1 THEN 1.0
            WHEN cl.temp_max_prom >= 35 THEN
                 CAST((SELECT valor FROM parametros_sistema WHERE clave = 'factor_calor_35') AS DECIMAL(4,2))
            WHEN cl.temp_max_prom >= 30 THEN
                 CAST((SELECT valor FROM parametros_sistema WHERE clave = 'factor_calor_30') AS DECIMAL(4,2))
            ELSE 1.0 END, 1) AS vida_ajustada_dias,
       CASE WHEN p.requiere_refrigeracion = 0 AND cl.temp_max_prom >= 35
            THEN 1 ELSE 0 END AS riesgo_calor
FROM productos p
CROSS JOIN (SELECT temp_max_prom FROM clima_torreon WHERE mes = MONTH(CURDATE())) cl
WHERE p.activo = 1;

-- Lotes por caducar (alerta de la app) — incluye vencidos con cantidad restante
CREATE OR REPLACE VIEW v_lotes_por_caducar AS
SELECT l.id_lote, l.id_sucursal, i.nombre AS ingrediente, um.clave AS unidad,
       l.cantidad, l.fecha_caducidad,
       DATEDIFF(l.fecha_caducidad, CURDATE()) AS dias_restantes,
       CASE WHEN l.fecha_caducidad < CURDATE() THEN 'vencido'
            WHEN l.fecha_caducidad <= CURDATE() + INTERVAL
                 (SELECT CAST(valor AS UNSIGNED) FROM parametros_sistema
                   WHERE clave = 'alerta_caducidad_dias') DAY THEN 'por_caducar'
            ELSE 'vigente' END AS estado_lote
FROM lotes_inventario l
JOIN ingredientes i     ON i.id_ingrediente = l.id_ingrediente
JOIN unidades_medida um ON um.id_unidad = i.id_unidad
WHERE l.cantidad > 0
  AND l.fecha_caducidad <= CURDATE() + INTERVAL
      (SELECT CAST(valor AS UNSIGNED) FROM parametros_sistema
        WHERE clave = 'alerta_caducidad_dias') DAY
ORDER BY l.fecha_caducidad;

-- =====================================================================
-- 12. PROCEDIMIENTOS ALMACENADOS
-- =====================================================================

DELIMITER $$

-- Edición de stock (doble clic en la tabla de inventario): registra el ajuste en el kardex.
-- Si el ingrediente aún no tiene fila en inventario, parte de 0 en vez de no hacer nada.
CREATE PROCEDURE sp_ajustar_stock(
    IN p_id_sucursal   INT UNSIGNED,
    IN p_id_ingrediente INT UNSIGNED,
    IN p_nuevo_stock   DECIMAL(12,3),
    IN p_id_usuario    INT UNSIGNED,
    IN p_observaciones VARCHAR(200)
)
BEGIN
    DECLARE v_actual DECIMAL(12,3) DEFAULT 0;
    DECLARE v_delta  DECIMAL(12,3);

    IF p_nuevo_stock < 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El stock no puede ser negativo';
    END IF;

    SELECT COALESCE(stock_actual, 0) INTO v_actual
      FROM inventario
     WHERE id_sucursal = p_id_sucursal AND id_ingrediente = p_id_ingrediente;

    SET v_delta = p_nuevo_stock - v_actual;

    IF v_delta <> 0 THEN
        INSERT INTO movimientos_inventario
               (id_sucursal, id_ingrediente, id_tipo_mov, cantidad, id_usuario, observaciones)
        VALUES (p_id_sucursal, p_id_ingrediente,
                (SELECT id_tipo_mov FROM tipos_movimiento
                  WHERE clave = IF(v_delta > 0, 'AJUSTE_POSITIVO', 'AJUSTE_NEGATIVO')),
                ABS(v_delta), p_id_usuario, COALESCE(p_observaciones, 'Ajuste manual desde inventario'));
    END IF;
END$$

-- Registrar merma (desperdicio).
-- NOTA: permite dejar el stock en negativo; si prefieres bloquearlo, agrega
-- SIGNAL cuando (stock_actual - p_cantidad) < 0.
CREATE PROCEDURE sp_registrar_merma(
    IN p_id_sucursal    INT UNSIGNED,
    IN p_id_ingrediente INT UNSIGNED,
    IN p_cantidad       DECIMAL(12,3),
    IN p_id_usuario     INT UNSIGNED,
    IN p_motivo         VARCHAR(200)
)
BEGIN
    INSERT INTO movimientos_inventario
           (id_sucursal, id_ingrediente, id_tipo_mov, cantidad, id_usuario, observaciones)
    VALUES (p_id_sucursal, p_id_ingrediente,
            (SELECT id_tipo_mov FROM tipos_movimiento WHERE clave = 'MERMA'),
            p_cantidad, p_id_usuario, p_motivo);
END$$

-- Da de baja lotes vencidos como merma por caducidad
CREATE PROCEDURE sp_purgar_caducados(
    IN p_id_sucursal INT UNSIGNED,
    IN p_id_usuario  INT UNSIGNED
)
BEGIN
    INSERT INTO movimientos_inventario
           (id_sucursal, id_ingrediente, id_tipo_mov, cantidad, id_usuario, observaciones)
    SELECT l.id_sucursal, l.id_ingrediente,
           (SELECT id_tipo_mov FROM tipos_movimiento WHERE clave = 'CADUCIDAD'),
           l.cantidad, p_id_usuario,
           CONCAT('Lote #', l.id_lote, ' vencido el ', l.fecha_caducidad)
      FROM lotes_inventario l
     WHERE l.id_sucursal = p_id_sucursal
       AND l.cantidad > 0 AND l.fecha_caducidad < CURDATE();

    UPDATE lotes_inventario
       SET cantidad = 0
     WHERE id_sucursal = p_id_sucursal
       AND cantidad > 0 AND fecha_caducidad < CURDATE();

    SELECT ROW_COUNT() AS lotes_purgados;
END$$

-- Botón "Generar orden de compra": crea una orden en borrador por proveedor con lo sugerido
CREATE PROCEDURE sp_generar_ordenes_compra(
    IN p_id_sucursal INT UNSIGNED,
    IN p_id_usuario  INT UNSIGNED
)
BEGIN
    DECLARE v_done      INT DEFAULT 0;
    DECLARE v_proveedor INT UNSIGNED;
    DECLARE v_orden     INT UNSIGNED;
    DECLARE v_ultimo    INT UNSIGNED;
    DECLARE cur CURSOR FOR
        SELECT DISTINCT id_proveedor
          FROM v_orden_compra_sugerida
         WHERE id_sucursal = p_id_sucursal AND sugerido > 0 AND id_proveedor IS NOT NULL;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_done = 1;

    SELECT COALESCE(MAX(id_orden), 0) INTO v_ultimo FROM ordenes_compra;

    OPEN cur;
    leer: LOOP
        FETCH cur INTO v_proveedor;
        IF v_done = 1 THEN LEAVE leer; END IF;

        INSERT INTO ordenes_compra (id_sucursal, id_proveedor, id_usuario)
        VALUES (p_id_sucursal, v_proveedor, p_id_usuario);
        SET v_orden = LAST_INSERT_ID();

        INSERT INTO detalle_ordenes_compra (id_orden, id_ingrediente, cantidad_solicitada, precio_unitario)
        SELECT v_orden, id_ingrediente, sugerido, precio_compra
          FROM v_orden_compra_sugerida
         WHERE id_sucursal = p_id_sucursal AND id_proveedor = v_proveedor AND sugerido > 0;

        UPDATE ordenes_compra
           SET total = (SELECT SUM(cantidad_solicitada * precio_unitario)
                          FROM detalle_ordenes_compra WHERE id_orden = v_orden)
         WHERE id_orden = v_orden;
    END LOOP;
    CLOSE cur;

    SELECT * FROM ordenes_compra WHERE id_orden > v_ultimo AND id_sucursal = p_id_sucursal;
END$$

-- Recepción de mercancía: da entrada al inventario y cierra la orden
CREATE PROCEDURE sp_recibir_orden_compra(
    IN p_id_orden   INT UNSIGNED,
    IN p_id_usuario INT UNSIGNED
)
BEGIN
    DECLARE v_estado VARCHAR(20);
    DECLARE v_sucursal INT UNSIGNED;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    SELECT estado, id_sucursal INTO v_estado, v_sucursal
      FROM ordenes_compra WHERE id_orden = p_id_orden FOR UPDATE;

    IF v_estado IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La orden de compra no existe';
    ELSEIF v_estado NOT IN ('borrador', 'enviada') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La orden ya fue recibida o cancelada';
    END IF;

    -- si no se capturó lo recibido, se asume que llegó completo
    UPDATE detalle_ordenes_compra
       SET cantidad_recibida = cantidad_solicitada
     WHERE id_orden = p_id_orden AND cantidad_recibida IS NULL;

    INSERT INTO movimientos_inventario
           (id_sucursal, id_ingrediente, id_tipo_mov, cantidad, id_usuario, id_orden, observaciones)
    SELECT v_sucursal, d.id_ingrediente,
           (SELECT id_tipo_mov FROM tipos_movimiento WHERE clave = 'ENTRADA_COMPRA'),
           d.cantidad_recibida, p_id_usuario, p_id_orden,
           CONCAT('Recepción de orden #', p_id_orden)
      FROM detalle_ordenes_compra d
     WHERE d.id_orden = p_id_orden AND d.cantidad_recibida > 0;

    UPDATE ordenes_compra
       SET estado = 'recibida', fecha_recepcion = NOW()
     WHERE id_orden = p_id_orden;

    COMMIT;
END$$

-- Datos de prueba: genera ventas aleatorias de los últimos N días (NO toca el inventario)
-- Uso:  CALL sp_generar_ventas_demo(60);
-- NOTA: como no genera kardex, el consumo por recetas existe pero dias_agotar
-- saldrá NULL ("—") hasta que haya movimientos reales de inventario.
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
        -- más movimiento jueves a sábado
        SET v_tickets = 25 + FLOOR(RAND() * 20)
                        + IF(DAYOFWEEK(v_fecha) IN (5, 6, 7), 12, 0);
        SET v_t = 0;
        WHILE v_t < v_tickets DO
            INSERT INTO ventas (id_sucursal, id_usuario, id_metodo_pago, fecha_hora)
            VALUES (v_suc, v_usr, 1 + FLOOR(RAND() * 3),
                    TIMESTAMP(v_fecha, SEC_TO_TIME(7 * 3600 + FLOOR(RAND() * 13 * 3600))));
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

-- =====================================================================
-- 13. USUARIO DE APLICACIÓN (opcional; cambia la contraseña antes de ejecutar)
-- =====================================================================
-- CREATE USER IF NOT EXISTS 'cosecha_app'@'localhost' IDENTIFIED BY 'CAMBIAR_CONTRASENA_SEGURA';
-- GRANT SELECT, INSERT, UPDATE, EXECUTE ON frutidata.* TO 'cosecha_app'@'localhost';
-- FLUSH PRIVILEGES;
