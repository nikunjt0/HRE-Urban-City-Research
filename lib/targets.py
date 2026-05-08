"""Priority case-study cities + manual nodesid↔city_id overrides + composite weights.

The 13 priority cities for the case study. `bairoch_id` is the canonical
city_id from city_locations.csv. `nodesid` is the Viabundus node id (None when
Viabundus does not cover that city — south-German cities like Augsburg,
Würzburg, Regensburg, Ulm, Bamberg, Speyer, Rothenburg are NOT in Viabundus).
"""

PRIORITY_CITIES = [
    # name (display)         bairoch_id   nodesid   notes
    ("Leipzig",                  9070,    4337),
    ("Cologne (Köln)",          14060,    3888),
    ("Nuremberg (Nürnberg)",    22094,    5492),
    ("Frankfurt am Main",       15027,    1987),
    ("Augsburg",                23006,    None),     # not in Viabundus
    ("Bamberg",                 22016,    None),
    ("Würzburg",                22145,    None),
    ("Regensburg",              23123,    None),
    ("Erfurt",                  11039,    1826),
    ("Ulm",                     16085,    None),
    ("Magdeburg",               11094,    4705),
    ("Rothenburg ob der Tauber", 22109,   None),
    ("Speyer",                  18087,    None),
]

# Tunable weights for the composite "launch potential" score.
DEFAULT_WEIGHTS = {
    "legal_capacity":       +1.0,
    "merchant_capital":     +1.0,
    "trade_access":         +1.0,
    "agricultural_surplus": +0.7,
    "peasant_mobility":     +0.6,
    "noble_extraction":     -0.8,
    "conflict_risk":        -0.5,
}
