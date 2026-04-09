"""
scraper.py
Web Scraper - Resultados Examen de Admisión UNMSM 2026-II

Estrategia: los datos están en el HTML estático (no Ajax).
- data-score  → Puntaje (atributo del <td>)
- data-merit  → Mérito E.P (atributo del <td>)
- data-auth   → Nombres/Escuela en Base64 (atributo del <span>)
Se usa requests + BeautifulSoup para leer el HTML completo,
y Selenium solo para obtener los links de carreras.
"""

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import base64
import time
import os

BASE_URL = "https://admision.unmsm.edu.pe/Website20262/A/A.html"
OUTPUT_PATH = "output/resultados_sanmarcos.xlsx"
COLUMNAS = ["Código", "Apellidos y Nombres", "Escuela", "Puntaje", "Mérito E.P", "Observación"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=options)


def get_career_links(driver):
    """Usa Selenium solo para obtener los links de carreras."""
    driver.get(BASE_URL)
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "table a"))
    )
    time.sleep(2)
    links = driver.find_elements(By.CSS_SELECTOR, "table a")
    career_links = []
    seen = set()
    for link in links:
        href = link.get_attribute("href")
        text = link.text.strip()
        if href and "results.html" in href and href not in seen:
            career_links.append({"name": text, "url": href})
            seen.add(href)
    print(f"✅ Se encontraron {len(career_links)} carreras.")
    return career_links


def decode_auth(value):
    """Decodifica un valor Base64 de data-auth."""
    try:
        # Agregar padding si falta
        padded = value + "=" * (-len(value) % 4)
        return base64.b64decode(padded).decode("utf-8")
    except Exception:
        return value  # Si falla, devolver el valor original


def scrape_career_requests(career):
    """
    Descarga el HTML de la carrera con requests y parsea con BeautifulSoup.
    Lee TODOS los <tr> del HTML fuente (no solo los visibles en el DOM),
    leyendo data-score, data-merit y data-auth directamente.
    """
    try:
        resp = requests.get(career["url"], headers=HEADERS, timeout=30)
        resp.raise_for_status()
        # La página usa UTF-8
        resp.encoding = "utf-8"

        soup = BeautifulSoup(resp.text, "html.parser")

        # Buscar todas las filas de la tabla (incluyendo las paginadas)
        rows = soup.select("table tbody tr")
        if not rows:
            print(f"  ⚠️  Sin filas en HTML: {career['name']}")
            return pd.DataFrame()

        data = []
        for tr in rows:
            cells = tr.find_all("td")
            if len(cells) < 4:
                continue

            # Código — texto directo
            codigo = cells[0].get_text(strip=True)
            if not codigo or codigo == "Código":
                continue

            # Apellidos y Nombres — span[data-auth] en Base64
            span1 = cells[1].find("span", attrs={"data-auth": True})
            nombre = decode_auth(span1["data-auth"]) if span1 else cells[1].get_text(strip=True)

            # Escuela — span[data-auth] en Base64
            span2 = cells[2].find("span", attrs={"data-auth": True})
            escuela = decode_auth(span2["data-auth"]) if span2 else cells[2].get_text(strip=True)

            # Puntaje — atributo data-score del <td>
            puntaje = cells[3].get("data-score", "").strip()

            # Mérito E.P — atributo data-merit del <td>
            merito = cells[4].get("data-merit", "").strip() if len(cells) > 4 else ""

            # Observación — texto directo
            observacion = cells[5].get_text(strip=True) if len(cells) > 5 else ""

            data.append([codigo, nombre, escuela, puntaje, merito, observacion])

        if not data:
            print(f"  ⚠️  Sin datos parseados: {career['name']}")
            return pd.DataFrame()

        df = pd.DataFrame(data, columns=COLUMNAS)
        df = df[df["Código"].str.strip() != ""]
        df = df.reset_index(drop=True)
        print(f"  ✅ {career['name']}: {len(df)} registros")
        return df

    except Exception as e:
        print(f"  ❌ Error en {career['name']}: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def save_to_excel(all_dfs, path):
    final_df = pd.concat(all_dfs, ignore_index=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        final_df.to_excel(writer, index=False, sheet_name="Todos")
        ws = writer.sheets["Todos"]
        col_widths = {"A": 12, "B": 38, "C": 30, "D": 12, "E": 12, "F": 45}
        for col, width in col_widths.items():
            ws.column_dimensions[col].width = width
        ws.freeze_panes = "A2"
    print(f"  → Excel guardado en '{path}' ({len(final_df)} registros totales)")
    return final_df


def main():
    os.makedirs("output", exist_ok=True)
    driver = setup_driver()

    try:
        print("🔍 Obteniendo links de carreras...")
        careers = get_career_links(driver)
        if not careers:
            print("⚠️  No se encontraron carreras.")
            return
    finally:
        driver.quit()  # Selenium ya no se necesita

    all_dfs = []
    for i, career in enumerate(careers, 1):
        print(f"\n[{i}/{len(careers)}] {career['name']}")
        df = scrape_career_requests(career)
        if not df.empty:
            all_dfs.append(df)
        time.sleep(0.3)  # Pausa cortés entre requests

    if all_dfs:
        final_df = save_to_excel(all_dfs, OUTPUT_PATH)
        print(f"\n🎉 ¡Listo! {len(final_df)} registros totales en '{OUTPUT_PATH}'")
    else:
        print("\n⚠️  No se extrajo ningún dato.")


if __name__ == "__main__":
    main()
