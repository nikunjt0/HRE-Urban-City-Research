# Title: Mapping the plague through natural language processing
# Author: Fabienne Krauer, University of Oslo
# Last updated: 16.05.2022

# This script requires the following files:
# - plague_sticker_v1.rds
# - sticker_comparison_NER.rds

# This script produces the following files:
# - sticker_geonames_geocoded.rds
# - sticker_comparison_geocoding.rds

# Housekeeping ----------------------------------------------------------

rm(list=ls())
set.seed(42)

library(RCurl)
library(rjson)
library(dplyr)

source("func_authenticate.R")
source("func_haversine.R")
source("func_geocode_google.R")
source("func_geocode_geonames.R")

# DATA --------------------------------------------------------------------

sticker <- readRDS("data/plague_sticker_v1.rds")
geoparser <- readRDS("data/sticker_geoparser_entities.rds")

# Generate list of unique original location names for alternative geocoding
locdata <- sticker %>% group_by(name_orig) %>% slice(1)
  
# Google  ------------------------------------------------------------

google <- data.frame()
for (i in 1:length(locdata)) {
  
  Sys.sleep(5)
  result <- geocode.goo(enc2utf8(locdata$name_orig[i]), 
                        level="admin", partial=FALSE, APIkey=APIkey)
    
     
  if (result$status=="ZERO_RESULTS") {
    result <- geocode.goo(enc2utf8(locdata$name_orig[i]), 
                          level="admin", partial=TRUE, APIkey=APIkey)
  }
  
  if (result$status=="ZERO_RESULTS") {
    result <- geocode.goo(enc2utf8(locdata$name_orig[i]), 
                          level="feature", partial=TRUE, APIkey=APIkey)
  }
  
  if (result$status=="ZERO_RESULTS") {
    result <- geocode.goo(enc2utf8(locdata$name_orig[i]), 
                          level="country", partial=TRUE, APIkey=APIkey) 
  }
  
  result <- cbind("name_orig"=locdata$name_orig[i], result)
  google <- rbind(google, result)
}  

saveRDS(google, file="data/sticker_google_geocoded.rds")


# GEONAMES ------------------------------------------------------------

geonames <- data.frame(name_orig=NA)

for (i in 1:length(locdata)) {

  # Search exact
  result <- geocode.gn(place=locdata$name_orig[i], 
                        fclass=c("P", "A", "L", "T", "H", "V"), 
                        searchtype="placeexact", 
                        max=1, user=user_geonames)
  # Search fuzzy
  if (result$status[1]=="ZERO_RESULTS") {
    result <- geocode.gn(place=locdata$name_orig[i], 
                          fclass=c("P", "A", "L", "T", "H", "V"), 
                          searchtype="placefuzzy", 
                          max=1, user=user_geonames)
    # Search all
    if (result$status[1]=="ZERO_RESULTS") {
      result <- geocode.gn(place=locdata$name_orig[i], 
                            fclass=c("P", "A", "L", "T", "H", "V"), 
                            searchtype="all", 
                            max=1, user=user_geonames)
    }
  }
  
  result <- cbind("name_orig"=locdata$name_orig[i], result)
  geonames <- merge(geonames, result, by=intersect(names(geonames), names(result)), all=T)
}

geonames <- geonames[!is.na(geonames$name_orig),]
geonames$lng <- as.numeric(geonames$lng)
geonames$lat <- as.numeric(geonames$lat)

saveRDS(geonames, file="data/sticker_geonames_geocoded.rds")

# GEOPARSER ------------------------------------------------------------

geoparser <- geoparser %>% 
              filter(token %in% locdata$name_orig) %>% 
              group_by(token) %>% slice(1)
geoparser$status <- "OK"

# COMBINE ------------------------------------------------------------

