# Title: Mapping the plague through natural language processing
# Author: Fabienne Krauer, University of Oslo
# Last updated: 16.05.2022

# This script requires the following files:
# - sticker_standard_toponyms.rds
# - sticker_OCR.txt
# - sticker_textprep.rds
# - countrycodes.txt
# - sticker_chapters.txt

# This script produces the following files:
# - plague_sticker_v1.rds
# - plague_sticker_v1.csv

# This script contains data cleaning steps that were done manually in excel and 
# can therefore not be run fully

# Housekeeping ----------------------------------------------------------
rm(list=ls())
set.seed(42)

library(readr)
library(readxl)
library(xlsx)
library(stringr)
library(dplyr)

library(RCurl)
library(rjson)

source("func_authenticate.R")
source("func_geocode_arcgis.R")
source("func_haversine.R")

# LOAD DATA ----------------------------------------------------------

standard_topo <- readRDS("data/sticker_standard_toponyms.rds")
orig <- read_file("data/sticker_OCR.txt") # Original OCR text
text <- readRDS("data/sticker_textprep.rds") # OCR text without authors in parenthesis
countrycodes <- read.delim("data/countrycodes.txt", encoding="UTF-8", stringsAsFactors=FALSE)
chapters <- read.delim("data/sticker_chapters.txt", header=T,  sep = "\t")

# PREPROCESSING ----------------------------------------------------------

# The following section generates text snippets around each toponym, which are 
# are used to assess whether this is related to a specific outbreak. This is done manually in Excel
tocheck <- standard_topo[standard_topo$type=="location",]
# Assign chapter to each toponym
tocheck$chapter <- NA
for (i in 1:nrow(chapters)) {
  tocheck$chapter <- ifelse(tocheck$start>=chapters$start[i] & tocheck$end<=chapters$end[i], 
                             chapters$chapter[i], tocheck$chapter)
  
}

# Extract text snippet of 200 characters around each location
tocheck$snippet <- NA
for (i in 1:nrow(tocheck)) {
  tocheck$snippet[i] <- substr(orig, tocheck$start_orig[i]-100, tocheck$end_orig[i]+100)
}

# Extract positions of years
yearpos <- cbind(data.frame(str_extract_all(text, "1[3-9][0-9]{2}(-[0-9][0-9])?((?<=-[0-9][0-9])[0-9][0-9])?")),
                 data.frame(str_locate_all(text, "1[3-9][0-9]{2}(-[0-9][0-9])?((?<=-[0-9][0-9])[0-9][0-9])?")))
colnames(yearpos)[1] <- "year"

# remove numbers before 1346 and after 1908
yearpos <- cbind(yearpos,  data.frame(str_split_fixed(yearpos$year, "-", 2), stringsAsFactors=F))
yearpos$X1 <- as.numeric(yearpos$X1)
yearpos <- yearpos[yearpos$X1>=1346 & yearpos$X1<=1908,]

tocheck <- merge(yearpos[,c(1:3)], tocheck, by=c("start", "end"), all=T)
tocheck <- tocheck[order(tocheck$start),]

# Extract author names
authors <- cbind(data.frame(str_locate_all(orig, "\\([^\\(\\)]+\\)")),
                 data.frame(str_extract_all(orig, "\\([^\\(\\)]+\\)"), stringsAsFactors = F))
colnames(authors) <- c("start_orig", "end_orig", "authors")

tocheck <- merge(tocheck, authors, by=c("start_orig", "end_orig"), all=T)
tocheck$authors <- gsub("\\(|\\)", "", tocheck$authors)
tocheck <- tocheck[order(tocheck$start),]

write.xlsx(tocheck, "data/sticker_tocheck1.xlsx", row.names = F, showNA = F)
    
# --> The final linking of outbreak related toponyms and the corresponding years and authors is done manually in excel (unfortunately)
    
# BATCH GEOCODING --------------------------------------------------------

