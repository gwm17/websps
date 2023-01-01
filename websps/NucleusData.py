from .db import db, Nucleus
from dataclasses import dataclass
import numpy as np
import requests as req
import lxml.html as xhtml
from typing import Optional

@dataclass
class NucleusData:
    mass: float = 0.0
    elementSymbol: str = ""
    isotopicSymbol: str = ""
    Z: int = 0
    A: int = 0

def get_nuclear_data(id: np.uint32) -> Optional[NucleusData]:
    nuc: Optional[Nucleus] = db.session.get(Nucleus, id)
    if nuc is None:
        return None
    return NucleusData(nuc.mass, nuc.element, nuc.isotope, nuc.z, nuc.a)

def construct_catima_layer_element(id: np.uint32, s: int) -> Optional[tuple[float, int, float]]:
    nuc: Optional[Nucleus] = db.session.get(Nucleus, id)
    if nuc is None:
        return None
    return (nuc.mass, nuc.z, float(s))

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