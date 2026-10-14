# Simulación con-vs-sin app

Compara dos formas de pedir, con la **misma demanda real** de la base:

- **Sin app**: lo del mismo día de la semana pasada.
- **Con app**: pronóstico a 1 día + cuantil newsvendor de residuales
  (margen alto = se pide agresivo; caro y perecedero = conservador).

La política se elige **por dinero en una mitad de calibración** y se evalúa
en la otra mitad no vista. La utilidad cuenta el inventario final a costo
(`utilidad_cierre`); la gráfica acumula la utilidad económica diaria, que
cuadra con el cierre por construcción.

El inventario se simula día a día, FIFO, con la vida útil real de cada
producto (`vida_anaquel_dias`). Lo caducado es merma a costo; lo no
vendido por falta de stock es venta perdida a precio lleno.

## Correr

Desde la raíz del repo (necesita MySQL con datos; usa el `.env`):

```powershell
python scripts/simulacion/run_simulacion.py
python -m unittest tests.test_simulacion
```

Guarda `resultados/utilidad_acumulada.png`.

## Supuestos (dilos en voz alta al presentar)

1. Compra matutina: el pedido llega el mismo día (lead time 0).
2. FIFO estricto, sin sustitución entre productos.
3. Ruido Monte Carlo = residuales reales por día de semana (no iid).
4. Precios, costos y vidas útiles salen de la base, no inventados.
5. Los datos demo son sintéticos (`RAND()` con boost jue–sáb): esto valida
   la **metodología**, no la superioridad del modelo. Con historial real,
   los números mandan.

## Qué mirar

- `MAE mod < MAE base` por producto: el modelo anticipa mejor.
- `merma s/app vs c/app` y `util +`: el dinero.
- Monte Carlo del top 1: rango P10–P90 de ahorro de merma y utilidad extra.
