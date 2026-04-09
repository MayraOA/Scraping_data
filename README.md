# Scraping_data

Este repositorio contiene dos tareas de ciencia de datos usando Python.

## Tarea 1 — Web Scraping: Resultados de Admisión UNMSM

### ¿Qué hace?
Extrae automáticamente los resultados del examen de admisión de todas las carreras de la UNMSM usando Selenium, y los consolida en un archivo Excel.

### ¿Cómo instalar las dependencias?
```bash
pip install selenium pandas openpyxl
```

### ¿Cómo correrlo?
```bash
python scraper.py
```

### ¿Qué contiene el output?
El archivo `output/resultados_sanmarcos.xlsx` con todos los postulantes de todas las carreras.

---

## Tarea 2 — API REST: RAWG Video Games Database

### ¿Qué hace?
Consulta la API de RAWG para explorar, comparar y analizar datos de videojuegos por plataforma, género y año.

### ¿Cómo instalar las dependencias?
```bash
pip install requests pandas
```

### ¿Cómo correrlo?
Abre `api/tarea_rawg_api.ipynb` en Jupyter Notebook y ejecuta todas las celdas.

### ¿Qué contiene el output?
El archivo `api/output/top20_rawg.csv` con los 20 mejores juegos de todos los tiempos.