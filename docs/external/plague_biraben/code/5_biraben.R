# Title: Mapping the plague through natural language processing
# Author: Fabienne Krauer, University of Oslo
# Last updated: 16.05.2022

# This script requires the following files:
# - biraben_annex4.txt. Note this file is not provided for copyright reasons. 

# This script produces the following files:
# - plague_biraben_v1.rds
# - plague_biraben_v1.csv

# This script contains data cleaning steps that were done manually in excel and 
# can therefore not be run fully

# Housekeeping ----------------------------------------------------------

rm(list=ls())
library(dplyr)
library(tidyr)
library(rjson)
library(readr)
library(ggplot2)

source("func_authenticate.R")
source("func_geocode_google.R")
source("func_geocode_arcgis.R")
source("func_haversine.R")


# CLEANING OF RAW DATA -------------------------------------------------

# get raw data
ncol <-  max(count.fields("data/biraben_annex4.txt", sep = "\t", quote = ""), na.rm = TRUE)

data <- read.delim("data/biraben_annex4.txt",
                   header = FALSE,
                   sep = "\t",
                   quote = "",
                   col.names = paste0("location_", 1:ncol),
                   na.strings = "",
                   as.is = TRUE,
                   fill = TRUE,
                   strip.white = TRUE,
                   encoding = "UTF-8")

# add column for chapter information
colnames(data)[1] <- "year"
data$chapter <- data$year
data$chapter <- gsub("[0-9]+", NA, data$chapter)

for (i in seq_along(data$chapter)[-1]) {
  if (is.na(data$chapter[i])) {
    data$chapter[i] <- data$chapter[i-1]
  }
} 

data <- subset(data, data$year!=data$chapter)

#reshape to long
data <- reshape(data, direction="long", varying = c(2:ncol), idvar="id", sep="_")
chapters <- unique(data$chapter)
data <- data %>% group_by(chapter) %>% mutate(chapno = which(chapters==chapter[1]))
data <- data[order(data$chapno, data$year, data$time),]
data <- data[!is.na(data$location),-c(5:6)]
colnames(data)[3] <- "id"
data$id <- 1:nrow(data)
data$year <- as.numeric(data$year)

#tag uncertain locations (defined as single entries with question marks)
data$certain <- ifelse(grepl("\\?", data$location),0,1)
data$location <- ifelse(data$certain==0, gsub("\\?", "", data$location),data$location)

# Define level of spatial precision as given by biraben (names in brackets are "regions")
data$type_orig <-  ifelse(grepl("^\\(", data$location),"region", "place")
data$location <- ifelse(data$type_orig=="region", gsub("^\\(|\\)$", "", data$location), data$location)

# generate group ID for each unique place name
data <- data[order(data$chapter, data$location),]
data$locid <- as.numeric(factor(paste0(data$location, data$chapter)))
data <- data.frame(data)
data <- data[order(data$id),]
colnames(data)[4] <- "name_orig"

# Generate subset with unique place names for geocoding
locs <- data[!duplicated(data$locid), colnames(data) %in% c("locid", "chapter","name_orig", "type_orig")]
locs <- data.frame(locs[order(locs$locid), c(4,2,1,3)])


# GEOCODING -------------------------------------------------

# Google

# Define countries to loop through with API query (nomenclature according to ISO 3166-1)
countrylist <- list(
  list("Allemagne, Europe centrale", 
       list("DE", "AT", "CH", "CZ", "FR", "LI")),
  list("Balkans partie nord-occidentale", 
       list("AT", "CZ", "HR", "HU", "ME", "MD", "RO", "RS", "SI", "SK", "XK")),
  list("Balkans partie sud-orientale", 
       list("AL", "BA", "BG", "HR", "GR", "HU", "MK", "MD", "ME", "RO", "RS", "TR", "UA", "XK")),
  list("Beneluxe", 
       list("BE", "LU", "NL", "FR")),
  list("France", 
       list("FR", "AD", "MC")),
  list("Iles Britanniques", 
       list("GB", "IE", "IM", "GG", "GI", "JE")),
  list("Italie", 
       list("IT", "MT", "SM", "VA")),
  list("Levante", 
       list("AM", "AZ", "BH", "CY", "GE", "IL", "PS", "IQ", "IR", "JO", "KW", "LB", "OM", "QA", 
            "SA", "SY", "TM", "TR", "TJ", "YE", "KG", "UZ")),
  list("Maghreb", 
       list("DZ", "EG", "MA", "TN", "LY")),
  list("Péninsule Ibérique", 
       list("ES","PT", "AD", "GI")),
  list("Pologne, Prusse-Orientale, Lituanie, Lettonie, Estonie", 
       list("BY", "EE", "LT", "LV", "PL", "RU")),
  list("Russie Sud-Est", 
       list("RU", "UA", "BY", "KZ", "MD", "KG", "UZ", "TJ", "TM")),
  list("Russie Nord-Ouest", 
       list("RU", "BY", "UA", "KZ", "MD")),
  list("Scandinavie", 
       list("DK", "FI", "NO", "SE", "IS", "AX", "FO", "SJ")))  


