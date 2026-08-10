# Title: Mapping the plague through natural language processing
# Author: Fabienne Krauer, University of Oslo
# Last updated: 16.05.2022

# This script requires the following files:
# - sticker_textprep.rds
# - sticker_standard_toponyms.rds

# This script produces the following files:
# - sticker_google_tokens.rds
# - sticker_google_entities.rds
# - sticker_coreNLP_annotation.rds
# - sticker_coreNLP_tokens.rds
# - sticker_spacy_tokens.rds
# - sticker_geoparser_entities.rds
# - sticker_germaner_entities.rds
# - sticker_comparison_NER.rds


# Housekeeping ----------------------------------------------------------

rm(list=ls())
set.seed(42)

library(googleAuthR)
library(httr)
library(RCurl)
library(rjson)
library(readr)
library(stringr)
library(dplyr)
library(coreNLP)
library(spacyr)

source("func_authenticate.R")
source("func_POS_google.R")
source("func_NER_google.R")

# This has to be done only once
#spacy_install()
#spacy_download_langmodel("de")
  

# DATA -------------------------------------------------------

text <- readRDS("data/sticker_textprep.rds")
standard_topo <- readRDS("data/sticker_standard_toponyms.rds")


# GOOGLE NLP ----------------------------------------------------------

# Split text in two chunks 
# for some reason, google somehow cannot handle the full text at once
text1 <- substr(text, 1, 421499)
text2 <- substr(text, 421500, nchar(text))

# Authenticate
authentification <- gar_auth_service(json_file= jsonfile, 
                                     scope = "https://www.googleapis.com/auth/cloud-platform")

# Analyze POS
system.time({
  google_tokens1 <- func_POS_google(text1, authentification, APIkey, sentence=FALSE) 
  google_tokens2 <- func_POS_google(text2, authentification, APIkey, sentence=FALSE) 
})
  
google_tokens1$set <- 1
google_tokens2$set <- 2
google_tokens <- merge(google_tokens1, google_tokens2, by=intersect(names(google_tokens1), names(google_tokens2)), all=T)
google_tokens$text.beginOffset <- as.numeric(google_tokens$text.beginOffset)
google_tokens <- google_tokens[order(google_tokens$set, google_tokens$text.beginOffset),]

# correct offset for second text chunk
google_tokens$text.beginOffset <- ifelse(google_tokens$set==2, 
                                         google_tokens$text.beginOffset+max(google_tokens$text.beginOffset[google_tokens$set==1])+2,
                                         google_tokens$text.beginOffset)

# Calculate start and end of tokens
google_tokens$start <- google_tokens$text.beginOffset+1
google_tokens$end <- google_tokens$start + nchar(google_tokens$text.content)-1

saveRDS(google_tokens, "data/sticker_google_tokens.rds")
rm(list=c("google_tokens1", "google_tokens2"))

# Analyze NER
system.time({
  google_entities <- func_NER_google(text1, authentification, APIkey)
  google_entities2 <- func_NER_google(text2, authentification, APIkey)
})

google_entities1$set <- 1
google_entities2$set <- 2
google_entities <- merge(google_entities1, google_entities2, 
                         by=intersect(names(google_entities1), names(google_entities2)), all=T)

google_entities$offset <- as.numeric(google_entities$offset)
google_entities <- google_entities[order(google_entities$set, google_entities$offset),]

# correct offset for second text chunk
google_entities$offset <- ifelse(google_entities$set==2, 
                                 google_entities$offset+max(google_tokens$text.beginOffset[google_tokens$set==1])+2,
                                 google_entities$offset)

google_entities$start <- as.numeric(google_entities$offset)+1
google_entities$end <- google_entities$start+nchar(google_entities$content)-1
google_entities$salience <- as.numeric(google_entities$salience)
google_entities <- google_entities[order(google_entities$start),]

google_entities$id <- 1:nrow(google_entities)

google_entities$entity_orig <- google_entities$entity
google_entities$entity <- tolower(google_entities$entity)

saveRDS(google_entities, "data/sticker_google_entities.rds")
rm(list=c("google_entities1", "google_entities2"))


# STANFORD CORE NLP -------------------------------------------------------

initCoreNLP(stanfordlib, type="german") 

