### README for: Storm from the Steppes: Warfare and Succession Institutions in Pre-modern Eurasia, 1000-1799 CE ###

Daniel S Smith
July 2025
American Political Science Review

The Dataverse archive contains all data and code needed to replicate results in the manuscript and supplementary materials. Please direct any questions or concerns to Daniel S Smith (smith.13091@osu.edu).

## CONTENTS ##

Storm_from_the_Steppes_Supplementary_Materials.pdf - supplementary materials with additional analyses
Storm_from_the_Steppes_Replication_Code.R - Replication code for R-produced figures and tables (manuscript and supplementary materials)
Storm_from_the_Steppes_Eurasian_Dynasties_1000_1799.csv - dynasty data for dynasty-century analyses
Storm_from_the_Steppes_Eurasian_Polity_Century_1000_1800.csv - polity data for dynasty-century analyses
Storm_from_the_Steppes_Eurasian_Rulers_1000_1799.csv - rulers dataset for survival analyses

## REPLICATION CODE ##

# R version 4.3.2 (2023-10-31 ucrt)
Platform: x86_64-w64-mingw32/x64 (64-bit)
Running under: Windows 11 x64 (build 26100)

# The "Storm_from_the_Steppes_Replication_Code.R" file indicates blocks of code to reproduce each table and figure with the exception of manually-generated ArcGIS maps. 

Load Data (Lines 34-94)
Construct Panel (100-160)
Figure 1. Prevalence of Father-to-son Succession Systems, 1000-1800 CE (Line 167)
Figure 2. Dynastic Average Rule Duration by Border Distance to Inner Asia, 1000-1799 CE (Line 194)
Figure 3. Father-to-son Succession Systems Increase Rule Duration (Line 228)
Figure 4. Eurasian Rulers Practicing FS Succession Enjoyed Longer Reigns (Line 254)
Figure 5. Rule Duration by IACW Score (Line 279)
Table 2. Linear Probability Models: Reliance on Inner Asian Cavalry Warfare Is Negatively Associated with Father-to-son Succession Systems (Line 305)
Table 3. Linear Probability Models: Inner Asian Cavalry Warfare Conditionally Predicts Non-FS Conquests (Line 358)
Figure 7. Inner Asian Conquests and Rule Duration in Northern India, 1000-1499 CE (Line 528)
Figure 8. Inner Asian Conquests and Rule Duration in China Proper, 1000-1368 CE (Line 560)
Table A1. Rulers in States with Father-to-son Succession Systems Rule Longer (Line 598)
Table A2. Rulers in States with Father-to-son Succession Systems are Less Likely to be Deposed by Domestic Actors (Line 655)
Table A3. Fixed Effects Models: Reliance on Inner Asian Cavalry Warfare Is Negatively Associated with Father-to-son Succession Systems (Line 712)
Table A4. 2SLS Instrumental Variable Models: Reliance on Inner Asian Cavalry Warfare Predicts Lower Likelihood of Father-to-son Succession Systems (Line 749)
Table A5. Polity Fixed Effects Models: Inner Asian Cavalry Warfare Conditionally Predicts Non-FS Conquests (Line 821)
Table A6. FE Models: Reliance on Inner Asian Cavalry Warfare Is Negatively Associated with Rule Duration (Line 876)
Table B1. Dynasty-Century Data Descriptive Statistics (Line 956)
Table B2. IACW Score Predicts Father-to-son Succession Systems (Logistic Regression) (Line 968)
Table B3. IACW Conflict Conditionally Predict Non-FS Conquest (Logistic Regression) (Line 1018)
Table B4. IACW Score Predicts FS Succession (Eurasian pseudo-regions) (Line 1101)
Table B5. IACW Conflict Conditionally Predicts Non-FS Conquests (Eurasian pseudo-regions) (Line 1169)
Table B6. IACW Score Predicts FS Succession (Fixest Conley SEs) (Line 1238)
Table B7. IACW Conflict Conditionally Predicts Non-FS Conquests (Fixest Conley SEs) (Line 1305)

## CODEBOOK ##

# Dynasties Data:

