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

TYPICAL_ELEMENTS = ['Fe', 'Cu', 'Si', 'Ni', 'Mn', 'Cr', 'Al', 'Zn', 'Mg', 'C', 'Pb', 'Co', 'Ti', 'As', 'Sn', 'O']
WAVELENGTH_MIN = 200.0
WAVELENGTH_MAX = 1000.0
RESOLUTION = 1000
PLASMA_TEMP = 1
ELECTRON_DENSITY = 1e17
DATASET_DIR = "para2"
NUM_SAMPLES = 10000
PACK_SIZE = 100.0 

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
            time.sleep(1) # Extra buffer for memory efficiency
        except Exception:
            page_source = self.driver.page_source
            if "No lines found" in page_source:
                raise ValueError("No lines found")
            
            with open("nist_timeout_error.html", "w", encoding="utf-8") as f:
                f.write(page_source)
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

        return pd.DataFrame(columns=['wavelength', 'intensity'])

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

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage") 
    chrome_options.add_argument("window-size=1920,1080")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)


def main():
    print(f"Generating {NUM_SAMPLES} spectra...\n")
    metadata = []
    
    wavelength_packs = np.arange(WAVELENGTH_MIN, WAVELENGTH_MAX, PACK_SIZE)
    
    for i in range(1, NUM_SAMPLES + 1):
        comp = generate_random_composition()
        filename = build_filename(comp)
        
        print(f"\n[{i}/{NUM_SAMPLES}] Generating: {filename}")
        
        try:
            driver = setup_driver()
        except Exception as e:
            print("Error launching Chrome:", e)
            continue
            
        all_packs = []
        
        try: 
            for low_w in wavelength_packs:
                upp_w = min(low_w + PACK_SIZE, WAVELENGTH_MAX)
                print(f"    -> Fetching pack: {low_w} nm to {upp_w} nm")
                
                try:
                    libs = SeleniumNISTScraper(
                        elements=list(comp.keys()), 
                        percentages=list(comp.values()), 
                        resolution=RESOLUTION, 
                        low_w=low_w, 
                        upper_w=upp_w,
                        Te=PLASMA_TEMP,
                        Ne=ELECTRON_DENSITY,
                        driver=driver
                    )
                    
                    df_pack = libs.get_raw_spectrum()
                    if not df_pack.empty:
                        all_packs.append(df_pack)
                    else:
                        print(f"       No visible plot generated in this range. Skipping.")
                    
                except ValueError as e:
                    if str(e) == "No lines found":
                        print(f"    No lines found in this range. Skipping.")
                    else:
                        print(f"    (Error fetching pack: {e})")
                except Exception as e:
                    print(f"    Unexpected error fetching pack: {e}")
                    
        finally:
            driver.quit()
                
        if not all_packs:
            print(f"    Error: No data collected across any pack for sample {i}.")
            continue
            
        try:
            df_final = pd.concat(all_packs, ignore_index=True)
            df_final = df_final.drop_duplicates(subset=['wavelength'], keep='first').sort_values('wavelength')
            
            filepath = os.path.join(DATASET_DIR, filename)
            df_final.to_csv(filepath, index=False)
            
            row = {'sample_id': filename}
            for el in TYPICAL_ELEMENTS:
                row[el] = comp.get(el, 0.0) 
            metadata.append(row)
            
        except Exception as e:
            print(f"Error processing data for sample {i}: {e}")
            
    if metadata:
        pd.DataFrame(metadata).to_csv(os.path.join(DATASET_DIR, "Elements_labels.csv"), index=False)
        print(f"\nFinished successfully. Data is in folder: '{DATASET_DIR}'")

if __name__ == "__main__":
    main()