system.time(coreNLP_anno <- annotateString(text))
saveRDS(coreNLP_anno, "data/sticker_coreNLP_annotation.rds")

coreNLP_tokens <- coreNLP_anno$token
coreNLP_tokens$start <- coreNLP_tokens$CharacterOffsetBegin+1
coreNLP_tokens$end <- coreNLP_tokens$CharacterOffsetEnd

# The tokens with Umlaut are returned incorrectly, this is a patch solution to get the correct tokens:
tokens <- c()
for (i in 1:nrow(coreNLP_tokens)) {
  tokens <- c(tokens, substr(text, coreNLP_tokens$start[i], coreNLP_tokens$end[i]))
}
tokens <- trimws(tokens, "both")
tokens <- enc2utf8(tokens)
coreNLP_tokens$token <- tokens

colnames(coreNLP_tokens)[2] <- "token_id"
coreNLP_tokens <- coreNLP_tokens[order(coreNLP_tokens$start),]
coreNLP_tokens$id <- 1:nrow(coreNLP_tokens)

coreNLP_tokens$entity <- tolower(coreNLP_tokens$NER)
coreNLP_tokens$entity <- ifelse(coreNLP_tokens$entity=="o", NA, coreNLP_tokens$entity)
coreNLP_tokens$entity <- ifelse(coreNLP_tokens$entity=="misc", "other", coreNLP_tokens$entity)

saveRDS(coreNLP_tokens, "data/sticker_coreNLP_tokens.rds")
rm(tokens)



# SPACY -------------------------------------------------------------------

spacy_initialize(model="de", refresh_settings = T)

system.time(spacy_tokens <- spacy_parse(text, additional_attributes = c("idx")))
spacy_finalize()

spacy_tokens$start <- spacy_tokens$idx + 1
spacy_tokens$end <- spacy_tokens$start + nchar(spacy_tokens$token)-1
spacy_tokens$entity_orig <- spacy_tokens$entity
spacy_tokens$entity <- ifelse(spacy_tokens$entity=="LOC_B" | spacy_tokens$entity=="LOC_I", "location", 
                              ifelse(spacy_tokens$entity=="MISC_B" | spacy_tokens$entity=="MISC_I", "other", 
                                     ifelse(spacy_tokens$entity=="PER_B" | spacy_tokens$entity=="PER_I", "person", 
                                            ifelse(spacy_tokens$entity=="ORG_B" | spacy_tokens$entity=="ORG_I", "organization", NA))))
spacy_tokens <- spacy_tokens[order(spacy_tokens$start),]
spacy_tokens$id <- 1:nrow(spacy_tokens)

saveRDS(spacy_tokens, "data/sticker_spacy_tokens.rds")



# GEOPARSER ---------------------------------------------------------------

# Geoparser cannot handle chunks larger than 10,000 characters.
# split text into chunks of max. 10,000 (max nchar) after a period
periods <- data.frame(str_locate_all(text, "\\."))$start
splitpos <- c()
split <- 9990
while (split<nchar(text)) {
  
  newsplit <- periods[max(which(split>periods))]
  splitpos <- c(splitpos, newsplit)
  split <- newsplit + 10000
}
diff(splitpos)
rm(split)
rm(newsplit)
splitpos <- c(0, splitpos)

textsplit <- vector("list", length(splitpos))
for (i in 1:length(textsplit)) {
  if (i <= (length(splitpos)-1)) {
    textsplit[[i]] <- substr(text, splitpos[i]+1, (splitpos[i+1]))
  }
  else {
    textsplit[[i]] <- substr(text, splitpos[i]+1, nchar(text))
  }
}


# query geoparser for all text chunks
geoparser <- vector("list", length(textsplit))
t1 <- Sys.time()
for (i in 1:length(textsplit)) {
  request <- POST("https://geoparser.io/api/geoparser",
                  add_headers(
                    "Accept" = "application/json",
                    "Authorization" = paste("apiKey", gpAPI),
                    "Content-Type" = "application/x-www-form-urlencoded; charset=UTF-8"),
                  body = paste0("inputText=", URLencode(textsplit[[i]])))
  
  result_json <- content(request, as = "text")
  geoparser[[i]] <- fromJSON(result_json)$features
}
t2 <- Sys.time()
t2-t1

