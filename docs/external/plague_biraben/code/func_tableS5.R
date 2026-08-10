func_tableS5 <- function(sticker, biraben) {
  
  tableS5 <- data.frame("item"="loc_total", 
                        "Sticker"=nrow(sticker), 
                        "Biraben"=nrow(biraben))
  status <- cbind(data.frame(table(sticker$status)),data.frame(table(biraben$status))[,2])
  colnames(status) <- colnames(tableS5)
  
  tableS5 <- rbind(tableS5, status)
  tableS5 <- rbind(tableS5, 
                   cbind("item"="loc_unique", 
                         "Sticker"=length(unique(sticker$locid)), 
                         "Biraben"=length(unique(biraben$locid))))
  
  # spatial coverage
  tableS5 <- rbind(tableS5, 
                   cbind("item"="latitude",
                         "Sticker"=paste(round(min(sticker$lat, na.rm=T),0), round(max(sticker$lat, na.rm=T),0), sep= " to "),
                         "Biraben"=paste(round(min(biraben$lat, na.rm=T),0), round(max(biraben$lat, na.rm=T),0), sep= " to ")))
  
  tableS5 <- rbind(tableS5, 
                   cbind("item"="longitude",
                         "Sticker"=paste(round(min(sticker$lon, na.rm=T),0), round(max(sticker$lon, na.rm=T),0), sep= " to "),
                         "Biraben"=paste(round(min(biraben$lon, na.rm=T),0), round(max(biraben$lon, na.rm=T),0), sep= " to ")))
  
  # countries
  tableS5 <- rbind(tableS5, 
                   cbind("item"="countries",
                         "Sticker"=length(unique(sticker$country_ISO2[!is.na(sticker$country_ISO2)])),
                         "Biraben"=length(unique(biraben$country_ISO2[!is.na(sticker$country_ISO2)]))))
  
  # Types
  foo1 <- data.frame(sort(round(prop.table(table(sticker$type_detail))*100, 1)))
  colnames(foo1) <- c("item", "Sticker")
  foo2 <- data.frame(sort(round(prop.table(table(biraben$type_detail))*100, 1)))
  colnames(foo2) <- c("item", "Biraben")
  
  foo <- merge(foo1, foo2, by="item", all=T)
  foo$Sticker <- ifelse(is.na(foo$Sticker), 0.0, foo$Sticker)
  foo$Biraben <- ifelse(is.na(foo$Biraben), 0.0, foo$Biraben)
  
  tableS5 <- rbind(tableS5, foo)
  
  # temporal coverage
  tableS5 <- rbind(tableS5, 
                   cbind("item"="years", 
                         "Sticker"=paste(min(summary(sticker$year)), max(summary(sticker$year)),sep="-"), 
                         "Biraben"=paste(min(summary(biraben$year)), max(summary(biraben$year)),sep="-")))
  
  
  foo1 <- data.frame(round(prop.table(table(sticker$century))*100,1))
  colnames(foo1) <- c("item", "Sticker")
  
  tableS5 <- rbind(tableS5,
                   cbind(foo1, "Biraben" = data.frame(round(prop.table(table(biraben$century))*100,1))[,2]))
  
  
  round(prop.table(table(biraben$century))*100,1)
  
  return(tableS5)
  
  
}
