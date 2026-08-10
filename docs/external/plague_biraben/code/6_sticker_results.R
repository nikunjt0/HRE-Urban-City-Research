# Title: Mapping the plague through natural language processing
# Author: Fabienne Krauer, University of Oslo
# Last updated: 16.05.2022

# This file replicates all figures, analyses and tables from the paper

# This script requires the following files:
# - sticker_standard_toponyms.rds
# - sticker_comparison_NER.rds
# - sticker_comparison_geocoding.rds
# - sticker_google_tokens.rds
# - sticker_google_entities.rds
# - sticker_coreNLP_tokens.rds
# - sticker_spacy_tokens.rds
# - sticker_geoparser_entities.rds
# - sticker_germaner_entities.rds
# - plague_sticker_v1.rds
# - plague_biraben_v1.rds

# This script produces the following files:
# - fig1.tiff
# - fig2.tiff
# - fig3.tiff
# - table1.txt

# - tableS4.txt
# - figS2.tiff
# - figS3.tiff
# - figS4.tiff
# - figS5.tiff
# - figS6.tiff


# The natural earth shapefiles for the map are not provided, but can be downloaded here:
# https://www.naturalearthdata.com/downloads/

# Housekeeping ----------------------------------------------------------

rm(list=ls())
set.seed(42)

library(tidyverse)
library(rgdal)
library(grid)
library(gridExtra)
library(reshape2)

source("func_performance.R")
source("func_tableS4.R")
source("func_tableS5.R")

fignosize <- 18

theme_set(theme_light())

# Get data -----------------------------------------------------------------
sticker <- readRDS("data/plague_sticker_v1.rds")
biraben <- readRDS("data/plague_biraben_v1.rds")

standard_topo <- readRDS("data/sticker_standard_toponyms.rds")

comparison_NER <- readRDS("data/sticker_comparison_NER.rds")
# Add the type of location identified in the plague dataset
comparison_NER <- sticker %>% 
                  select(name, start, status, type_detail) %>% 
                  filter(status!="unknown") %>% 
                  group_by(start) %>% slice(1) %>% 
                  merge(comparison_NER, ., by="start", all=T)

comparison_geo <- readRDS("data/sticker_comparison_geocoding.rds")

google_tokens <- readRDS("data/sticker_google_tokens.rds")
google_entities <- readRDS("data/sticker_google_entities.rds")
coreNLP_tokens <- readRDS("data/sticker_coreNLP_tokens.rds")
spacy_tokens <- readRDS("data/sticker_spacy_tokens.rds")
geoparser_entities <- readRDS("data/sticker_geoparser_entities.rds")
germaner_entities <- readRDS("data/sticker_germaner_entities.rds")

# make base map
map <- readOGR("data/NatEarth/ne_10m_admin_0_countries", "ne_10m_admin_0_countries")
map@data$id<-rownames(map@data)
map <- fortify(map, region="id")

# Descriptive results  ---------------------------------------------------------

# Gold standard
nrow(standard_topo); table(standard_topo$entity); prop.table(table(standard_topo$entity))
nrow(sticker); 
nrow(sticker)/nrow(standard_topo[standard_topo$entity=="location",])
table(sticker$status)

# Plague dataset
round(prop.table(table(sticker$status))*100,1)
table(sticker$type_detail[sticker$status=="approximate"])
max(sticker$locid, na.rm=T)
length(unique(sticker$locid[sticker$status=="exact"]))


# countries
length(unique(sticker$country_ISO2[sticker$status=="exact"]))
sort(table(sticker$country_ISO2[sticker$status=="exact"]), decreasing=T)
sort(round(prop.table(table(sticker$country_ISO2[sticker$status=="exact"]))*100,1), decreasing=T)

# types
sort(table(sticker$type_detail[sticker$status=="exact"]), decreasing=T)
sort(round(prop.table(table(sticker$type_detail[sticker$status=="exact"]))*100, 2), decreasing=T)

# Frequency of locations
sort(table(sticker$name[sticker$status=="exact"]), decreasing=T)[1:20]
sort(round(prop.table(table(sticker$name[sticker$status=="exact"]))*100,1), decreasing=T)[1:20]

