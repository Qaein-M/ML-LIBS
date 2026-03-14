import os
import random
import numpy as np
import pandas as pd
from SimulatedLIBS import simulation

# =====================================================================
# === USTAWIENIA PROJEKTU (TUTAJ WPROWADZAJ EWENTUALNE ZMIANY) ===
# =====================================================================

TYPICAL_ELEMENTS = ['Fe', 'C', 'Si', 'Ni', 'Cr', 'Mn', 'Cu', 'Al', 'Ti', 'Mg', 'V', 'Be']

# 2. Spectra parameters
WAVELENGTH_MIN = 200.0   
WAVELENGTH_MAX = 600.0   
RESOLUTION = 1000        
GRID_STEP = 0.05         

# 3. Plasma parameters
PLASMA_TEMP = 1          # (eV)
ELECTRON_DENSITY = 1e17  

# 4. Konfiguracja zapisu
DATASET_DIR = "param1"  # output folder
NUM_SAMPLES = 1                    

# =====================================================================
# === Program Engine ===
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
    
    interpolated_intensities = np.interp(custom_grid, df_raw['wavelength'], df_raw['intensity'])
    
    interpolated_intensities = np.round(interpolated_intensities, decimals=2)
    
    return pd.DataFrame({
        'wavelength': custom_grid,
        'intensity': interpolated_intensities
    })

def main():
    print(f"Rozpoczynam generowanie {NUM_SAMPLES} widm...")
    print(f"Zakres: {WAVELENGTH_MIN}-{WAVELENGTH_MAX} nm, Krok: {GRID_STEP} nm\n")
    
    metadata = []
    
    for i in range(1, NUM_SAMPLES + 1):
        comp = generate_random_composition()
        filename = build_filename(comp)
        
        print(f"[{i}/{NUM_SAMPLES}] Generowanie: {filename}")
        
        try:
            libs = simulation.SimulatedLIBS(
                elements=list(comp.keys()), 
                percentages=list(comp.values()), 
                resolution=RESOLUTION, 
                low_w=WAVELENGTH_MIN, 
                upper_w=WAVELENGTH_MAX,
                Te=PLASMA_TEMP,
                Ne=ELECTRON_DENSITY
            )
            
            df_raw = libs.get_raw_spectrum()
            df_final = custom_interpolate(df_raw, WAVELENGTH_MIN, WAVELENGTH_MAX, GRID_STEP)
            
            filepath = os.path.join(DATASET_DIR, filename)
            df_final.to_csv(filepath, index=False, float_format='%.2f')
            
            # Zapisanie DOKŁADNYCH PROCENTÓW do treningu regresji
            row = {'sample_id': filename}
            for el in TYPICAL_ELEMENTS:
                # Jeśli wylosowaliśmy pierwiastek, zapisz jego %, w przeciwnym razie 0.0
                row[el] = comp.get(el, 0.0) 
            metadata.append(row)
            
        except Exception as e:
            print(f"--> Błąd przy próbce {i}: {e}")
            
    if metadata:
        df_labels = pd.DataFrame(metadata)
        labels_file = os.path.join(DATASET_DIR, "Element_labels.csv")
        df_labels.to_csv(labels_file, index=False)
        print(f"\nZakończono sukcesem! Dane są w folderze: '{DATASET_DIR}'")

if __name__ == "__main__":
    main()



