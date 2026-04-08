"""
scraper.py
Web Scraper - Resultados Examen de Admisión UNMSM
Extrae todas las carreras y todos los postulantes, guarda en Excel.
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import pandas as pd
import time
import os

BASE_URL = "https://admision.unmsm.edu.pe/Website20262/A/A.html"
OUTPUT_PATH = "output/resultados_sanmarcos.xlsx"

def setup_driver():
    options = webdriver.ChromeOptions()
    # Comenta la línea de abajo si quieres VER el navegador abrirse (útil para debug)
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # Deshabilita la protección de selección de texto
    options.add_argument("--disable-web-security")
    driver = webdriver.Chrome(options=options)
    return driver

def get_career_links(driver):
    """Extrae todos los links de carreras de la página principal."""
    driver.get(BASE_URL)
    wait = WebDriverWait(driver, 20)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "a")))
    time.sleep(3)

    links = driver.find_elements(By.TAG_NAME, "a")
    career_links = []
    seen_urls = set()

    for link in links:
        href = link.get_attribute("href")
        text = link.text.strip()
        if (href and 
            href not in seen_urls and
            "admision.unmsm.edu.pe" in href and 
            "A.html" not in href and 
            text and len(text) > 3):
            career_links.append({"name": text, "url": href})
            seen_urls.add(href)

    print(f"✅ Se encontraron {len(career_links)} carreras.")
    return career_links

def extract_table_data(driver):
    """
    Extrae TODOS los registros de una tabla DataTables.
    Primero intenta mostrar todos con el selector,
    si no, va página por página.
    """
    all_rows = []

    # MÉTODO 1: Intentar cambiar el selector a "All" (-1)
    try:
        select_elements = driver.find_elements(By.CSS_SELECTOR, "select[name*='length'], select[name*='Length']")
        if select_elements:
            select = Select(select_elements[0])
            # Intentar seleccionar la opción con el mayor valor (todos los registros)
            options = [o.get_attribute("value") for o in select.options]
            print(f"    Opciones de paginación: {options}")
            if "-1" in options:
                select.select_by_value("-1")
            else:
                # Seleccionar el valor más grande disponible
                max_val = max([int(o) for o in options if o.lstrip('-').isdigit()])
                select.select_by_value(str(max_val))
            time.sleep(3)

            # Leer toda la tabla de una vez
            tables = pd.read_html(driver.page_source)
            if tables:
                return tables[0]
    except Exception as e:
        print(f"    Método 1 falló: {e}. Intentando paginación...")

    # MÉTODO 2: Ir página por página haciendo clic en "Siguiente"
    page_num = 1
    while True:
        try:
            # Esperar que la tabla cargue
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
            )
            time.sleep(1.5)

            # Extraer filas de la página actual usando JavaScript
            # (esto evita el problema de texto "encriptado" / no seleccionable)
            rows = driver.execute_script("""
                var table = document.querySelector('table');
                if (!table) return [];
                var rows = [];
                var trs = table.querySelectorAll('tbody tr');
                trs.forEach(function(tr) {
                    var cells = [];
                    tr.querySelectorAll('td').forEach(function(td) {
                        cells.push(td.innerText || td.textContent);
                    });
                    if (cells.length > 0) rows.push(cells);
                });
                return rows;
            """)

            if rows:
                all_rows.extend(rows)
                print(f"    Página {page_num}: {len(rows)} registros extraídos")

            # Buscar botón "Siguiente" / "Next"
            next_buttons = driver.find_elements(
                By.CSS_SELECTOR, 
                "a.paginate_button.next:not(.disabled), li.next:not(.disabled) a"
            )

            if not next_buttons or "disabled" in next_buttons[0].get_attribute("class"):
                print(f"    ✅ Última página alcanzada ({page_num} páginas en total)")
                break

            next_buttons[0].click()
            page_num += 1
            time.sleep(1.5)

        except Exception as e:
            print(f"    Error en página {page_num}: {e}")
            break

    if not all_rows:
        return pd.DataFrame()

    # Obtener headers de la tabla
    try:
        headers = driver.execute_script("""
            var table = document.querySelector('table');
            if (!table) return [];
            var headers = [];
            table.querySelectorAll('thead th').forEach(function(th) {
                headers.push(th.innerText || th.textContent);
            });
            return headers;
        """)
        if headers and len(headers) == len(all_rows[0]):
            return pd.DataFrame(all_rows, columns=headers)
    except:
        pass

    return pd.DataFrame(all_rows)

def scrape_career(driver, career):
    """Scrapea todos los postulantes de una carrera."""
    try:
        driver.get(career["url"])
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )
        time.sleep(2)

        df = extract_table_data(driver)

        if df.empty:
            print(f"  ⚠️  Sin datos: {career['name']}")
            return pd.DataFrame()

        df["Carrera"] = career["name"]
        df["URL"] = career["url"]
        print(f"  ✅ {career['name']}: {len(df)} postulantes")
        return df

    except Exception as e:
        print(f"  ❌ Error en {career['name']}: {e}")
        return pd.DataFrame()

def main():
    os.makedirs("output", exist_ok=True)
    driver = setup_driver()

    try:
        print("🔍 Obteniendo links de carreras...")
        careers = get_career_links(driver)

        if not careers:
            print("⚠️  No se encontraron carreras.")
            return

        all_data = []
        for i, career in enumerate(careers, 1):
            print(f"\n[{i}/{len(careers)}] Procesando: {career['name']}")
            df = scrape_career(driver, career)
            if not df.empty:
                all_data.append(df)

        if all_data:
            final_df = pd.concat(all_data, ignore_index=True)
            final_df.to_excel(OUTPUT_PATH, index=False)
            print(f"\n🎉 ¡Listo! {len(final_df)} registros totales guardados en '{OUTPUT_PATH}'")
        else:
            print("\n⚠️  No se extrajo ningún dato.")

    except Exception as e:
        print(f"Error fatal: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()