colnames(google)[c(2,3,12,13,20)] <- c("lat_google", "lon_google", "countryISO2_google", "type_google", "status_google")
comparison <- merge(locdata, google[,c(1,2,3,12,13,20)], by="name_orig", all=T)
colnames(geonames)[c(2,3,10,12,16)] <- c("status_geonames", "lon_geonames", "type_geonames", "lat_geonames", "countryISO2_geonames")
comparison <- merge(comparison, geonames[,c(1,2,3,10,12,16)], by="name_orig", all=T)
colnames(geoparser)[c(2,5,8,9,15,16)] <- c("countryISO2_geoparser", "type_geoparser", "lon_geoparser", "lat_geoparser", "name_orig", "status_geoparser")
comparison <- merge(comparison, geoparser[,c(2,5,8,9,15,16)], by="name_orig", all=T)
comparison$status_geoparser <- ifelse(is.na(comparison$status_geoparser), "ZERO_RESULTS", comparison$status_geoparser)

# we will compare only located places
comparison <- comparison[comparison$status!="unknown",]

# Calculate euclidean distances between centroids of sticker and the two alternatives
comparison$dist_google <- ifelse(comparison$status_google=="OK",
                                   calcdist(comparison$lon, comparison$lat, comparison$lon_google, comparison$lat_google), NA)
comparison$dist_geonames <- ifelse(comparison$status_geonames=="OK",
                                   calcdist(comparison$lon, comparison$lat, comparison$lon_geonames, comparison$lat_geonames), NA)
comparison$dist_geoparser <- ifelse(comparison$status_geoparser=="OK",
                                    calcdist(comparison$lon, comparison$lat, comparison$lon_geoparser, comparison$lat_geoparser), NA)

# Recode type country

# Google
comparison$type_google <- ifelse(comparison$type_google=="country",
                                   "Country", comparison$type_google)


# Geonames
comparison$type_geonames <- ifelse(comparison$type_geonames=="independent political entity" | 
                                     comparison$type_geonames=="dependent political entity", 
                                   "Country", comparison$type_geonames)

# Geoparser
comparison$type_geoparser <- ifelse(comparison$type_geoparser=="independent political entity" | 
                                      comparison$type_geoparser=="semi-independent political entity" | 
                                      comparison$type_geoparser=="dependent political entity", 
                                    "Country", comparison$type_geoparser)

# Asses whether it's a match

# Google
comparison$match_google <- ifelse((comparison$country_ISO2==comparison$countryISO2_google & comparison$type_detail=="Country" & comparison$type_google=="Country") |
                                      (comparison$type_detail!="Country" & comparison$bbox_diag_km>30 & comparison$dist_google<=comparison$bbox_diag_km/2 & comparison$country_ISO2==comparison$countryISO2_google) |
                                      (comparison$type_detail!="Country" & comparison$bbox_diag_km<=30 & comparison$dist_google<=30 & comparison$country_ISO2==comparison$countryISO2_google),
                                    1,0)
comparison$match_google <- ifelse(is.na(comparison$match_google), 0, comparison$match_google)


# Geonames
comparison$match_geonames <- ifelse((comparison$country_ISO2==comparison$countryISO2_geonames & comparison$type_detail=="Country" & comparison$type_geonames=="Country") |
                                      (comparison$type_detail!="Country" & comparison$bbox_diag_km>30 & comparison$dist_geonames<=comparison$bbox_diag_km/2 & comparison$country_ISO2==comparison$countryISO2_geonames) |
                                      (comparison$type_detail!="Country" & comparison$bbox_diag_km<=30 & comparison$dist_geonames<=30 & comparison$country_ISO2==comparison$countryISO2_geonames),
                                    1,0)
comparison$match_geonames <- ifelse(is.na(comparison$match_geonames), 0, comparison$match_geonames)


# Geoparser
comparison$match_geoparser <- ifelse((comparison$country_ISO2==comparison$countryISO2_geoparser & comparison$type_detail=="Country" & comparison$type_geoparser=="Country") |
                                       (comparison$type_detail!="Country" & comparison$bbox_diag_km>30 & comparison$dist_geoparser<=comparison$bbox_diag_km/2 & comparison$country_ISO2==comparison$countryISO2_geoparser) |
                                       (comparison$type_detail!="Country" & comparison$bbox_diag_km<=30 & comparison$dist_geoparser<=30 & comparison$country_ISO2==comparison$countryISO2_geoparser),
                                     1,0)
comparison$match_geoparser <- ifelse(is.na(comparison$match_geoparser),0, comparison$match_geoparser)

saveRDS(comparison, "data/sticker_comparison_geocoding.rds")