# Turn output into dataframe:
geoparser_entities <- c()
for (i in 1:length(geoparser)) {
  
  out <- geoparser[[i]]
  reps <- lengths(out$properties$references)/2  # assess how many repetitions of a given location were found
  # Extract text positions as a data.frame
  refs <- do.call("rbind", lapply(1:length(out$properties$references), 
                                  function(x) data.frame(as.matrix(out$properties$references[[x]]))))
  colnames(refs) <- c("start", "end")
  refs$start <- refs$start+1
  
  id <- c() # Add id's to the references for later merging
  for (j in 1:length(reps)) {
    id <- c(id, rep(out$id[j], reps[j]))
  }
  refs$id <- id
  
  # extract coordinates
  coords <- data.frame(do.call("rbind", out$geometry$coordinates)) 
  colnames(coords) <- c("lon", "lat")
  
  df <- data.frame(cbind("country"=out$properties$country, 
                         "name"=out$properties$name, "adm1"=out$properties$admin1, 
                         "type"=out$properties$type, "id"=out$id, 
                         "geom"=out$geometry$type, "confidence"=out$properties$confidence), 
                   stringsAsFactors = F)
  
  df <- cbind(df, coords)
  df$id <- as.numeric(df$id)
  df$confidence <- as.numeric(df$confidence)
  df <- merge(df, refs, by="id", all=T)
  
  df$split <- i
  geoparser_entities <- rbind(geoparser_entities, df)
  
}

# Recalculate start/end because of splitting of text into chunks
for (i in 1:length(splitpos)) {
  geoparser_entities$start[geoparser_entities$split==i] <- geoparser_entities$start[geoparser_entities$split==i]+splitpos[i]
  geoparser_entities$end[geoparser_entities$split==i] <- geoparser_entities$end[geoparser_entities$split==i]+splitpos[i]
}

colnames(geoparser_entities)[1] <- "id_geop"
geoparser_entities$id <- 1:nrow(geoparser_entities)
geoparser_entities$entity <- "location"

# add token name
geoparser_entities$token <- NA
for (i in 1:nrow(geoparser_entities)) {
  geoparser_entities$token[i] <- substr(text, geoparser_entities$start[i], geoparser_entities$end[i])
}

saveRDS(geoparser_entities, "data/sticker_geoparser_entities.rds")

rm(list=c("df", "refs", "id", "coords", "out", "reps", "request", "textsplit", "result_json", 
          "t1", "t2", "splitpos", "geoparser"))


# GERMANER ---------------------------------------------------------------

# use tokenization by spacy as raw input for germaner
germaner <- spacy_tokens[,c("token","pos")]

# replace end of sentence punctuation with blanks (requirement of germaner)
germaner$token[germaner$token=="." & germaner$pos=="PUNCT"] <- ""

# partition the text into smaller chunks for processing through GermaNER (java memory issues)
length(which(germaner$token==""))

splits <- split(which(germaner$token==""), ceiling(seq_along(which(germaner$token==""))/700))
splitpos <- c()
for (i in 1:(length(splits))) {
  splitpos <- c(splitpos, splits[[i]][length(splits[[i]])])
}

start <- 0
for (i in 1:length(splitpos)) {
  write.table(germaner[(start+1):(splitpos[i]),1], file=paste0("data/germaner_", i, ".tsv"), quote = F, sep="\t", col.names = F,row.names = F)
  start <- splitpos[i]
}

rm(splits)

# The tagging is done via command line

# Read in the 10 tagged files and combine to one file
germaner_entities <- c()
for (i in 1:10) {
  germaner_entities <- rbind(germaner_entities, read.delim(paste0("data/germaner_output_", i, ".tsv"), stringsAsFactors = F, header = F , sep=" ", blank.lines.skip = F))
}

