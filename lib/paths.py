"""Shared paths and constants for the HRE city-variable build."""
from pathlib import Path

ROOT = Path("/Users/nikunjtyagi/HistoryResearch")
DOCS = ROOT / "docs"
OUT = ROOT / "output"
OUT.mkdir(parents=True, exist_ok=True)

VIABUNDUS = DOCS / "viabundus" / "Viabundus-2-csv"
TOWNCHARTER = DOCS / "town_charters_and_first_mentions" / "towncharter_data"
CONFLICTS = DOCS / "conflicts_and_war"
CONSTRUCTION = DOCS / "construction_data"
MARKETS = DOCS / "markets" / "markets_data"
TERRITORIAL = DOCS / "territorial_histories" / "territorial_hit"
CITY_LOCATIONS_DIR = DOCS / "city_locations_and_border_maps" / "dataverse_files"
EU_POP = DOCS / "European_Population_data_Buringh"

CITY_LOCATIONS_CSV = CITY_LOCATIONS_DIR / "city_locations.csv"
TOWNCHARTER_CSV = TOWNCHARTER / "towncharter.csv"
LEGAL_FAMILIES_CSV = TOWNCHARTER / "legal_families.csv"
CONFLICT_CSV = CONFLICTS / "conflict_incidents.csv"
CONSTRUCTION_CSV = CONSTRUCTION / "construction.csv"
MARKETS_CSV = MARKETS / "markets.csv"
CITIES_POLITIES_CSV = TERRITORIAL / "cities_polities.csv"
TERRITORIES_ALL_CSV = TERRITORIAL / "territories_all.csv"
EU_POP_XLSX = EU_POP / "European urban population, 700 - 2000.xlsx"
CROSSWALK_CSV = OUT / "crosswalk_nodesid_cityid.csv"

BENCHMARKS = [1250, 1300, 1350, 1400, 1450, 1500]

# Magdeburg / Lübeck / Kulm law family codes (the three big northern-expansion
# legal traditions). Stronger civic autonomy proxy than other codes.
STRONG_LEGAL_FAMILIES = {"M05", "L04", "K03"}

# Pre-1500 universities used for LegalCapacity proxy. Year = founding year.
# Coords from Wikipedia. Used only for nearest-distance computation.
PRE_1500_UNIVERSITIES = [
    ("Bologna",     1088, 44.4949,  11.3426),
    ("Paris",       1150, 48.8489,   2.3437),
    ("Oxford",      1167, 51.7548,  -1.2544),
    ("Cambridge",   1209, 52.2043,   0.1149),
    ("Salamanca",   1218, 40.9619,  -5.6677),
    ("Padua",       1222, 45.4067,  11.8768),
    ("Naples",      1224, 40.8467,  14.2554),
    ("Toulouse",    1229, 43.6047,   1.4442),
    ("Siena",       1240, 43.3188,  11.3308),
    ("Coimbra",     1290, 40.2078,  -8.4252),
    ("Lisbon",      1290, 38.7223,  -9.1393),
    ("Madrid",      1293, 40.4168,  -3.7038),
    ("Rome",        1303, 41.9028,  12.4964),
    ("Avignon",     1303, 43.9493,   4.8055),
    ("Perugia",     1308, 43.1107,  12.3908),
    ("Florence",    1321, 43.7696,  11.2558),
    ("Pisa",        1343, 43.7228,  10.4017),
    ("Prague",      1348, 50.0875,  14.4214),
    ("Krakow",      1364, 50.0614,  19.9372),
    ("Vienna",      1365, 48.2087,  16.3725),
    ("Pecs",        1367, 46.0728,  18.2330),
    ("Heidelberg",  1386, 49.4109,   8.7100),
    ("Cologne",     1388, 50.9375,   6.9603),
    ("Erfurt",      1392, 50.9787,  11.0328),
    ("Buda",        1395, 47.4979,  19.0402),
    ("Wurzburg",    1402, 49.7913,   9.9534),
    ("Leipzig",     1409, 51.3397,  12.3731),
    ("Rostock",     1419, 54.0887,  12.1402),
    ("Greifswald",  1456, 54.0939,  13.3878),
    ("Freiburg",    1457, 47.9990,   7.8421),
    ("Basel",       1460, 47.5596,   7.5886),
    ("Ingolstadt",  1472, 48.7665,  11.4257),
    ("Trier",       1473, 49.7567,   6.6414),
    ("Mainz",       1477, 50.0007,   8.2716),
    ("Tubingen",    1477, 48.5216,   9.0576),
    ("Uppsala",     1477, 59.8586,  17.6389),
    ("Copenhagen",  1479, 55.6761,  12.5683),
]
