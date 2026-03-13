import io

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

CHARGE_NO_LIMIT = 109


def downloadLIBS(
    driver: WebDriver,
    elements,
    *,
    lower_wavelength=200,
    upper_wavelength=600,
    av=2,
    unit=1,
    resolution=1000,
    T_e=1,
    N_e="1e17",
    min_charge=0,
    max_charge=2,
    min_rel_intensity=0.01,
    intensity_scale=1,
    useSticksData=False,
) -> pd.DataFrame | None:
    """
    parametry:
        `driver`: WebDriver z selenium
        `elements`: skrot pierwiastka (np. `"Mg"`) albo lista pierwiastków razem z ich wkładem procentowym (procenty powinny sie sumowac do 100, np. `[("Mg", 40), ("Cu", 60)]` )

    opcjonalne parametry (domyślne jak na stronie):
        `lower_wavelength`: dolny limit długości fali
        `upper_wavelength`: górny limit długości fali
        `av`: wyjaśnienie tutaj -> https://physics.nist.gov/PhysRefData/ASD/Html/libshelp.html#LIBS_WAVIN
            `2` dla "Vacuum (< 200nm) Air (200-20000 nm) Vacuum (> 2000 nm)" \n
            `3` dla "Vacuum (all wavelengths)"
        `unit`: jednostka długości fali.
            `0` dla angstremów \n
            `1` dla nanometrów \n
            `2` dla mikrometrów
        `resolution`: rozdzielczość
        `T_e`: temperatura elektronowa plazmy
        `N_e`: gęstość elektronowa plazmy
        `min_charge`: minimalna wartościowość
        `max_charge`: maksymalna wartościowość (`CHARGE_NO_LIMIT` zeby nie bylo górnego ograniczenia)
        `min_rel_intensity`: ? w sumie nie rozumiem co to i na stronie nie ma wyjaśnienia
        `intensity_scale`:
            `1` dla "Energy flux" \n
            `2` dla "Photon flux"
        `useSticksData`: wyjaśnienie tutaj -> https://physics.nist.gov/PhysRefData/ASD/Html/libshelp.html#LIBSOUTSTICK

    Wartości typu `1e17` muszą(!) być podane jako string bo python formatuje takie liczby jako `"1e+17"` i link przestaje działać :)
    (za to `1e-17` już jest ok jako liczba)
    """

    libsURL = ""
    if isinstance(elements, list):
        composition = [f"{el}%3A{p}" for (el, p) in elements]
        composition = "%3B".join(composition)

        myPart = [f"mytext%5B%5D={el}&myperc%5B%5D={p}" for (el, p) in elements]
        myPart = "&".join(myPart)

        # tutaj możnaby było się pobawić i dodać oddzielny zakres wartosciowosci dla kazdego pierwiastka ale chyba tego nie potrzebujemy
        spectra = [f"{el}{min_charge}-{max_charge}" for (el, _) in elements]
        spectra = "%2C".join(spectra)

        libsURL = f"https://physics.nist.gov/cgi-bin/ASD/lines1.pl?composition={composition}&{myPart}&spectra={spectra}&low_w={lower_wavelength}&limits_type=0&upp_w={upper_wavelength}&show_av={av}&unit={unit}&resolution={resolution}&temp={T_e}&eden={N_e}&maxcharge={max_charge}&min_rel_int={min_rel_intensity}&int_scale={intensity_scale}&libs=1"
    else:
        libsURL = f"https://physics.nist.gov/cgi-bin/ASD/lines1.pl?composition={elements}%3A100&mytext%5B%5D={elements}&myperc%5B%5D=100&spectra={elements}{min_charge}-{max_charge}&low_w={lower_wavelength}&limits_type=0&upp_w={upper_wavelength}&show_av={av}&unit={unit}&resolution={resolution}&temp={T_e}&eden={N_e}&maxcharge={max_charge}&min_rel_int={min_rel_intensity}&int_scale={intensity_scale}&libs=1"

    driver.get(libsURL)

    missingData_h2 = driver.find_elements(By.XPATH, "/html/body/h2")
    if missingData_h2:
        if missingData_h2[0].text == "Error Message:":
            return None  # brak spektrum w bazie

    serviceUnavail_h1 = driver.find_elements(By.XPATH, "/html/body/h1")
    if serviceUnavail_h1:
        if serviceUnavail_h1[0].text == "Service Unavailable":
            return None  # stronka ma jakies problemy

    csvSource = "dataSticksArray" if useSticksData else "dataDopplerArray"
    csvData = driver.execute_script(
        f"return arrToRealCSV({csvSource})"
        # kilka razy mi się zdarzyło, że csvSource nie miał wartosci odrazu po zaladowaniu strony, ten js ponizej powinien zawsze dzialac (czeka az csvSource bedzie miało wartość)
        # f"return (function() {{ while ({csvSource} === null) {{}}; return arrToRealCSV({csvSource}) }})()"
    )

    df = pd.read_csv(io.StringIO(csvData), sep=",")
    return df


# przykladowe uzycie
if __name__ == "__main__":
    import matplotlib.pyplot as plt

    options = Options()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)

    df = downloadLIBS(driver, [("Cu", 40), ("Mn", 20), ("Au", 40)])

    if df is None:
        print("Spektrum nie istnieje/blad strony")
    else:
        # wypelnienie pustych komorek zerami, potencjalnie to powinno sie dziac automatycznie w downloadSpectrum(), ale nie wiem czy te miejsca na pewno powinny byc zerami.
        df = df.fillna(0.0)
        print(df)

        df.plot(x=df.columns[0])
        plt.show()
