"""Build backend/data/sites.csv (the monitored job sites) from an EIA-860M workbook.

EIA-860M is the U.S. Energy Information Administration's monthly inventory of
every operating power plant generator, with official plant IDs, operators and
coordinates. Download the latest "generator" workbook from
https://www.eia.gov/electricity/data/eia860m/ and run:

    python -I scripts/build_sites.py ml/data/raw/eia860m.xlsx

Each curated site below is matched to an EIA plant by name within its state
(the largest plant wins if several match). Time zones drive the 6 PM local
briefing; waterways mark sites that get river flood warnings.
"""
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import openpyxl

OUTPUT = Path(__file__).resolve().parent.parent / "data" / "sites.csv"

ET, CT, MT, AZ, PT = "America/New_York", "America/Chicago", "America/Denver", "America/Phoenix", "America/Los_Angeles"

# (display name, EIA name to match, state, time zone, waterway or None)
CURATED = [
    # Florida
    ("Turkey Point", "turkey point", "FL", ET, "Biscayne Bay"),
    ("St. Lucie", "st lucie", "FL", ET, "Atlantic Ocean"),
    ("Martin", "martin", "FL", ET, None),
    ("Manatee", "manatee", "FL", ET, None),
    ("West County Energy Center", "west county", "FL", ET, None),
    ("Fort Myers", "fort myers", "FL", ET, "Caloosahatchee River"),
    ("Riviera Beach", "riviera", "FL", ET, "Lake Worth Lagoon"),
    ("Port Everglades", "port everglades", "FL", ET, "Port Everglades"),
    ("Lauderdale", "lauderdale", "FL", ET, None),
    ("Cape Canaveral Energy Center", "cape canaveral", "FL", ET, "Indian River"),
    ("Sanford", "sanford", "FL", ET, "St. Johns River"),
    ("Crystal River", "crystal river", "FL", ET, "Gulf of Mexico"),
    ("Big Bend", "big bend", "FL", ET, "Tampa Bay"),
    ("Deerhaven", "deerhaven", "FL", ET, None),
    # Lower Mississippi / Gulf Coast
    ("Grand Gulf", "grand gulf", "MS", CT, "Mississippi River"),
    ("Waterford 3", "waterford 3", "LA", CT, "Mississippi River"),
    ("River Bend", "river bend", "LA", CT, "Mississippi River"),
    ("Big Cajun II", "big cajun 2", "LA", CT, "Mississippi River"),
    ("W.A. Parish", "w a parish", "TX", CT, "Brazos River"),
    ("South Texas Project", "south texas", "TX", CT, "Colorado River (TX)"),
    # Upper Mississippi / Ohio / Missouri / Tennessee rivers
    ("Labadie", "labadie", "MO", CT, "Missouri River"),
    ("Sioux", "sioux", "MO", CT, "Mississippi River"),
    ("Baldwin", "baldwin", "IL", CT, "Kaskaskia River"),
    ("Quad Cities", "quad cities", "IL", CT, "Mississippi River"),
    ("Prairie Island", "prairie island", "MN", CT, "Mississippi River"),
    ("Louisa", "louisa", "IA", CT, "Mississippi River"),
    ("Gibson", "gibson", "IN", CT, "Wabash River"),
    ("Browns Ferry", "browns ferry", "AL", CT, "Tennessee River"),
    ("Cumberland", "cumberland", "TN", CT, "Cumberland River"),
    ("Watts Bar", "watts bar", "TN", ET, "Tennessee River"),
    # Southeast
    ("Vogtle", "vogtle", "GA", ET, "Savannah River"),
    ("Scherer", "scherer", "GA", ET, None),
    ("Bowen", "bowen", "GA", ET, "Etowah River"),
    ("Oconee", "oconee", "SC", ET, "Lake Keowee"),
    ("Catawba", "catawba", "SC", ET, "Lake Wylie"),
    ("McGuire", "mcguire", "NC", ET, "Lake Norman"),
    ("North Anna", "north anna", "VA", ET, "Lake Anna"),
    # Mid-Atlantic / Northeast / Great Lakes
    ("Calvert Cliffs", "calvert cliffs", "MD", ET, "Chesapeake Bay"),
    ("Peach Bottom", "peach bottom", "PA", ET, "Susquehanna River"),
    ("Limerick", "limerick", "PA", ET, "Schuylkill River"),
    ("Susquehanna", "talenenergy susquehanna", "PA", ET, "Susquehanna River"),
    ("Millstone", "millstone", "CT", ET, "Long Island Sound"),
    ("Seabrook", "seabrook", "NH", ET, "Atlantic Ocean"),
    ("Nine Mile Point", "nine mile point", "NY", ET, "Lake Ontario"),
    ("Robert Moses Niagara", "robert moses niagara", "NY", ET, "Niagara River"),
    ("Fermi 2", "fermi", "MI", ET, "Lake Erie"),
    # Midwest / Plains
    ("Byron", "byron", "IL", CT, "Rock River"),
    ("Braidwood", "braidwood", "IL", CT, "Kankakee River"),
    ("Wolf Creek", "wolf creek", "KS", CT, None),
    ("Comanche Peak", "comanche peak", "TX", CT, "Squaw Creek Reservoir"),
    # Mountain West / Southwest / Pacific
    ("Palo Verde", "palo verde", "AZ", AZ, None),
    ("Four Corners", "four corners", "NM", MT, "Morgan Lake"),
    ("Hoover Dam", "hoover dam", "NV", PT, "Colorado River"),
    ("Intermountain", "intermountain", "UT", MT, None),
    ("Colstrip", "colstrip", "MT", MT, None),
    ("Diablo Canyon", "diablo canyon", "CA", PT, "Pacific Ocean"),
    ("Grand Coulee", "grand coulee", "WA", PT, "Columbia River"),
    ("Columbia Generating Station", "columbia generating", "WA", PT, "Columbia River"),
]

