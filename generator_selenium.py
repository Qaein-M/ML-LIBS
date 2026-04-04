import io
import os
import random
import re
import time
import urllib.parse

import numpy as np
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# ===========================================================
# =================== Parameters for data fetching ==========
# ===========================================================

TYPICAL_ELEMENTS = ["Mg", "Fe", "Mn", "Al", "Zn", "C", "N", "Si", "Ni", "Cu"]
WAVELENGTH_MIN = 200.0
WAVELENGTH_MAX = 1000.0
RESOLUTION = 1000
GRID_STEP = 0.05
PLASMA_TEMP = 1
ELECTRON_DENSITY = 1e17
DATASET_DIR = "para1"
NUM_SAMPLES = 10

# ===============================================
# ============ Selenium Scraper =================
# ===============================================


class SeleniumNISTScraper:
    def __init__(
        self, elements, percentages, resolution, low_w, upper_w, Te, Ne, driver
    ):
        self.base_url = "https://physics.nist.gov/cgi-bin/ASD/lines1.pl"

        composition_str = ";".join(
            [f"{el}:{perc}" for el, perc in zip(elements, percentages)]
        )
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
            ("int_scale", 2),  # photon flux
            ("libs", "1"),
        ]

        for el, perc in zip(elements, percentages):
            self.params.append(("mytext[]", el))
            self.params.append(("myperc[]", str(perc)))

        self.url = self.base_url + "?" + urllib.parse.urlencode(self.params)
        self.driver = driver

    def get_raw_spectrum(self):
        self.driver.get(self.url)

        # wydaje mi sie ze to jest i szybsze i mniej podatne na bledy (regexy fuj)
        csv_data = self.driver.execute_script(f"return arrToRealCSV(dataDopplerArray)")

        df = pd.read_csv(io.StringIO(csv_data), sep=",")
        df = df.fillna(0.0)
        df_final = pd.DataFrame(
            {"wavelength": df.iloc[:, 0], "intensity": df.iloc[:, 1]}
        )
        return df_final

        # try:
        #     WebDriverWait(self.driver, 15).until(
        #         EC.presence_of_element_located((By.ID, "chart_div"))
        #     )
        #     time.sleep(1)  # Extra buffor for memory efficiency
        # except Exception:
        #     page_source = self.driver.page_source
        #     with open("nist_timeout_error.html", "w", encoding="utf-8") as f:
        #         f.write(page_source)
        #     if "No lines found" in page_source:
        #         raise ValueError(
        #             "NIST did not found emission lines for this system (try changing the parameters)"
        #         )
        #     raise ValueError("Page did not load, raised value error")

        # page_source = self.driver.page_source

        # block_match = re.search(
        #     r"var\s+dataDopplerArray\s*=\s*\[(.*?)\]\s*;\s*var", page_source, re.DOTALL
        # )
        # if not block_match:
        #     block_match = re.search(
        #         r"var\s+dataDopplerArray\s*=\s*\[(.*?)\]\s*;", page_source, re.DOTALL
        #     )

        # if block_match:
        #     array_content = block_match.group(1)

        #     points = re.findall(
        #         r"\[\s*([+-]?[0-9.]+)\s*,\s*([+-]?[0-9.eE+-]+)\s*,", array_content
        #     )

        #     if points:
        #         wavelengths = [float(p[0]) for p in points]
        #         intensities = [float(p[1]) for p in points]

        #         df_final = pd.DataFrame(
        #             {"wavelength": wavelengths, "intensity": intensities}
        #         )

        #         if not df_final.empty:
        #             return df_final

        # with open("nist_parsing_error.html", "w", encoding="utf-8") as f:
        #     f.write(page_source)

        # raise ValueError("Could not excise dataDopplerArray data from HTML.")


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
    df_raw["wavelength"] = pd.to_numeric(df_raw["wavelength"], errors="coerce")
    df_raw["intensity"] = pd.to_numeric(df_raw["intensity"], errors="coerce")
    df_raw = df_raw.dropna().sort_values("wavelength")

    custom_grid = np.round(np.arange(min_w, max_w + (step / 2), step), decimals=2)

    interpolated_intensities = np.interp(
        custom_grid, df_raw["wavelength"], df_raw["intensity"], left=0, right=0
    )

    interpolated_intensities = np.round(interpolated_intensities, 4)

    return pd.DataFrame(
        {"wavelength": custom_grid, "intensity": interpolated_intensities}
    )