summary(sticker$bbox_diag_km[sticker$status=="exact"])

# Successful geocoding by type of geographical entity
sticker %>% group_by(type_detail) %>% 
  dplyr::summarise(n = n(), pct = 100*length(mode[mode=="auto"])/n()) %>% 
  arrange(pct)

prop.table(table(sticker$mode))

# NER ------------------------------------------------


# Tables and Figures  ----------------------------------------------------


## TABLE 1: Performance of all three algorithms compared to Gold standard -----

# Accepting partial and full matches

 # Performance
table1 <- cbind(
          round(performance(comparison_NER$entity, comparison_NER$entity_google, "Google"),2), # Google 
          round(performance(comparison_NER$entity, comparison_NER$entity_coreNLP, "Stanford CoreNLP"),2), # Stanford COreNLP
          round(performance(comparison_NER$entity, comparison_NER$entity_spacy, "spaCy"),2), # spaCy
          round(performance(comparison_NER$entity, comparison_NER$entity_germaner, "germaNER"),2), # germaNER
          round(performance(comparison_NER$entity, comparison_NER$entity_geoparser, "geoparser"),2) # Geoparser
        )

table1 <- data.frame(cbind(rownames(table1), table1))
table1

write_csv(table1, "data/table1.txt")


## TABLE S4: Numbers of tokens and entities -------------------------------------

tableS4 <- func_tableS4(standard_topo, 
                        google_entities, 
                        google_tokens,
                        spacy_tokens, 
                        coreNLP_tokens,
                        germaner_entities,
                        geoparser_entities,
                        comparison_NER)
tableS4

write_csv(tableS4, "data/tableS4.txt")


# Locations found by all algorithms
prop.table(table(comparison_NER$alltrue[comparison_NER$entity=="location"]))

# Locations missed by all algorithms
prop.table(table(comparison_NER$nonetrue[comparison_NER$entity=="location"]))
sort(unique(comparison_NER$token[comparison_NER$nonetrue==1]))

# Locations falsely identified as location by all three algorithms
sort(unique(comparison_NER$token[comparison_NER$allfalse==1]))


## Fig S2: false positives --------------

FP <- comparison_NER %>%
      filter(entity=="other") %>% 
      select(token, entity, entity_google, entity_spacy, entity_coreNLP, entity_geoparser, entity_germaner) %>% 
      pivot_longer(cols=3:7, names_to = "algo", values_to = "cat") %>% 
      dplyr::filter(cat=="location") %>% 
      group_by(algo, token) %>% 
      dplyr::summarise(count=n()) 
FP$algo <- gsub("^entity_", "", FP$algo)

figS2 <- ggplot(FP[FP$count>10,]) + 
        geom_bar(aes(x=count, y=token), stat="identity") + 
        facet_wrap(~algo, ncol=5) + ylab(NULL)
figS2
ggsave("figs/figS2.tiff", figS2, width=20, height=25, unit="cm", dpi=300)

## Fig S3: false negatives --------------

FN <- comparison_NER %>%
  filter(entity=="location") %>% 
  select(token, type_detail, entity, entity_google, entity_spacy, entity_coreNLP, entity_geoparser, entity_germaner) %>% 
  pivot_longer(cols=4:8, names_to = "algo", values_to = "cat") %>% 
  dplyr::filter(cat=="other") %>% 
  group_by(algo, token) %>% 
  dplyr::arrange(type_detail) %>% 
  dplyr::summarise(type = type_detail[1], count=n())
FN$algo <- gsub("^entity_", "", FN$algo)

figS3 <- ggplot(FN[FN$algo!="geoparser" & FN$count>5,]) + 
  geom_bar(aes(x=count, y=token), stat="identity") + 
  facet_wrap(~algo, ncol=5) + ylab(NULL)
figS3
ggsave("figs/figS3.tiff", figS3, width=20, height=30, unit="cm", dpi=300)


## Fig S4: False negatives by toponym type --------------