# EIA technology names -> short labels for the UI.
TECH_LABELS = {
    "Nuclear": "Nuclear",
    "Conventional Steam Coal": "Coal",
    "Natural Gas Fired Combined Cycle": "Natural Gas",
    "Natural Gas Fired Combustion Turbine": "Natural Gas",
    "Natural Gas Steam Turbine": "Natural Gas",
    "Natural Gas Internal Combustion Engine": "Natural Gas",
    "Conventional Hydroelectric": "Hydro",
    "Hydroelectric Pumped Storage": "Pumped Hydro",
    "Solar Photovoltaic": "Solar",
    "Batteries": "Battery",
    "Onshore Wind Turbine": "Wind",
    "Petroleum Liquids": "Oil",
}


def normalize(text):
    """Lowercase, letters/digits only, roman numerals II/III -> 2/3."""
    text = str(text).lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return re.sub(r"\b(iii|ii)\b", lambda m: {"ii": "2", "iii": "3"}[m.group(1)], text)


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")


def load_plants(workbook_path):
    """Aggregate EIA generator rows into one record per plant."""
    sheet = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)["Operating"]
    rows = sheet.iter_rows(values_only=True)
    header = None
    for row in rows:  # the header row is the one that starts with "Entity ID"
        if row and row[0] == "Entity ID":
            header = [str(c).strip() if c is not None else "" for c in row]
            break
    col = {name: header.index(name) for name in header if name}

    plants = {}
    for row in rows:
        if not row or row[col["Plant ID"]] in (None, ""):
            continue
        plant_id = int(row[col["Plant ID"]])
        capacity = float(row[col["Nameplate Capacity (MW)"]] or 0)
        plant = plants.setdefault(plant_id, {
            "eia_plant_id": plant_id,
            "eia_name": str(row[col["Plant Name"]]).strip(),
            "state": row[col["Plant State"]],
            "county": row[col["County"]],
            "lat": row[col["Latitude"]],
            "lng": row[col["Longitude"]],
            "capacity_mw": 0.0,
            "by_tech": defaultdict(float),
            "by_entity": defaultdict(float),
        })
        plant["capacity_mw"] += capacity
        plant["by_tech"][row[col["Technology"]]] += capacity
        plant["by_entity"][row[col["Entity Name"]]] += capacity
    return plants


def plant_type(by_tech):
    """Primary technology, plus a second one if it is at least 20% of capacity."""
    total = sum(by_tech.values()) or 1
    labels = defaultdict(float)
    for tech, mw in by_tech.items():
        labels[TECH_LABELS.get(tech, tech)] += mw
    ranked = sorted(labels.items(), key=lambda kv: kv[1], reverse=True)
    names = [ranked[0][0]] + [name for name, mw in ranked[1:2] if mw / total >= 0.2]
    return " / ".join(names)


def match(plants, term, state):
    """Best EIA plant for a curated name: exact > prefix > contains, then largest."""
    wanted = normalize(term)
    in_state = [p for p in plants.values() if p["state"] == state]
    for rule in (lambda n: n == wanted, lambda n: n.startswith(wanted), lambda n: wanted in n):
        found = [p for p in in_state if rule(normalize(p["eia_name"]))]
        if found:
            return max(found, key=lambda p: p["capacity_mw"])
    return None


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python -I scripts/build_sites.py <eia860m.xlsx>")
    plants = load_plants(sys.argv[1])
    print(f"Loaded {len(plants)} operating plants from EIA-860M")

    rows, missing = [], []
    for display, term, state, tz, waterway in CURATED:
        plant = match(plants, term, state)
        if not plant:
            missing.append(f"{display} ({state})")
            continue
        operator = max(plant["by_entity"].items(), key=lambda kv: kv[1])[0]
        rows.append({
            "id": slugify(display),
            "eia_plant_id": plant["eia_plant_id"],
            "name": display,
            "eia_name": plant["eia_name"],
            "state": state,
            "county": plant["county"],
            "lat": round(float(plant["lat"]), 5),
            "lng": round(float(plant["lng"]), 5),
            "utility": operator,
            "plant_type": plant_type(plant["by_tech"]),
            "capacity_mw": round(plant["capacity_mw"], 1),
            "timezone": tz,
            "waterway": waterway or "",
        })
        print(f"  {display:30} -> EIA {plant['eia_plant_id']:>6} {plant['eia_name']:35} {plant['capacity_mw']:8.0f} MW  {operator}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {len(rows)} sites to {OUTPUT}")
    if missing:
        print("Not found (retired or renamed):", ", ".join(missing))


if __name__ == "__main__":
    main()