germaner_entities <- germaner_entities[,c(1,3)]
colnames(germaner_entities) <- c("token", "entity")
germaner_entities <- cbind(spacy_tokens[order(spacy_tokens$start),c("start", "end")], germaner_entities)
germaner_entities$token <- ifelse(germaner_entities$token=="", ".", germaner_entities$token)
table(germaner_entities$token==spacy_tokens$token)
germaner_entities$entity_orig <- germaner_entities$entity
germaner_entities$entity <- ifelse(germaner_entities$entity=="B-LOC" | germaner_entities$entity=="I-LOC", "location", 
                              ifelse(germaner_entities$entity=="B-OTH" | germaner_entities$entity=="I-OTH", "other", 
                                     ifelse(germaner_entities$entity=="B-PER" | germaner_entities$entity=="I-PER", "person", 
                                            ifelse(germaner_entities$entity=="B-ORG" | germaner_entities$entity=="I-ORG", "organization", NA))))
germaner_entities <- germaner_entities[order(germaner_entities$start),]
germaner_entities$id <- 1:nrow(germaner_entities)

saveRDS(germaner_entities, "data/sticker_germaner_entities.rds")

# COMBINE ----------------------------------------------------------

# Combine all files in one dataset for comparison of performance
# Map all entities onto the standard tokenization pattern

# Spacy
comparison <- func_tokenmap(standard_topo, 
                            spacy_tokens[,c("start", "end", "entity", "id")])

colnames(comparison)[which(colnames(comparison) %in% c("id.x", "entity.x", "id.y", "entity.y"))] <- c("entity", "id", "entity_spacy", "id_spacy")

# Core NLP
comparison <- func_tokenmap(comparison, 
                            coreNLP_tokens[,c("start", "end", "entity", "id")])
colnames(comparison)[which(colnames(comparison) %in% c("id.x", "entity.x", "id.y", "entity.y"))] <- c("entity", "id", "entity_coreNLP", "id_coreNLP")

# geoparser
comparison <- func_tokenmap(comparison, 
                            geoparser_entities[,c("start", "end", "entity", "id")])
colnames(comparison)[which(colnames(comparison) %in% c("id.x", "entity.x", "id.y", "entity.y"))] <- c("entity", "id", "entity_geoparser", "id_geoparser")

# germaner
comparison <- func_tokenmap(comparison, 
                            germaner_entities[,c("start", "end", "entity", "id")])
colnames(comparison)[which(colnames(comparison) %in% c("id.x", "entity.x", "id.y", "entity.y"))] <- c("entity", "id", "entity_germaner", "id_germaner")

# Google
comparison <- func_tokenmap(comparison, 
                            google_entities[,c("start", "end", "entity", "id")])
colnames(comparison)[which(colnames(comparison) %in% c("id.x", "entity.x", "id.y", "entity.y"))] <- c("entity", "id", "entity_google", "id_google")

comparison$entity_coreNLP <- ifelse(comparison$entity_coreNLP=="location" & !is.na(comparison$entity_coreNLP), "location", "other")
comparison$entity_spacy <- ifelse(comparison$entity_spacy=="location" & !is.na(comparison$entity_spacy), "location", "other")
comparison$entity_google <- ifelse(comparison$entity_google=="location" & !is.na(comparison$entity_google), "location", "other")
comparison$entity_geoparser <- ifelse(comparison$entity_geoparser=="location" & !is.na(comparison$entity_geoparser), "location", "other")
comparison$entity_germaner <- ifelse(comparison$entity_germaner=="location" & !is.na(comparison$entity_germaner), "location", "other")


# Locations identified by all algorithms
comparison$alltrue <- ifelse(comparison$entity=="location" &
                                comparison$entity_spacy=="location" & 
                               comparison$entity_google=="location" & 
                               comparison$entity_coreNLP=="location" & 
                               comparison$entity_geoparser=="location" &
                               comparison$entity_germaner=="location", 1, 0)

# Locations identified by none of the algorithms
comparison$nonetrue <- ifelse(comparison$entity=="location" &
                                comparison$entity_spacy!="location" & 
                                comparison$entity_google!="location" & 
                                comparison$entity_coreNLP!="location" & 
                                comparison$entity_geoparser!="location" &
                                comparison$entity_germaner!="location", 1, 0)

# Locations false identified by all algorithms
comparison$allfalse <- ifelse(comparison$entity!="location" &
                                comparison$entity_spacy=="location" & 
                                comparison$entity_google=="location" & 
                                comparison$entity_coreNLP=="location" & 
                                comparison$entity_geoparser=="location" &
                                comparison$entity_germaner=="location", 1, 0)



saveRDS(comparison, "data/sticker_comparison_NER.rds")




