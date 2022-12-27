from .db import get_db
from dataclasses import dataclass
import numpy as np
import requests as req
import lxml.html as xhtml

@dataclass
class NucleusData:
    mass: float = 0.0
    elementSymbol: str = ""
    isotopicSymbol: str = ""
    Z: int = 0
    A: int = 0

def get_nuclear_data(id: np.uint32) -> NucleusData:
    db = get_db()
    data = db.execute("SELECT * FROM nucleus n WHERE n.id = ?", (id,)).fetchone()
    return NucleusData(data["mass"], data["element"], data["isotope"], data["z"], data["a"])

def construct_catima_layer_element(id: np.uint32, s: int) -> tuple[float, int, float]:
    db = get_db()
    data = db.execute("SELECT * FROM nucleus n WHERE n.id = ?", (id,)).fetchone()
    return (data["mass"], data["Z"], float(s))

def get_excitations(id: np.uint32) -> list[float]:
    levels = []
    text = ''
    symbol = get_nuclear_data(id).isotopicSymbol.replace("<sup>", '').replace("</sup>", '')
    print(symbol)
    site = req.get(f"https://www.nndc.bnl.gov/nudat2/getdatasetClassic.jsp?nucleus={symbol}&unc=nds")
    contents = xhtml.fromstring(site.content)
    tables = contents.xpath("//table")
    rows = tables[2].xpath("./tr")
    for row in rows[1:-2]:
        entries = row.xpath("./td")
        if len(entries) != 0:
            entry = entries[0]
            data = entry.xpath("./a")
            if len(data) == 0:
                text = entry.text
            else:
                text = data[0].text
            text = text.replace('?', '').replace('\xa0\xa0≈','')
            levels.append(float(text)/1000.0) #convert to MeV
    return levels