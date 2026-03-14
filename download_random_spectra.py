import os
import urllib.parse
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import numpy as np

DOWNLOAD_DIR = os.getcwd()
BASE_URL = "https://physics.nist.gov/cgi-bin/ASD/lines1.pl"

elements = ['Mn', 'C', 'N', 'O', 'Be']
num_spectra = 3

def generate_random_spectra():

    try:
        for i in range(num_spectra):
            print(f"Downloading {i+1}/{num_spectra}")
        
            random_weights = np.random.rand(len(elements))
            percentages = (random_weights / np.sum(random_weights) * 100).tolist()
            
            composition_dict = {el: round(p, 1) for el, p in zip(elements, percentages)}
            print(f"Composition: {composition_dict}")
            
            comp_str = ";".join([f"{el}:{p:.1f}" for el, p in zip(elements, percentages)])
            spectra_str = ",".join([f"{el}0-2" for el in elements])
            
            """parameters:
                composition: string in the format "Element1:Percentage1;Element2:Percentage2 (sum up to 100)
                spectra: min_charge to max_charge 
                low_w: lower wavelength limit
                upp_w: upper wavelength limit
                show_av: 2 for "Vacuum (< 200nm) Air (200-20000 nm) Vacuum (> 2000 nm)", 3 for "Vacuum (all wavelengths)"
                unit: 0 for angstroms, 1 for nanometers, 2 for micrometers
                temp: plasma electron temperature
                eden: plasma electron density 
                maxcharge: maximum ion charge
                min_rel_int: minimum relative intensity, filters out spectral lines below this threshold
                int_scale: 1 for "Energy flux", 2 for "Photon flux"
                libs: 1 to use LIBS data
                """
            
            params = [
                ("composition", comp_str),
                ("spectra", spectra_str),
                ("low_w", "200"),
                ("upp_w", "600"),
                ("show_av", "2"),
                ("unit", "1"),
                ("resolution", "1000"),
                ("temp", "1"),
                ("eden", "1e17"),
                ("maxcharge", "2"),
                ("min_rel_int", "0.01"),
                ("int_scale", "1"),
                ("libs", "1")
            ]
            
            for el, p in zip(elements, percentages):
                params.append(("mytext[]", el))
                params.append(("myperc[]", f"{p:.1f}"))
                
            full_url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
            
            driver.get(full_url)
            original_window = driver.current_window_handle

            button = wait.until(EC.element_to_be_clickable((By.NAME, "ViewDataCSV")))
            button.click()

            wait.until(EC.number_of_windows_to_be(2))

            for window_handle in driver.window_handles:
                if window_handle != original_window:
                    driver.switch_to.window(window_handle)
                    break

            body_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        
            csv_data = body_element.text
            
            filename = os.path.join(DOWNLOAD_DIR, f"spectra_{'_'.join([f'{k}_{v}' for k, v in composition_dict.items()])}.csv")
            with open(filename, 'w') as f:
                f.write(csv_data)
            print(f"Saved to: {filename}")

            driver.close()
            driver.switch_to.window(original_window)

    except Exception as e:
        print(f"Error: {e}")

    finally:
        driver.quit()

if __name__ == "__main__":
    options = Options()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

    generate_random_spectra()