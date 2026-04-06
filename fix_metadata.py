import os

import numpy as np
import pandas as pd

directory = os.fsencode("./para1/")

df = pd.DataFrame(
    columns=np.array(
        ["sample_id", "Mg", "Fe", "Mn", "Al", "Zn", "C", "N", "Si", "Ni", "Cu"]
    )
)

for file in os.listdir(directory):
    filename = os.fsdecode(file)
    if filename.endswith(".csv"):
        [name, _ext] = filename.split(".csv")
        els = name.split("_")
        data = {col: "0.0" for col in df.columns}
        data["sample_id"] = filename
        for el in els:
            for i in range(len(el)):
                if el[i].isdigit():
                    break

            data[el[:i]] = el[i:]

        df.loc[len(df)] = data

df.to_csv("metadata.csv", sep=",", index=False)
