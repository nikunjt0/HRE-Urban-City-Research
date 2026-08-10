func_tableS4 <- function(standard_topo, 
                         google_entities, 
                         google_tokens,
                         spacy_tokens, 
                         coreNLP_tokens,
                         germaner_entities,
                         geoparser_entities,
                         comparison_NER) {
  
  # prep table
  tableS4 <- data.frame("item"=rep(NA, 2), "standard"=rep(NA, 2), "GoogleNLP"=rep(NA, 2), 
                        "CoreNLP"=rep(NA, 2), "spaCy"=rep(NA, 2), "germaNER"=rep(NA, 2), "Geoparser"=rep(NA, 2))
  tableS4$item <- c("n_tokens", "ent_total")
  
  # N of tokens and entities
  tableS4[1,2:7]  <- c(nrow(standard_topo), nrow(google_tokens), nrow(coreNLP_tokens), 
                       nrow(spacy_tokens), nrow(spacy_tokens), NA)
  tableS4[2,2:7]  <- c(nrow(standard_topo[standard_topo$entity=="location",]), 
                       nrow(google_entities), 
                       nrow(coreNLP_tokens[!is.na(coreNLP_tokens$entity),]),
                       nrow(spacy_tokens[!is.na(spacy_tokens$entity),]),  
                       nrow(germaner_entities[!is.na(germaner_entities$entity),]),
                       nrow(geoparser_entities))
  
  # N of entities by type
  foo1 <- data.frame(algo="1_standard", table(standard_topo$entity))
  foo2 <- data.frame(algo="2_google", table(google_entities$entity))
  foo3 <- data.frame(algo="3_coreNLP", table(coreNLP_tokens$entity))
  foo4 <- data.frame(algo="4_spacy", table(spacy_tokens$entity))
  foo5 <- data.frame(algo="5_germaner", table(germaner_entities$entity))
  foo <- merge(foo1, foo2, by=intersect(names(foo1), names(foo2)), all=T)
  foo <- merge(foo, foo3, by=intersect(names(foo), names(foo3)), all=T)
  foo <- merge(foo, foo4, by=intersect(names(foo), names(foo4)), all=T)
  foo <- merge(foo, foo5, by=intersect(names(foo), names(foo5)), all=T)
  foo <- pivot_wider(foo, names_from = "algo", values_from = "Freq")
  foo$geoparser <- c(nrow(geoparser_entities), rep(NA,6))
  colnames(foo) <- colnames(tableS4)
  tableS4 <- rbind(tableS4, foo)
  rm(foo)
  
  # N of entities after mapping
  foo1 <- data.frame(algo="1_standard", table(comparison_NER$entity))
  foo2 <- data.frame(algo="2_google", table(comparison_NER$entity_google))
  foo3 <- data.frame(algo="3_coreNLP", table(comparison_NER$entity_coreNLP))
  foo4 <- data.frame(algo="4_spacy", table(comparison_NER$entity_spacy))
  foo5 <- data.frame(algo="5_germaner", table(comparison_NER$entity_germaner))
  foo6 <- data.frame(algo="6_geoparser", table(comparison_NER$entity_geoparser))
  foo <- merge(foo1, foo2, by=intersect(names(foo1), names(foo2)), all=T)
  foo <- merge(foo, foo3, by=intersect(names(foo), names(foo3)), all=T)
  foo <- merge(foo, foo4, by=intersect(names(foo), names(foo4)), all=T)
  foo <- merge(foo, foo5, by=intersect(names(foo), names(foo5)), all=T)
  foo <- merge(foo, foo6, by=intersect(names(foo), names(foo6)), all=T)
  foo <- pivot_wider(foo, names_from = "algo", values_from = "Freq")
  colnames(foo) <- colnames(tableS4)
  tableS4 <- rbind(tableS4, foo)
  rm(foo)
  
  # calculate percentages
  pct1 <- data.frame("item"=tableS4[c(3:9),1])
  for (i in 2:7) {
    
    colname <- colnames(tableS4)[i]
    moo <- data.frame(tableS4[c(3:9),i])
    colnames(moo) <- colname
    moo[is.na(moo),1] <- 0
    foo <- data.frame(prop.table(moo[,1]))
    colnames(foo) <- colname
    pct1 <- cbind(pct1, round(foo*100,1))
    
  }
  rm(moo)
  rm(foo)
  
  # Entities after mapping
  pct2 <- data.frame("Var1"=NA, "Freq"=NA, "algo"=NA)
  poo <- comparison_NER[,c("entity", "entity_google", "entity_coreNLP", "entity_spacy", "entity_germaner", "entity_geoparser")]
  
  for (i in 1:6) {
    
    colname <- colnames(tableS4)[i+1]
    moo <- data.frame(prop.table(table(poo[,i])))
    moo$algo <- colname
    pct2 <- rbind(pct2, moo)
    
  }
  pct2 <- pct2[!is.na(pct2$algo),]
  pct2$Freq <- round(pct2$Freq*100,1)
  pct2 <- pivot_wider(pct2, names_from = "algo", values_from = "Freq")
  colnames(pct2)[1] <- "item"
  
  pct <- rbind(pct1, pct2)
  
  # paste numbers and percentages together
  for (i in 2:7) {
    for (j in 1:9) {
      insert <- paste0(tableS4[j+2, i], " (", pct[j,i],")")
      if (insert=="NA (0)") insert = ""
      tableS4[j+2,i] <- insert
    }
  }
  
  return(tableS4)
}
