# Diagrama entidad-relación — `frutidata`

Diagrama de las **20 tablas esenciales** para explicar el funcionamiento de la
frutería: 18 del flujo operativo más 2 catálogos de apoyo (`categorias_producto`
y `unidades_medida`). Está dividido en cinco módulos para que cada vista sea
legible; juntos forman el mismo modelo entidad-relación. Una tabla puede
aparecer en más de un módulo para mostrar sus relaciones, pero se cuenta una
sola vez.

> **Cómo leerlo:** `PK` = llave primaria, `FK` = llave foránea, `UK` = valor
> único. Las líneas con `||--o{` significan uno a muchos. Las tablas puente
> (`recetas`, `detalle_ventas`, `detalle_ordenes_compra`) resuelven relaciones
> muchos a muchos.

## 1. Catálogo y ventas

```mermaid
erDiagram
    ROLES ||--o{ USUARIOS : "asigna"
    USUARIOS ||--o{ VENTAS : "cobra"
    SUCURSALES ||--o{ VENTAS : "opera"
    CATEGORIAS_PRODUCTO ||--o{ PRODUCTOS : "clasifica"
    UNIDADES_MEDIDA ||--o{ PRODUCTOS : "mide"
    PRODUCTOS ||--o{ DETALLE_VENTAS : "se vende"
    VENTAS ||--|{ DETALLE_VENTAS : "contiene"

    ROLES {
        tinyint id_rol PK
        varchar nombre
    }
    USUARIOS {
        int id_usuario PK
        tinyint id_rol FK
        varchar nombre
        varchar correo UK
        boolean activo
    }
    SUCURSALES {
        int id_sucursal PK
        varchar nombre
        boolean activa
    }
    CATEGORIAS_PRODUCTO {
        tinyint id_categoria PK
        varchar nombre
    }
    UNIDADES_MEDIDA {
        tinyint id_unidad PK
        varchar clave
        varchar nombre
    }
    PRODUCTOS {
        int id_producto PK
        tinyint id_categoria FK
        tinyint id_unidad FK
        varchar nombre
        decimal precio_venta
        decimal costo_unitario
        int vida_anaquel_dias
        boolean activo
    }
    VENTAS {
        bigint id_venta PK
        int id_sucursal FK
        int id_usuario FK
        int id_cliente FK
        tinyint id_metodo_pago FK
        datetime fecha_hora
        decimal total
        enum estado
    }
    DETALLE_VENTAS {
        bigint id_detalle PK
        bigint id_venta FK
        int id_producto FK
        int cantidad
        decimal precio_unitario
        decimal costo_unitario
        decimal subtotal
    }
```

**Qué explica:** una venta es una cabecera (`ventas`) con varios renglones
(`detalle_ventas`). Cada renglón apunta a un producto y guarda el precio y el
costo del momento; así el histórico no cambia si después se actualiza el
catálogo. `clientes` y `metodos_pago` se omiten porque son catálogos opcionales.

## 2. Recetas: productos e ingredientes

```mermaid
erDiagram
    PRODUCTOS ||--o{ RECETAS : "compone"
    INGREDIENTES ||--o{ RECETAS : "ingrediente"

    PRODUCTOS {
        int id_producto PK
        varchar nombre
        decimal precio_venta
    }
    INGREDIENTES {
        int id_ingrediente PK
        tinyint id_categoria_ing FK
        tinyint id_unidad FK
        varchar nombre
        decimal costo_unitario
        int vida_anaquel_dias
        boolean activo
    }
    RECETAS {
        int id_producto PK
        int id_ingrediente PK
        decimal cantidad
    }
```

**Qué explica:** un producto vendible (por ejemplo, un jugo) consume varios
ingredientes; `recetas` guarda la cantidad de cada insumo por unidad vendida.
Las frutas y verduras que se venden tal cual no necesitan receta.

## 3. Inventario con caducidad

```mermaid
erDiagram
    SUCURSALES ||--o{ INVENTARIO : "almacena"
    INGREDIENTES ||--o{ INVENTARIO : "stock"
    SUCURSALES ||--o{ LOTES_INVENTARIO : "lote"
    INGREDIENTES ||--o{ LOTES_INVENTARIO : "lote"
    SUCURSALES ||--o{ MOVIMIENTOS_INVENTARIO : "mueve"
    INGREDIENTES ||--o{ MOVIMIENTOS_INVENTARIO : "mueve"
    USUARIOS ||--o{ MOVIMIENTOS_INVENTARIO : "registra"
    VENTAS ||--o{ MOVIMIENTOS_INVENTARIO : "descuenta"

    SUCURSALES {
        int id_sucursal PK
        varchar nombre
    }
    INGREDIENTES {
        int id_ingrediente PK
        varchar nombre
        decimal costo_unitario
        int vida_anaquel_dias
    }
    INVENTARIO {
        int id_sucursal PK
        int id_ingrediente PK
        decimal stock_actual
        decimal stock_minimo
        datetime updated_at
    }
    LOTES_INVENTARIO {
        int id_lote PK
        int id_sucursal FK
        int id_ingrediente FK
        decimal cantidad
        date fecha_ingreso
        date fecha_caducidad
        decimal costo_unitario
    }
    MOVIMIENTOS_INVENTARIO {
        bigint id_movimiento PK
        int id_sucursal FK
        int id_ingrediente FK
        tinyint id_tipo_mov FK
        decimal cantidad
        datetime fecha_hora
        int id_usuario FK
        bigint id_venta FK
        int id_orden FK
    }
    USUARIOS {
        int id_usuario PK
        varchar nombre
    }
    VENTAS {
        bigint id_venta PK
        datetime fecha_hora
    }
```