# Read the checked dataset and add ID
uncoded <- read_excel("data/sticker_checked1.xlsx")
uncoded$authors <- gsub("\\.$", "", uncoded$authors)
uncoded <- uncoded[order(uncoded$year, uncoded$start),]
uncoded$id <- 1:nrow(uncoded)
uncoded <- uncoded[order(uncoded$id),]
uncoded$locid <- as.numeric(factor(uncoded$token))
uncoded_unique <- uncoded[!duplicated(uncoded$token),c("token", "locid")]

arcgis <- data.frame("locid"=0)
for (i in 1:nrow(uncoded_unique)) {
  result <- geocode.ag(uncoded_unique$token[i], max=1, token=arcGIS, language="en", storage=TRUE)
  result <- cbind("locid"=uncoded_unique$locid[i], result)
  arcgis <- merge(arcgis, result, by=intersect(names(arcgis), names(result)), all=T)
}
rm(result)
arcgis <- arcgis[arcgis$locid!=0,]


geocoded <- merge(uncoded, geocoded, by="locid", all=T)
write.xlsx(geocoded, "data/sticker_tocheck2.xlsx", row.names = F, showNA = F)

# --> The final checking of the location data is done manually in excel


# FINALIZING  --------------------------------------------------------

#Read the checked dataset
data <- read_excel("data/sticker_checked2.xlsx")

# Correct country affiliation for disputed territories to "de jure" affiliation: KRIM
data$country <- ifelse(data$ShortLabel %in% c("Khersones", "Feodosia", "Kerch", "Perekop") & data$country=="RUS" , 
                       "UKR", data$country)

# Remove country affiliation for West Indies
data$country <- ifelse(data$token=="Westindien", NA, data$country)

# Convert country names to ISO-2 codes
data <- merge(data, countrycodes[c("code_alpha2", "code_alpha3", "name_en")], by.x="Country", by.y="code_alpha3", all.x=T)
data <- data[,c("id", "token", "year", "start", "end", "start_orig", "end_orig", "ShortLabel", "LongLabel", "Addr_type", "Type", 
                "name_en", "country_ISO3", "country_ISO2", "LangCode", "Y", "X", "Ymin", "Xmin", "Ymax", "Xmax", "status",
                "mode", "remark", "doublecount", "authors")]

colnames(data)[12:14] <- c("country", "country_ISO3", "country_ISO2")

# Assign unique locid
data <- data[order(data$id),]
data$locid <- as.numeric(factor(paste0(data$Y, data$X)))
data$locid <- ifelse(data$status=="unknown", NA, data$locid)

# Calculate diameter of bounding box
data$bbox_diam_km <- calcdist(data$Xmax, data$Ymax, data$Xmin, data$Ymin)

data$type <- ifelse(data$Type %in% c("City", "Neighborhood", "Ruin", "Village", "District", "Hill", "Landmark", "Municipality", "Tourist Attraction"), "Place", 
                       ifelse(data$Type %in% c("County", "State or Province", "Community"), "Administrative Unit",
                              ifelse(data$Type %in% c("Colloquial Area", "Zone", "Mountain", "Mountain Range", "Plateau", "Stream", "Park", 
                                                      "Forest", "Gulf", "Lake", "Historical Region", "Other Land Feature",
                                                      "Territory", "Valley"), "Region", 
                                     data$Type)))

table(data$Type, data$type)

data$decade <- paste(data$year - (data$year %% 10), data$year - (data$year %% 10) + 9, sep="-")
data$century <- as.numeric(gsub("[0-9]{2}$", "", data$year)) + 1

colnames(data)[2] <- "name_orig"
colnames(data)[9] <- "name"
colnames(data)[10] <- "name_detail"
colnames(data)[11] <- "type_detail"
colnames(data)[16] <- "lat"
colnames(data)[17] <- "lon"
colnames(data)[18] <- "lat_min"
colnames(data)[19] <- "lon_min"
colnames(data)[20] <- "lat_max"
colnames(data)[21] <- "lon_max"

saveRDS(data, "data/plague_sticker_v1.rds")

write_excel_csv(data, 
            path="data/plague_sticker_v1.csv",
            na="",
            col_names = T,
            append=F)

