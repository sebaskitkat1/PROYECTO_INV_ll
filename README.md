# CaféData — Sistema de Análisis de Datos (Escritorio)

Adaptación a aplicación de escritorio (Python + PySide6) del prototipo
web original. Es una **base funcional**, pensada para irse ampliando
progresivamente: navegación entre pantallas, KPIs, tablas y gráficas
ya funcionan con datos de ejemplo; lo que falta (conectar datos reales,
filtros funcionales, autenticación real, etc.) queda señalado como
siguiente paso.

## Instalación

Requiere Python 3.10+.

```bash
python -m venv venv
source venv/bin/activate      # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecución

```bash
python main.py
```

## Estructura del proyecto

```
main.py                        Punto de entrada
app/
  main_window.py                Ventana principal y navegación (QStackedWidget)
  styles.py                     Paleta de colores y hoja de estilos (QSS) global
  data/
    mock_data.py                 Datos de ejemplo (equivalente a mockData.ts)
  widgets/
    kpi_card.py                  Tarjeta de indicador (KPI) reutilizable
    nav_bar.py                   Barra superior de navegación reutilizable
    mpl_canvas.py                 Lienzo de matplotlib embebido y estilizado
  screens/
    login_screen.py               Login + carga de CSV
    dashboard_screen.py           Resumen del día, KPIs y gráficas
    sales_screen.py               Análisis de ventas (tabla + dispersión)
    inventory_screen.py           Inventario (tabla + rotación + Pareto/ABC)
    prediction_screen.py          Predicción de demanda a 30 días
```

## Qué ya funciona

- Navegación completa entre las 5 pantallas (Login, Dashboard, Ventas,
  Inventario, Predicción), replicando la estructura del prototipo web.
- Selector de archivo CSV en el login: lo lee con `pandas` y valida que
  se pueda abrir (por ahora las pantallas siguen mostrando datos de
  ejemplo; conectar ese CSV a las gráficas es el siguiente paso natural).
- Todas las gráficas (líneas, barras, dispersión) con `matplotlib`
  embebido, replicando los datos y la paleta de colores del original.
- Tablas de ventas, inventario y predicción con formato, colores por
  estado/tendencia y orden por columna (inventario).
- Diseño visual (colores, tipografía, tarjetas) tomado del prototipo
  Figma/React (`#1F4E78` como color primario, tarjetas con sombra sutil, etc.).

## Próximos pasos sugeridos

1. **Conectar datos reales**: reemplazar las funciones de
   `app/data/mock_data.py` por otras que lean del CSV cargado en el
   login (`self.loaded_dataframe` en `LoginScreen`) o de una base de
   datos (ya trabajas con MySQL/Oracle/PostgreSQL, así que un módulo
   `app/data/db_source.py` con la misma interfaz encajaría bien aquí).
2. **Filtros funcionales** en la pantalla de Ventas (por ahora los
   combos de período/categoría no re-consultan los datos).
3. **Autenticación real** en el login (por ahora solo valida que los
   campos no estén vacíos).
4. **Persistencia de sesión/estado** entre pantallas si se necesita
   mantener filtros o selección al navegar.
5. **Predicción real**: sustituir los datos de ejemplo de
   `prediction_screen.py` por un modelo simple (regresión, promedio
   móvil) sobre los datos cargados.
6. **Empaquetado**: cuando esté listo para distribuir, `pyinstaller`
   permite generar un `.exe`/binario standalone a partir de `main.py`.