**Qué explica:** `inventario` es el saldo agregado por sucursal e ingrediente;
`lotes_inventario` guarda cada ingreso con su fecha de caducidad (para FEFO);
`movimientos_inventario` es el kardex: entradas, salidas, mermas y ajustes. El
tipo de movimiento (`tipos_movimiento`) se omite como catálogo, pero `id_tipo_mov`
dice si suma o resta.

## 4. Compras y proveedores

```mermaid
erDiagram
    PROVEEDORES ||--o{ ORDENES_COMPRA : "surte"
    SUCURSALES ||--o{ ORDENES_COMPRA : "solicita"
    USUARIOS ||--o{ ORDENES_COMPRA : "crea"
    ORDENES_COMPRA ||--|{ DETALLE_ORDENES_COMPRA : "detalla"
    INGREDIENTES ||--o{ DETALLE_ORDENES_COMPRA : "pide"

    PROVEEDORES {
        int id_proveedor PK
        varchar nombre
        int dias_entrega
        boolean activo
    }
    SUCURSALES {
        int id_sucursal PK
        varchar nombre
    }
    USUARIOS {
        int id_usuario PK
        varchar nombre
    }
    ORDENES_COMPRA {
        int id_orden PK
        int id_sucursal FK
        int id_proveedor FK
        int id_usuario FK
        datetime fecha_creacion
        datetime fecha_recepcion
        enum estado
        decimal total
    }
    DETALLE_ORDENES_COMPRA {
        int id_detalle PK
        int id_orden FK
        int id_ingrediente FK
        decimal cantidad_solicitada
        decimal cantidad_recibida
        decimal precio_unitario
    }
    INGREDIENTES {
        int id_ingrediente PK
        varchar nombre
        decimal costo_unitario
    }
```

**Qué explica:** una orden de compra tiene cabecera (proveedor, sucursal,
usuario, estado) y detalle por ingrediente. Al recibirla, la app actualiza
`inventario`, crea lotes y registra el movimiento en el kardex.

## 5. Pronóstico

```mermaid
erDiagram
    MODELOS_PRONOSTICO ||--o{ PRONOSTICOS : "ejecuta"
    SUCURSALES ||--o{ PRONOSTICOS : "genera"
    USUARIOS ||--o{ PRONOSTICOS : "solicita"
    PRONOSTICOS ||--o{ PRONOSTICO_DIARIO : "serie diaria"
    PRONOSTICOS ||--o{ PRONOSTICO_PRODUCTO : "detalle por producto"
    PRODUCTOS ||--o{ PRONOSTICO_PRODUCTO : "producto"

    MODELOS_PRONOSTICO {
        tinyint id_modelo PK
        varchar nombre
        json parametros
    }
    PRONOSTICOS {
        int id_pronostico PK
        tinyint id_modelo FK
        int id_sucursal FK
        int id_usuario FK
        datetime fecha_generacion
        int horizonte_dias
        decimal mae_modelo
        decimal mae_naive
        decimal mae_ma7
        boolean es_preliminar
    }
    PRONOSTICO_DIARIO {
        int id_pronostico PK
        date fecha PK
        decimal ventas_estimadas
    }
    PRONOSTICO_PRODUCTO {
        int id_pronostico PK
        int id_producto PK
        decimal ingresos_actual
        decimal ingresos_predicho
        decimal crecimiento_pct
    }
    PRODUCTOS {
        int id_producto PK
        varchar nombre
    }
    SUCURSALES {
        int id_sucursal PK
        varchar nombre
    }
    USUARIOS {
        int id_usuario PK
        varchar nombre
    }
```

**Qué explica:** cada corrida de pronóstico se guarda en `pronosticos` con el
modelo, la sucursal, el usuario, el horizonte y los errores MAE. La serie diaria
va en `pronostico_diario` y el detalle por producto en `pronostico_producto`.

> **Ojo:** estas tablas **guardan** el pronóstico cuando el usuario presiona
> “Guardar”. La simulación de la temporada **no las lee**: recalcula el
> pronóstico en memoria, día a día, con la historia hasta ayer.

## Flujo completo en una frase

`productos` / `ingredientes` → `ventas` / `detalle_ventas` → `inventario` /
`lotes_inventario` / `movimientos_inventario` → `ordenes_compra` /
`detalle_ordenes_compra` → `pronosticos` / `pronostico_diario` /
`pronostico_producto`.

## Tablas omitidas (y por qué)

| Tabla omitida | Motivo |
|---|---|
| `categorias_ingrediente` | Catálogo de una columna; se explica como atributo de `ingredientes`. |
| `clientes`, `metodos_pago` | Catálogos opcionales de la venta; no cambian el flujo de inventario. |
| `historial_precios` | Auditoría de cambios de precio; no participa en la operación diaria. |
| `tipos_movimiento` | Catálogo del kardex (`entrada`, `salida`, `merma`, `ajuste`); se explica como atributo. |
| `bitacora_accesos` | Auditoría de login; no es parte del flujo comercial. |
| `parametros_sistema`, `clima_torreon` | Configuración y referencia; el pronóstico actual no los usa. |
| `ingrediente_proveedor` | Tabla puente de precios por proveedor; se puede mencionar sin dibujarla. |
| `v_*` (vistas) | No son tablas; son consultas de reporte (KPIs, ventas diarias, inventario, Pareto). |