def main():
    print(f"Configuring chrome browser in the background...")
    driver = configure_driver()

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
                driver=driver,
            )

            df_final = libs.get_raw_spectrum()

            # interpolacje zawsze mozna zrobic pozniej, narazie wykomentowalem
            # df_final = custom_interpolate(
            #     df_raw, WAVELENGTH_MIN, WAVELENGTH_MAX, GRID_STEP
            # )

            filepath = os.path.join(DATASET_DIR, filename)
            df_final.to_csv(filepath, index=False)

            # Zapisanie DOKŁADNYCH PROCENTÓW do treningu regresji
            row = {"sample_id": filename}
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


def configure_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.page_load_strategy = "eager"
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2,
        "profile.managed_default_content_settings.stylesheets": 2,
    }
    chrome_options.add_experimental_option("prefs", prefs)
    # chrome_options.add_argument("window-size=1920,1080")

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        print("Error when launching chrome, make sure the browser is installed")
        print(e)
        return


if __name__ == "__main__":
    # https://gist.github.com/wooddar/df4c89f381fa20ce819e94782dc5bc04
    from multiprocessing import Queue, cpu_count
    from threading import Thread

    from selenium import webdriver

    print(f"Generating {NUM_SAMPLES} compositions")
    composition_data = [generate_random_composition() for _ in range(0, NUM_SAMPLES)]

    print(f"Saving metadata")
    metadata = []
    for comp in composition_data:
        filename = build_filename(comp)
        row = {"sample_id": filename}
        for el in TYPICAL_ELEMENTS:
            # Jeśli wylosowaliśmy pierwiastek, zapisz jego %, w przeciwnym razie 0.0
            row[el] = comp.get(el, 0.0)

        metadata.append(row)

    df_labels = pd.DataFrame(metadata)
    labels_file = os.path.join(DATASET_DIR, "Elements_labels.csv")
    df_labels.to_csv(labels_file, index=False)

    composition_data.append("STOP")

    selenium_data_queue = Queue()
    worker_queue = Queue()

    worker_ids = list(range(cpu_count()))

    print("Spawning webdrivers")
    selenium_workers = {}
    for i in worker_ids:
        selenium_workers[i] = configure_driver()
        print(f"{i + 1}/{cpu_count()} done")

    for worker_id in worker_ids:
        worker_queue.put(worker_id)

    def selenium_task(worker, comp):
        """
        :param worker: A selenium web worker NOT a worker ID
        :type worker: webdriver.XXX
        :param data: Any data for your selenium function (must be pickleable)
        :rtype: None
        """

        libs = SeleniumNISTScraper(
            elements=list(comp.keys()),
            percentages=list(comp.values()),
            resolution=RESOLUTION,
            low_w=WAVELENGTH_MIN,
            upper_w=WAVELENGTH_MAX,
            Te=PLASMA_TEMP,
            Ne=ELECTRON_DENSITY,
            driver=worker,
        )

        df_final = libs.get_raw_spectrum()

        filename = build_filename(comp)
        print(f"Scraped {filename}")
        filepath = os.path.join(DATASET_DIR, filename)
        df_final.to_csv(filepath, index=False)

    def selenium_queue_listener(data_queue, worker_queue):
        """
        Monitor a data queue and assign new pieces of data to any available web workers to action
        :param data_queue: The python FIFO queue containing the data to run on the web worker
        :type data_queue: Queue
        :param worker_queue: The queue that holds the IDs of any idle workers
        :type worker_queue: Queue
        :rtype: None
        """
        while True:
            current_data = data_queue.get()
            if current_data == "STOP":
                # If a stop is encountered then kill the current worker and put the stop back onto the queue
                # to poison other workers listening on the queue
                data_queue.put(current_data)
                break
            else:
                # Get the ID of any currently free workers from the worker queue
                worker_id = worker_queue.get()
                worker = selenium_workers[worker_id]
                # Assign current worker and current data to your selenium function
                selenium_task(worker, current_data)
                # Put the worker back into the worker queue as  it has completed it's task
                worker_queue.put(worker_id)
        return

    selenium_processes = [
        Thread(target=selenium_queue_listener, args=(selenium_data_queue, worker_queue))
        for _ in worker_ids
    ]

    for p in selenium_processes:
        p.daemon = True
        p.start()

    for d in composition_data:
        selenium_data_queue.put(d)

    for p in selenium_processes:
        p.join()

    for b in selenium_workers.values():
        b.quit()

        # main()
