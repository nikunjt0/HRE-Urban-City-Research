# Title: Mapping the plague through natural language processing
# Author: Fabienne Krauer, University of Oslo
# Last updated: 16.05.2022

# This script requires the following files:
# - sticker_OCR.txt
# - sticker_standard_entities.rds
# - sticker_goldstandard_annotated_1.tsv
# - sticker_goldstandard_annotated_2.tsv
# - sticker_goldstandard_annotated_consensus.tsv

# This script produces the following files:
# - sticker_textprep.rds
# - sticker_textprep.txt
# - sticker_standard_toponyms.rds
# - sticker_standard_toponyms.csv



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


# PREPROCESSING ----------------------------------------------------------

# Read raw data
orig <- read_file("data/sticker_OCR.txt") 
nchar(orig)

# Remove author names in parenthesis
authors <- cbind(data.frame(str_locate_all(orig, "\\([^\\(\\)]+\\)")),
                 data.frame(str_extract_all(orig, "\\([^\\(\\)]+\\)"), stringsAsFactors = F))
colnames(authors)[3] <- "authors"

# Preprocess text
text <- gsub(" \\[\\.\\.\\.\\] ", " ", orig) # Remove place holders for tables
text <- gsub("\\([^\\(\\)]+\\)", "", text) #Remove words in brackets (author names)
text <- gsub("\\. \\.", "\\.", text) # Remove double periods with ws
text <- gsub("\\.\\.", "\\.", text) # Remove double periods without ws
text <- gsub(" +", " ", text) # Remove excess ws
text <- gsub("\\s(?=(\\.|,|;|:|!|\\?))", "", text, perl=T) # Remove ws before punctuation
text <- gsub("\"", "", text) # Remove quotation marks within text
nchar(text)

saveRDS(text, "data/sticker_textprep.rds")
write.table(text, file="data/sticker_textprep.txt", 
            sep = "\t", na="", col.names=F, fileEncoding="UTF-8", row.names = F, quote = F)


# ANNOTATED RAW DATASET --------------------------------------

# Read results from both annotators and combine in consensus file
anno1 <- read.delim("data/sticker_goldstandard_annotated_1.tsv", header=FALSE, 
                    comment.char="#", stringsAsFactors=FALSE, encoding="UTF-8")

anno2 <- read.delim("data/sticker_goldstandard_annotated_2.tsv", header=FALSE, 
                    comment.char="#", stringsAsFactors=FALSE, encoding="UTF-8")

colnames(anno1)[3:4] <- colnames(anno2)[3:4] <- c("token", "entity")

agreement <- data.frame(cbind(anno1$V1, anno1$token, anno1$entity, anno2$entity), stringsAsFactors = F)
agreement$X3 <- ifelse(agreement$X3=="_", 0, 1)
agreement$X4 <- ifelse(agreement$X4=="_", 0, 1)
agree(agreement[,3:4])
kappa2(agreement[,3:4])

standard <- read.delim("data/sticker_goldstandard_annotated_consensus.tsv", header=FALSE, 
                      comment.char="#", stringsAsFactors=FALSE, encoding="UTF-8")
standard <- cbind(standard[,c(1:4)],  data.frame(str_split_fixed(standard$V1, "-", 2), stringsAsFactors=F))
standard$X1 <- as.numeric(standard$X1)
standard$X2 <- as.numeric(standard$X2)
colnames(standard)[5:6] <- c("sentence", "word")
standard <- cbind(standard,  data.frame(str_split_fixed(standard$V2, "-", 2), stringsAsFactors=F))
standard$X1 <- as.numeric(standard$X1)
standard$X2 <- as.numeric(standard$X2)
colnames(standard)[7:8] <- c("start", "end")
standard$start <- standard$start+1
standard$id <- 1:nrow(standard)
colnames(standard)[3:4] <- c("token", "entity")
standard$entity <- ifelse(standard$entity=="_", "other", standard$entity)
standard <- standard %>% dplyr::group_by(entity) %>%  dplyr::mutate(multigroup=ifelse(length(id)>1 & entity!="other" & entity!="LOC",1,0))
sub <- standard %>% dplyr::filter(multigroup==1) %>%  dplyr::group_by(entity) %>% dplyr::mutate(group=group_indices())
standard <- merge(standard, sub[,c("id", "group")], by="id", all=T)
standard$entity <- ifelse(standard$entity!="other", "location", standard$entity)
standard <- standard[,c("id", "token", "start", "end", "entity", "multigroup", "group", "sentence", "word")]

rm(sub)

# Merge toponyms that were split during annotation back together
moo <- standard %>% dplyr::filter(multigroup==1) %>% dplyr::group_by(group) %>% 
  dplyr::summarise(start=start[1], end=end[n()], token = paste0(token, collapse=" "))
moo$token <- gsub("\\s\\.", "\\.", moo$token, perl=T)
moo$token <- gsub("\\s\\-", "\\-", moo$token, perl=T)
moo$token <- gsub("\\s\\/\\s", "\\/", moo$token, perl=T)
standard <- standard[standard$multigroup==0, c("token", "entity", "start", "end")]
standard <- merge(standard, moo[,c(2:4)], by=intersect(names(standard), names(moo)), all=T)
standard <- standard[order(standard$start),]
standard$entity <- ifelse(is.na(standard$entity),"location", standard$entity)

# Add original start and end characters (before removing authors in parenthesis)
dummy <- orig
standard$start_orig <- NA
standard$end_orig <- NA

escapes <- c("[", "]", "(", ")", "{", "}", "*", "+", "?", "|", "^", "$", ".")

pb <- txtProgressBar(min = 0, max = nrow(standard), style = 3)
for (i in 1:nrow(standard)) {
  
  token <- standard$token[i]
  if (token %in% escapes) {
      token <- paste0("\\", token) # some characters need to be escaped for the regex
  } 
  
  moo <- data.frame(str_locate(dummy, token))
  standard$start_orig[i] <- moo$start
  standard$end_orig[i] <- moo$end
  dummy <- substr(dummy, moo$end, nchar(dummy))
  setTxtProgressBar(pb, i)
}

rm(list=c("dummy", "moo"))

pb <- txtProgressBar(min = 0, max = nrow(standard), style = 3)
for (i in 2:nrow(standard)) {
  standard$start_orig[i] <- standard$end_orig[i-1] + standard$start_orig[i] - 1
  standard$end_orig[i] <- standard$end_orig[i-1] + standard$end_orig[i] - 1
  setTxtProgressBar(pb, i)
  
}

standard <- standard[order(standard$start),]
standard$id <- 1:nrow(standard)

saveRDS(standard, "data/sticker_standard_toponyms.rds")

write_excel_csv(standard, 
                path="data/sticker_standard_toponyms.csv",
                na="",
                col_names = T,
                append=F)