FN_type <- comparison_NER %>%
            filter(entity=="location" & !is.na(status)) %>% 
            select(token, type_detail, entity, entity_google, entity_spacy, entity_coreNLP, entity_geoparser, entity_germaner) %>% 
            pivot_longer(cols=4:8, names_to = "algo", values_to = "cat")  %>% 
            group_by(type_detail, algo) %>% 
            dplyr::summarise(n = n(), 
                             FN = length(cat[cat=="other"]), 
                             prop_FN = 100 * FN / n)
FN_type$algo <- gsub("^entity_", "", FN_type$algo)
FN_type$label <- paste0(FN_type$type_detail, " ( n = ", FN_type$n,") ")


# Type of FN entity by algorithm
figS4 <- ggplot(FN_type) + 
        geom_bar(aes(x=prop_FN, y=label), stat="identity") + 
        facet_wrap(~algo, ncol=5) + ylab(NULL) + 
        xlab("percentage of false negatives")
figS4
ggsave("figs/figS4.tiff", figS4, width=22, height=12, unit="cm", dpi=300)


# Geocoding -------------------------------------------

# Pct of toponyms located

# Google
table(comparison_geo$status_google)
round(prop.table(table(comparison_geo$status_google))*100,1)
# Geonames
table(comparison_geo$status_geonames)
round(prop.table(table(comparison_geo$status_geonames))*100,1)
# Geoparser
table(comparison_geo$status_geoparser)
round(prop.table(table(comparison_geo$status_geoparser))*100,1)

# Pct of toponyms correctly located

# Google
table(comparison_geo$match_google)
round(prop.table(table(comparison_geo$match_google))*100,2)
# Geonames
table(comparison_geo$match_geonames)
round(prop.table(table(comparison_geo$match_geonames))*100,2)
# Geoparser
table(comparison_geo$match_geoparser)
round(prop.table(table(comparison_geo$match_geoparser))*100,2)

# Mismatches by country
mismatch_country <- comparison_geo %>% 
            filter(!is.na(country)) %>% 
            group_by(country) %>% 
            dplyr::summarise(n=n(),
                             prop_mismatch_google=length(match_google[match_google==0])/n(),
                             prop_mismatch_geonames=length(match_geonames[match_geonames==0])/n(),
                             prop_mismatch_geoparser=length(match_geoparser[match_geoparser==0])/n())

mismatch_country %>% filter(prop_mismatch_google>0.5 & n>5) %>% 
  select(country, prop_mismatch_google) %>% 
  arrange(-prop_mismatch_google)

mismatch_country %>% filter(prop_mismatch_geonames>0.5 & n>5) %>% 
              select(country, prop_mismatch_geonames) %>% 
              arrange(-prop_mismatch_geonames)

            
mismatch_country %>% filter(prop_mismatch_geoparser>0.5 & n>5) %>% 
              select(country, prop_mismatch_geoparser) %>% 
              arrange(-prop_mismatch_geoparser)
              

# Matches by type
match_type <- comparison_geo %>% 
              filter(!is.na(type_detail)) %>% 
              select(type_detail, match_google, match_geonames, match_geoparser) %>% 
              group_by(type_detail) %>% 
              pivot_longer(., cols=2:4, names_to = "algo", values_to = "match") %>% 
              dplyr::group_by(type_detail, algo) %>% 
              dplyr::summarise(n=n(),
                               prop_match=100*length(match[match==1])/n())
              
match_type$label <- paste0(match_type$type_detail, " ( n = ", match_type$n,") ")
match_type$algo <- recode(match_type$algo, "match_geonames"= "Geonames", "match_geoparser"="Geoparser", "match_google"="Google")

figS5 <- ggplot(match_type) + 
  geom_bar(aes(x=prop_match, y=label), stat="identity") + 
  facet_wrap(~algo, ncol=5) + ylab(NULL) + 
  xlab("percentage of correctly geolocated toponyms")
figS5
ggsave("figs/figS5.tiff", figS5, width=22, height=12, unit="cm", dpi=300)


# Biraben vs. Sticker ----------------------------------


# Fig. 1 ===========================================================================

summary(sticker$lon)
summary(sticker$lat)

