# Title: Mapping the plague through natural language processing
# Author: Fabienne Krauer, University of Oslo
# DOI: 10.5281/zenodo.6587267
# Last updated: 22.09.2020

geocode.ag <- function(location, max, token, language=NULL, storage) {   
  
  param1 <- URLencode(paste0("&SingleLine=", location))
  param2 <- URLencode("&category=Populated Place,Postal,Land Features,Water Features")
  param3 <- paste0("&maxLocations=", max)
  param4 <- URLencode(paste0("&token=", token))
  param5 <- "&outFields=location,Match_addr,LongLabel,ShortLabel,Addr_type,Type,PlaceName,Subregion,Region,Territory,Country,LangCode,Y,X,Ymin,Xmin,Ymax,Xmax"

  if (!is.null(language)) {
    param6 <- paste0("&langCode=", language)
  } 
  else {
    param6 <- c()
  }
  
  if (storage==TRUE) {
    param7 <- "&forStorage=true"
  }
  else {
    param7 <- "&forStorage=false"
  }
  
  # Define URL string to query
  urlstring <- URLencode(paste0("http://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates?", 
                                "&f=json", param1, param2, param3, param4, param5, param6, param7)) 
  
  print(urlstring)
  # Query API
  message(paste("Querying", location, sep = " "), appendLF = TRUE)
  connect <- url(urlstring)
  query <- try(readLines(con=connect, encoding="UTF-8", warn = T), silent = F)
  close(connect)
  
  reply <- fromJSON(paste(query, collapse = "")) # convert to list
  
  if (length(reply$candidates)==0) {
    reply <- data.frame("status" = "ZERO_RESULTS")
    message("STATUS: ZERO_RESULTS", appendLF = TRUE)
    return(reply)
  } 
   
  else {
    reply <- data.frame(reply$candidates[[1]]$attributes)
    reply[] <- lapply(reply, function(x) if(is.factor(x)) as.character(x) else x)
    reply[] <- lapply(reply, function(x) if(x=="") NA else x)
    reply$status <- "OK"
    reply <- reply[,c("status", "Match_addr","LongLabel","ShortLabel","Addr_type","Type","PlaceName",
                      "Subregion","Region","Territory","Country","LangCode","Y","X","Ymin","Xmin","Ymax","Xmax")]
    message("STATUS: OK", appendLF = TRUE)
    return(reply)
  }

  
}