google <- data.frame()
for (i in 1:length(locs$name_orig)) {
  for (ii in 1:length(countrylist)) { #Loop through chapters to find matching entry
    if (countrylist[[ii]][[1]]==locs$chapter[i]) {
      for (iii in 1:length(countrylist[[ii]][[2]])) { # level: admin, partial: FALSE 
        result <- cbind("locid"=locs$locid[i], "chapter"=locs$chapter[i], "name_orig"=locs$name_orig[i],
                        geocode.goo(enc2utf8(locs$name_orig[i]), 
                                  country=countrylist[[ii]][[2]][[iii]],
                                  level="admin",
                                  partial=FALSE,
                                  APIkey=APIkey)) 
        if (result$status=="OK") {
          break
        }
        if (iii==length(countrylist[[ii]][[2]]) & result$status=="ZERO_RESULTS") {
          for (iii in 1:length(countrylist[[ii]][[2]])) { # level: admin, partial: TRUE 
            result <- cbind("locid"=locs$locid[i], "chapter"=locs$chapter[i], "name_orig"=locs$name_orig[i],
                            geocode.goo(enc2utf8(locs$name_orig[i]), 
                                      country=countrylist[[ii]][[2]][[iii]],
                                      level="admin",
                                      partial=TRUE,
                                      APIkey=APIkey))
            if (result$status=="OK") {
              break
            }
            if (iii==length(countrylist[[ii]][[2]]) & result$status=="ZERO_RESULTS") {
              for (iii in 1:length(countrylist[[ii]][[2]])) { # level: feature, partial: FALSE 
                result <- cbind("locid"=locs$locid[i], "chapter"=locs$chapter[i], "name_orig"=locs$name_orig[i],
                                geocode.goo(enc2utf8(locs$name_orig[i]), 
                                          country=countrylist[[ii]][[2]][[iii]],
                                          level="feature",
                                          partial=FALSE,
                                          APIkey=APIkey))
                if (result$status=="OK") {
                  break
                }
                if (iii==length(countrylist[[ii]][[2]]) & result$status=="ZERO_RESULTS") { # level: country, partial: FALSE 
                  result <- cbind("locid"=locs$locid[i], "chapter"=locs$chapter[i], "name_orig"=locs$name_orig[i],
                                  geocode.goo(enc2utf8(locs$name_orig[i]), 
                                            level="country",
                                            partial=FALSE,
                                            APIkey=APIkey))
                  if (result$status=="OK") {
                    break
                  }
                }
              }
            }        
          }  
        }
      }
      google <- rbind(google, result)
      break
    }  
  }
}


google <- google[order(google$locid, google$status),]
google <- subset(google, !duplicated(google$locid))

# combine ADM info to one field
google$name_detail <- paste(google$name, google$adm2short, google$adm1short, google$countryshort, sep=", ")

# if locations do not have an official name (but a number), replace the number with the looked-up name
google$name[grep("[[:digit:]]+", google$name)] <- checked$newname[grep("[[:digit:]]+", google$name)]

#change type of "Ireland" from establishment to "Country" (this is some weird google bug)
google$type[!is.na(google$name) & google$name=="Ireland"] <- "country"

# add country manually for locations with missing or disputed political affiliation
google$name[is.na(google$country) & !is.na(google$name)]

google$country[!is.na(google$name) & 
                   (google$name=="Feodosia" |  
                      google$name=="Crimean Peninsula" |
                      google$name=="Perekop" |
                      google$name=="Simferopol" |
                      google$name=="Kerch")] <- "Ukraine"