fig1 <- ggplot(data=map) +
  theme_classic() +
  ylab("Latitude") + xlab("Longitude") +
  geom_polygon(aes(x=long, y=lat, group=group), fill="grey85", colour=NA) +
  geom_path(aes(x=long, y=lat, group=group), colour="white", size=0.005) +
  geom_point(data=sticker, aes(x=lon, y=lat), colour="red", size=0.5) +
  scale_y_continuous(expand=c(0,0)) +
  scale_x_continuous(expand=c(0,0)) +
  coord_fixed(ratio=1, xlim=c(min(sticker$lon, na.rm=T)-2, max(sticker$lon, na.rm=T)+2), 
              ylim=c(min(sticker$lat, na.rm=T)-2, max(sticker$lat, na.rm=T)+2)) 
fig1

tiff(file = paste0("figs/fig1.tiff"),
     width = 6000,
     height = 3000,
     res = 600)
fig1
dev.off()


# Prep data for comparison

# Outbreaks per country
country1 <- sticker %>% dplyr::filter(!is.na(country)) %>% dplyr::group_by(country) %>% 
  dplyr::summarise(n=n(), pct=round(n()/nrow(sticker)*100,1), ntotal=nrow(sticker[!is.na(sticker$country),]), data="Sticker")
country2 <- biraben %>% dplyr::filter(!is.na(country)) %>% dplyr::group_by(country) %>% 
  dplyr::summarise(n=n(), pct=round(n()/nrow(biraben)*100,1), ntotal=nrow(sticker[!is.na(biraben$country),]), data="Biraben")
countries <- merge(country1, country2, by=intersect(names(country1), names(country2)), all=T)
countries <- countries %>% dplyr::group_by(country) %>% dplyr::mutate(maxpct =max(pct[data=="Sticker"], pct[data=="Biraben"], na.rm=T))
countries$country <- ifelse(countries$maxpct<4,"Other", countries$country)
countries <- countries %>% dplyr::group_by(country, data) %>% dplyr::summarise(n=sum(n, na.rm=T), pct=n*100/ntotal[1])
countries$country <- gsub("\\(.+\\)$", "", countries$country)
countries$country <- ifelse(countries$country=="United Kingdom of Great Britain and Northern Ireland ","UK",countries$country)
countries$country <- ifelse(countries$country=="Russian Federation ","Russia",countries$country)

# Outbreaks per place
places1 <- sticker %>% dplyr::filter(type=="Place") %>% dplyr::group_by(name) %>% 
  dplyr::summarise(n=n(), pct=round(n()/nrow(sticker)*100,1), ntotal=nrow(sticker), data="Sticker")
places2 <- biraben %>% dplyr::filter(type=="Place") %>% dplyr::group_by(name) %>% 
  dplyr::summarise(n=n(), pct=round(n()/nrow(biraben)*100,1), ntotal=nrow(biraben), data="Biraben")
places <- merge(places1, places2, by=intersect(names(places1), names(places2)), all=T)
places <- places %>% dplyr::group_by(name) %>% dplyr::mutate(maxpct =max(pct[data=="Sticker"], pct[data=="Biraben"], na.rm=T))
places <- places[places$maxpct>0.5,]

# Outbreaks per year
year1 <- sticker %>% dplyr::group_by(year) %>% dplyr::summarise(n=n(), data="Sticker")
year2 <- biraben %>% dplyr::group_by(year) %>% dplyr::summarise(n=n(), data="Biraben")
year <- merge(year1, year2, by=intersect(names(year1), names(year2)), all=T)

rm(list=c("country1", "country2", "places1", "places2", "year1", "year2"))


# Results: Summary statistics
countries[countries$data=="Sticker", c("country", "pct")]
countries[countries$data=="Biraben", c("country", "pct")]

# Table S5 --------------------------------------

tableS5 <- func_tableS5(sticker, biraben)
write_csv(tableS5, "data/tableS5.txt")


