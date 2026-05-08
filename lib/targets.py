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

# Tunable weights for the heuristic "launch potential" composite (the prior).
# These are theoretical commitments, not estimated coefficients. The fitted
# OLS posterior — with bootstrap 95% CIs and out-of-sample validation against
# Bairoch population — lives in build_predictive_model.py and is reported in
# §5 of the rendered report. The two are intentionally kept separate; this
# composite drives the qualitative tier maps and city profiles, while the
# fitted model drives the quantitative claims.
#
# peasant_mobility is included here for narrative continuity (it appears in
# the prior equation walk-through), but the predictive model excludes it
# because build_peasant_mobility.py:43-53 makes it a deterministic function
# of three other factors — feeding it into a regression yields perfect
# collinearity.
DEFAULT_WEIGHTS = {
    "legal_capacity":       +1.0,
    "merchant_capital":     +1.0,
    "trade_access":         +1.0,
    "agricultural_surplus": +0.7,
    "peasant_mobility":     +0.6,
    "noble_extraction":     -0.8,
    "conflict_risk":        -0.5,
}