google$countryshort[!is.na(google$name) & 
                        (google$name=="Feodosia" |  
                           google$name=="Crimean Peninsula" |
                           google$name=="Perekop" |
                           google$name=="Simferopol" |
                           google$name=="Kerch")] <- "UA"
google$country[!is.na(google$name) & google$name=="Abkhazia"] <- "Georgia"
google$countryshort[!is.na(google$name) & google$name=="Abkhazia"] <- "GE"
google$country[!is.na(google$name) & google$name=="Famagusta"] <- "Cyprus"
google$countryshort[!is.na(google$name) & google$name=="Famagusta"] <- "CY"
google$country[!is.na(google$name) & google$name=="Ireland"] <- "Ireland"
google$countryshort[!is.na(google$name) & google$name=="Ireland"] <- "IE"
google$country[!is.na(google$name) & (google$name=="Istria" | google$name=="Istra")] <- "Croatia"
google$countryshort[!is.na(google$name) & (google$name=="Istria" | google$name=="Istra")] <- "HR"
google$country[!is.na(google$name) & google$name=="Vale of Kashmir"] <- "India"
google$countryshort[!is.na(google$name) & google$name=="Vale of Kashmir"] <- "IN"
google$country[!is.na(google$name) & (google$name=="Gaza Strip" | google$name=="Nablus")] <- "Palestine"
google$countryshort[!is.na(google$name) & (google$name=="Gaza Strip" | google$name=="Nablus")] <- "PS"
google$country[!is.na(google$name) & google$name=="Neretva"] <- "Bosnia and Herzegovina"
google$countryshort[!is.na(google$name) & google$name=="Neretva"] <- "BA"
google$country[!is.na(google$name) & google$name=="Novo Brdo"] <- "Kosovo"
google$countryshort[!is.na(google$name) & google$name=="Novo Brdo"] <- "XK"


# ArcGIS
arcgis <- data.frame("locid"=0)
for (i in 1:nrow(locs)) {
  result <- geocode.ag(locs$name_orig[i], max=1, token=arcGIS, language="en", storage=TRUE)
  result <- cbind("locid"=locs$locid[i], result)
  arcgis <- merge(arcgis, result, by=intersect(names(arcgis), names(result)), all=T)
}
rm(result)
arcgis <- arcgis[arcgis$locid!=0,]

geocoded <- merge(google, arcgis, by="locid", all=T)

# Check locations individually and add missing locs manually (this is done in excel)
write.xlsx(geocoded, "data/biraben_tocheck.xlsx", row.names = F, showNA = F)

# FINALIZE -------------------------------------------------

geocoded <- read_excel("data/biraben_checked.xlsx")

final <- merge(data, geocoded, by=c("locid", "name_orig"), all=TRUE)
final <- final[order(final$id),]
rownames(final) <- 1:nrow(final)

final$lon <- round(final$lon,4)
final$lat <- round(final$lat,4)
final$lon_min <- round(final$lon_min,4)
final$lat_min <- round(final$lat_min,4)
final$lon_max <- round(final$lon_max,4)
final$lat_max <- round(final$lat_max,4)
final$bbox_diag_km <- calcdist(final$lon_max, final$lat_max, final$lon_min, final$lat_min)

final$locid <- as.numeric(factor(paste0(final$lat, final$lon)))
final$locid <- ifelse(final$status=="unknown", NA, final$locid)

# recode types
final$type <- ifelse(final$type %in% c("City", "Neighborhood", "Ruin", "Village", "District", "Hill", "Landmark", "Municipality"), "Place", 
                       ifelse(final$type %in% c("County", "State or Province", "Community"), "Administrative Unit",
                              ifelse(final$type %in% c("Colloquial Area", "Zone", "Mountain", "Mountain Range", "Stream", "Park", "Historical Region"), "Region", 
                                     final$type)))


final$decade <- paste(final$year - (final$year %% 10), final$year - (final$year %% 10) + 9, sep="-")
final$century <- as.numeric(gsub("[0-9]{2}$", "", final$year)) + 1

saveRDS(final, "data/plague_biraben_v1.rds")
write_excel_csv(final, 
                path="data/plague_biraben_v1.csv",
                na="",
                col_names = T,
                append=F)