# Merge all geocoded locations
merge <- merge(sticker[sticker$status!="unknown",c("id", "lat", "lon", "locid", "year", "name_orig", "name", "country_ISO3", "bbox_diag_km", "type")], #"country", "bbox_diam_km", "status")], 
               biraben[biraben$status!="unknown",c("id", "lat", "lon", "locid", "year", "name_orig", "name", "country_ISO3", "bbox_diag_km", "type")], #"country", "bbox_diam_km", "status", "locid")], 
               by=c("year", "lat", "lon"), all=T)
merge$set <- ifelse(!is.na(merge$id.x) & is.na(merge$id.y), "Sticker", 
                    ifelse(is.na(merge$id.x) & !is.na(merge$id.y), "Biraben", "both"))

table(merge$set)



# Limit to Spatio-temporal extent of the second Pandemic
merge <- merge[((merge$type.x=="Place" & !is.na(merge$type.x)) | 
                   (merge$type.y=="Place" & !is.na(merge$type.y))) & 
                  merge$year<1894,]

# Omit Nanking and Pakhoi, these are third pandemic, but before 1894
merge <- merge[!(merge$name.x %in% c("Nanking", "Pakhoi")),]


merge_map <- melt(merge, id.vars=c("year", "lon", "lat"), 
                  measure.vars=c("name.x", "name.y"), value.name = "place")
merge_map <- merge_map[!is.na(merge_map$place),-4]
merge_map$century <- as.numeric(substr(as.character(merge_map$year), 1,2))+1
merge_map$century2 <- ifelse(merge_map$century== 14, "1346-1399",
                             ifelse(merge_map$century== 15, "1400-1499",
                                    ifelse(merge_map$century==16, "1500-1599",
                                           ifelse(merge_map$century==17, "1600-1699",
                                                  ifelse(merge_map$century==18, "1700-1799", "1800-1894")))))


summary(merge_map$lon)
summary(merge_map$lat)

table(merge$set)
length(unique(merge$locid.x[merge$set=="Sticker"]))

# Count outbreaks by place
merge_summary <- merge_map %>% dplyr::group_by(lon, lat, place) %>% 
            dplyr::summarise(n=n()) %>% 
            dplyr::arrange(-n) %>% 
            dplyr::mutate(order=1:n())


# Fig. 2 ============================================================================

fig2 <- ggplot() + 
  theme_minimal() +
  theme(panel.grid.major = element_blank()) +
  ylab("Latitude") + xlab("Longitude") +
  geom_polygon(data=map, aes(x=long, y=lat, group=group), fill="grey85", colour=NA) +
  geom_path(data=map, aes(x=long, y=lat, group=group), colour="white", size=0.01) +
  geom_point(data=merge[merge$set=="Biraben",], aes(x=lon, y=lat), colour=bircol, size=0.5) +
  geom_point(data=merge[merge$set=="Sticker",], aes(x=lon, y=lat), colour=sticol, size=0.5) +
  geom_point(data=merge[merge$set=="both",], aes(x=lon, y=lat), colour=allcol, size=0.5) +
  coord_fixed(ratio=1,
              #xlim=c(-22,90),
              #ylim=c(15,65)) 
              xlim=c(min(merge_map$lon), max(merge_map$lon)),
              ylim=c(min(merge_map$lat), max(merge_map$lat)))
fig2


tiff(file = paste0("figs/fig2.tif"),
     width = 5800,
     height = 3000,
     res = 600)
fig2
dev.off()


# Fig. 3 ============================================================================

fig3 <- vector("list", length(unique(merge_map$century2)))
count <- 1
for (i in unique(merge_map$century2)) {
  
  foo <- ggplot() + 
    theme_minimal() +
    theme(panel.grid.major = element_blank()) +
    ylab("Latitude") + xlab("Longitude") +
    geom_polygon(data=map, aes(x=long, y=lat, group=group), fill="grey80", colour=NA) +
    geom_path(data=map, aes(x=long, y=lat, group=group), colour="white", size=0.01) +
    #geom_point(data=merge_map, aes(x=lon, y=lat, colour=as.factor(century)), size=0.5) +
    geom_point(data=merge_map[merge_map$century2==i,], aes(x=lon, y=lat), colour="magenta", size=0.5) +
    ggtitle(i) +
    coord_fixed(ratio=1,
                #xlim=c(-22,90),
                #ylim=c(15,65)) 
                xlim=c(min(merge_map$lon), max(merge_map$lon)),
                ylim=c(12, max(merge_map$lat)))
  
  fig3[[count]] <-  ggplotGrob(foo)
  count <- count + 1
}