polity_name - designation for a dynasty's associated polity
truhart_id - ID assigned to polity in Truhart's (1996) Historical Dictionary of States
dynasty_name - designation for dynasty
dynasty_id - unique ID for dynasties
dyn_start - start year according to Truhart (1996) or, in some cases, Tapsell (1983)
dyn_end - end year according to Truhart (1996) or, in some cases, Tapsell (1983)
dynasty_source - secondary source used to identify the dynasty
rulers_coded - takes a 1 if rulers for that dynasty are present in the rulers dataset
rulers_source - secondary source with corresponding list of rulers
fs_start - start year associated with father-to-son succession practices
fs_end - end year associated with father-to-son succession practices
IACW_primary_start - start year associated with primary reliance on IACW
IACW_primary_end - end year associated with primary reliance on IACW
IACW_partial_start - start year associated with partial reliance on IACW
IACW_partial_end - end year associated with partial reliance on IACW
start_core - location of dynasty's geographic core at founding
pres_country - two letter country code associated with present day entity in which the start core lies
proxy_location - present-day proxy location for dynasty's core
core_latitude - proxy location latitude
core_longitude - proxy location longitude
successor - identity of successor
IACW_successor - takes a value of 1 if the successor relied primarily or partially on IACW, and 0 otherwise
fs_successor - takes a value of 1 if the successor had FS succession norms, and 0 otherwise
dynastic_end_conquest - takes a value of 1 if the dynasty was terminated via external conquest
core_region - Eurasian region in which the start core lies
state_history - the count of centuries in which any polity was present at the start core's location
inner_asia_core_dist - distance from Inner Asia in kilometers
EPR1_ID - ID for Eurasian Pseudo-regions scheme 1
EPR2_ID - ID for Eurasian Pseudo-regions scheme 2
EPR3_ID - ID for Eurasian Pseudo-regions scheme 3

#Polity-Century Data:

polity_name - spatial source name for entity
source - source for spatial data
Layer_year - century snapshot for a given polity
Entity_Area_Name - Truhart (1996) name for entity
truhart_id - ID assigned to polity in Truhart's (1996) Historical Dictionary of States
SUM_IAC_all - sum of battles in which one or more parties relied on IACW
SUM_Inter_state - sum of battles that involve opposing polities
SUM_Intra_state - sum of battles that involve opposing parties from within a single polity
SUM_HYDE_pop - estimated total population based on HYDE data
mean_elevation - estimated average elevation in meters
mean_open_terrain - proportion of polity's territory classified as either steppe/grassland or open shrubland
inner_asia_border_dist - shortest distance between a polity's border and Inner Asia
landform - whether polity's centroid lies within a peninsula, island, or (otherwise) continental landmass
warm_water_coast - dummy variable that takes a value of 1 if a polity's border contacts a sub-arctic coastline

#Rulers Data:

polity_name - designation for a dynasty's associated polity
truhart_id - ID assigned to polity in Truhart's (1996) Historical Dictionary of States
dynasty_name - designation for dynasty
dynasty_id - unique ID for dynasties
ruler - name of ruler
duration - count of years in power
start_year - first year in power
end_year - last year in power
deposed - ruler was forcibly removed from power by a domestic actor
previous_duration - time in power of previous ruler from the same dynasty
military_slave_corps - dummy variable indicating whether the ruler had access to military slaves (e.g. Mamlukism)
dynastic_order - the ruler's order in a dynastic sequence
parliament - dummy variable indicating the presence of a parliament
son - dummy variable indicating whether a ruler is the son of the previous ruler
father_to_son - father-to-son succession is customary
IACW - the ruler's dynasty relies on IACW at the outset of her rule
core - geographic proxy for the main territories initially associated with a ruler's dynasy
core_latitude - latitude for the core proxy
core_longtude - longitude for the core proxy
core_region - Eurasian region in which the start core lies
state_hist - count of centuries preceding a rulers ascent for which a state entity overlapped with the core proxy location
GRID_ID_250k - ID for a given two-hundred and fifty thousand square kilometer grid cell
GRID_ID_500k - ID for a given five-hundred thousand square kilometer grid cell
GRID_ID_1000k - ID for a given millon square kilometer grid cell



