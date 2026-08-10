func_NER_google <- function(text, authentification, googleAPI) {
  
  baseurl <- "https://language.googleapis.com/v1beta1/documents:analyzeEntities?key="
  resultJSON <- getURL(paste0(baseurl, googleAPI),
                                    .opts = curlOptions(postfields = toJSON(list(document=list(type ="PLAIN_TEXT",
                                                                                               language="DE",
                                                                                               content = text), 
                                                                                 encodingType = "UTF16")),
                                                        httpheader = c("Content-Type" = "application/json",
                                                                       Authorization = authentification)))
  
  entities <- fromJSON(resultJSON)[[1]]

  lengths <- c()
  for (j in 1:length(entities)) {
    lengths <- c(lengths, length(entities[[j]]$mentions))
  }
  
  google_entities <- c()
  for (i in 1:length(entities)) {
    for (k in 1:lengths[i]) {
      dummy <- cbind(entities[[i]]$name,
                     entities[[i]]$mentions[[k]]$text$content,
                     entities[[i]]$entity,
                     entities[[i]]$salience,
                     entities[[i]]$mentions[[k]]$text$beginOffset)
      google_entities <- rbind(google_entities, dummy)
    }
  }
  google_entities <- data.frame(google_entities, stringsAsFactors = F)
  colnames(google_entities) <- c("name", "content", "entity", "salience", "offset")

  return(google_entities)
}