tiff(file = paste0("figs/fig3.tiff"),
     width = 8000,
     height = 5000,
     res = 600)
grid.arrange(arrangeGrob(grobs=fig3, ncol=2)) #x=unit(0, "npc"), y=unit(1, "npc"), just=c("left", "top"), 
#gp=gpar(col="black", fontsize=size), ncol=1))
dev.off()





# Fig. S5 ============================================================================

bircol <- "grey25"
sticol <- "magenta"
allcol <- "turquoise4"

figS5a <- ggplot(countries) + theme_minimal() + 
  xlab(NULL) + ylab("Percentage of total observations") +
  geom_bar(aes(x=country, y=pct, fill=data), stat="identity", position="dodge") +
  scale_fill_manual(values=c(bircol, sticol), breaks=c("Biraben", "Sticker")) +
  scale_y_continuous(expand=c(0,0)) + coord_flip()

figS5a


figS5b <- ggplot(places) + theme_minimal() + 
  xlab(NULL) + ylab("Number of mentions") +
  geom_bar(aes(x=name, y=n, fill=data), stat="identity", position=position_dodge(preserve = "single")) +
  scale_fill_manual(values=c(bircol, sticol), breaks=c("Biraben", "Sticker")) +
  scale_y_continuous(expand=c(0,0)) + coord_flip()

figS5b


figS5c <- ggplot(data=year) + theme_light() +
  geom_line(aes(x=year, y=n, colour=data)) + 
  ylab("N of locations with plague") + xlab("Year") +
  scale_x_continuous(breaks=c(1400, 1500, 1600, 1700, 1800, 1900),
                     expand=c(0.01,0)) +
  scale_color_manual(values=c(bircol, sticol), breaks=c("Biraben", "Sticker")) +
  # scale_x_continuous(labels=date_format("%lat"),
  #                    breaks=date_breaks("50 years"),
  #                    expand=c(0.01,0)) +
  scale_y_continuous(expand=c(0,0))
figS5c


tiff(file = paste0("figs/figS5.tif"),
     width = 6000,
     height = 5000,
     res = 600)
grid.arrange(arrangeGrob(figS5a, top=textGrob("A", x=unit(0, "npc"), y=unit(0, "npc"), 
                                              just=c("left", "top"), gp=gpar(col="black", fontsize=fignosize))), 
             arrangeGrob(figS5b, top=textGrob("B", x=unit(0, "npc"), y=unit(0, "npc"), 
                                              just=c("left", "top"), gp=gpar(col="black",fontsize=fignosize))),
             arrangeGrob(figS5c, top=textGrob("C", x=unit(0, "npc"), y=unit(0, "npc"), 
                                              just=c("left", "top"), gp=gpar(col="black",fontsize=fignosize))),
             
             layout_matrix=rbind(c(1,2),c(3,3)))
dev.off()


# Fig. S6: Boxplot of types and bounding box diagonal ==========================================

types <- sticker[!duplicated(sticker$locid),c("bbox_diag_km", "type")]
types$set <-"Sticker"
types <- rbind(types, cbind(biraben[!duplicated(biraben$locid),c("bbox_diag_km", "type")], "set"="Biraben"))
types <- types[!is.na(types$type),]

figS6 <- ggplot(types) + 
  geom_boxplot(aes(x=type, y=bbox_diag_km, fill=set)) + theme_minimal() +
  xlab(NULL) + ylab("Diagonal of the bounding box (km) \n") +
  scale_fill_manual(values=c(bircol, sticol), breaks=c("Biraben", "Sticker")) +
  scale_y_log10() 
figS6

tiff(file = paste0("figs/figS2.tif"),
     width = 4000,
     height = 4000,
     res = 600)
figS6
dev.off()




