import os
import re  
import time
import random
import urllib.parse
import numpy as np
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ===========================================================
# =================== Parameters for data fetching ==========
# ===========================================================

TYPICAL_ELEMENTS = ['Fe', 'C', 'Si', 'Ni', 'Be']
WAVELENGTH_MIN = 200.0
WAVELENGTH_MAX = 600.0
RESOLUTION = 1000
GRID_STEP = 0.05
PLASMA_TEMP = 1
ELECTRON_DENSITY = 1e17
DATASET_DIR = "para1"
NUM_SAMPLES = 1

# ===============================================
# ============ Selenium Scraper =================
# ===============================================

class SeleniumNISTScraper:
    def __init__(self, elements, percentages, resolution, low_w, upper_w, Te, Ne, driver):
        self.base_url = "https://physics.nist.gov/cgi-bin/ASD/lines1.pl"
        
        composition_str = ";".join([f"{el}:{perc}" for el, perc in zip(elements, percentages)])
        spectra_str = ",".join([f"{el}0-2" for el in elements])
        
        self.params = [
            ("composition", composition_str),
            ("spectra", spectra_str),
            ("low_w", str(low_w)),
            ("upp_w", str(upper_w)),
            ("limits_type", "0"),
            ("show_av", "2"),
            ("unit", "1"),
            ("resolution", str(resolution)),
            ("temp", str(Te)),
            ("eden", str(Ne)),
            ("maxcharge", "2"),
            ("min_rel_int", "0.01"),
            ("libs", "1")
        ]
        
        for el, perc in zip(elements, percentages):
            self.params.append(("mytext[]", el))
            self.params.append(("myperc[]", str(perc)))

        self.url = self.base_url + "?" + urllib.parse.urlencode(self.params)
        self.driver = driver

    def get_raw_spectrum(self):
        self.driver.get(self.url)
        
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "chart_div"))
            )
            time.sleep(1) # Extra buffor for memory efficiency
        except Exception:
            page_source = self.driver.page_source
            with open("nist_timeout_error.html", "w", encoding="utf-8") as f:
                f.write(page_source)
            if "No lines found" in page_source:
                raise ValueError("NIST did not found emission lines for this system (try changing the parameters)")
            raise ValueError("Page did not load, raised value error")

        page_source = self.driver.page_source

        block_match = re.search(r'var\s+dataDopplerArray\s*=\s*\[(.*?)\]\s*;\s*var', page_source, re.DOTALL)
        if not block_match:
            block_match = re.search(r'var\s+dataDopplerArray\s*=\s*\[(.*?)\]\s*;', page_source, re.DOTALL)

        if block_match:
            array_content = block_match.group(1)
            
            points = re.findall(r'\[\s*([+-]?[0-9.]+)\s*,\s*([+-]?[0-9.eE+-]+)\s*,', array_content)

            if points:
                wavelengths = [float(p[0]) for p in points]
                intensities = [float(p[1]) for p in points]

                df_final = pd.DataFrame({
                    'wavelength': wavelengths,
                    'intensity': intensities
                })

                if not df_final.empty:
                    return df_final

        with open("nist_parsing_error.html", "w", encoding="utf-8") as f:
            f.write(page_source)
            
        raise ValueError("Could not excise dataDopplerArray data from HTML.")

# =====================================================================
# === Application Logic ======
# =====================================================================

if not os.path.exists(DATASET_DIR):
    os.makedirs(DATASET_DIR)

def generate_random_composition():
    num_elements = random.randint(2, 5)
    chosen_elements = random.sample(TYPICAL_ELEMENTS, num_elements)
    proportions = np.random.dirichlet(np.ones(num_elements), size=1)[0]
    percentages = [float(round(p * 100, 2)) for p in proportions]
    percentages[-1] = float(round(100.0 - sum(percentages[:-1]), 2))
    return dict(zip(chosen_elements, percentages))

def build_filename(composition):
    comp_strings = [f"{el}{perc}" for el, perc in composition.items()]
    return "_".join(comp_strings) + ".csv"

def custom_interpolate(df_raw, min_w, max_w, step):
    df_raw['wavelength'] = pd.to_numeric(df_raw['wavelength'], errors='coerce')
    df_raw['intensity'] = pd.to_numeric(df_raw['intensity'], errors='coerce')
    df_raw = df_raw.dropna().sort_values('wavelength')
    
    custom_grid = np.round(np.arange(min_w, max_w + (step/2), step), decimals=2)
    
    interpolated_intensities = np.interp(
        custom_grid, 
        df_raw['wavelength'], 
        df_raw['intensity'],
        left=0, 
        right=0
    )
    
    interpolated_intensities = np.round(interpolated_intensities, 4)
    
    return pd.DataFrame({
        'wavelength': custom_grid,
        'intensity': interpolated_intensities
    })

def main():
    print(f"Configuring chrome browser in the background...")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("window-size=1920,1080")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        print("Error when launching chrome, make sure the browser is installed")
        print(e)
        return

    print(f"Generating {NUM_SAMPLES} spectra...\n")
    metadata = []
    
    for i in range(1, NUM_SAMPLES + 1):
        comp = generate_random_composition()
        filename = build_filename(comp)
        
        print(f"[{i}/{NUM_SAMPLES}] Generating: {filename}")
        
        try:
            libs = SeleniumNISTScraper(
                elements=list(comp.keys()), 
                percentages=list(comp.values()), 
                resolution=RESOLUTION, 
                low_w=WAVELENGTH_MIN, 
                upper_w=WAVELENGTH_MAX,
                Te=PLASMA_TEMP,
                Ne=ELECTRON_DENSITY,
                driver=driver
            )
            
            df_raw = libs.get_raw_spectrum()
            df_final = custom_interpolate(df_raw, WAVELENGTH_MIN, WAVELENGTH_MAX, GRID_STEP)
            
            filepath = os.path.join(DATASET_DIR, filename)
            df_final.to_csv(filepath, index=False)
            
            # Zapisanie DOKŁADNYCH PROCENTÓW do treningu regresji
            row = {'sample_id': filename}
            for el in TYPICAL_ELEMENTS:
                # Jeśli wylosowaliśmy pierwiastek, zapisz jego %, w przeciwnym razie 0.0
                row[el] = comp.get(el, 0.0) 
            metadata.append(row)
            
        except Exception as e:
            print(f"--> Error with sample {i}: {e}")
            
    if metadata:
        df_labels = pd.DataFrame(metadata)
        labels_file = os.path.join(DATASET_DIR, "Elements_labels.csv")
        df_labels.to_csv(labels_file, index=False)
        print(f"\nFinished succesfuly, data is in folder: '{DATASET_DIR}'")
        
    driver.quit()

if __name__ == "__main__":
    main()