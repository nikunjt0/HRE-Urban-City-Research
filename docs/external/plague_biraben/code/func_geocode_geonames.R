# Title: Mapping the plague through natural language processing
# Author: Fabienne Krauer, University of Oslo
# DOI: 10.5281/zenodo.6587267
# Last updated: 22.09.2020

geocode.gn <- function(place, country=NULL, continent=NULL, fclass=NULL, 
                        fcode=NULL, searchtype, max=NULL, user) {   
  
  Sys.sleep(5) # Throttle function to stay within maximum of 1000 credits / hour
  
    if (!searchtype %in% c("all", "placefuzzy", "placeexact")) {
    stop("Search type must be either all, placefuzzy or placeexact")
  } else {
    if (searchtype=="all") {
      param1 <- URLencode(paste0("q=",  place))
    } else if  (searchtype=="placefuzzy"){
      param1 <- URLencode(paste0("name=", place))
    } else {
      param1 <- URLencode(paste0("name_equals=", place))
    }
  }
  
  # Number of rows
  if (!is.null(max)) {
    if (max<1 | max>1000) {
      stop("Max must be between 1 and 1000")
    } else {
      param2 <- paste0("&maxRows=", max)
    }
  } else {
    param2 <- c()
  }
  
  # Country
  if (!is.null(country)) {
    if (unique(nchar(country))!=2 | !all(grepl("^[[:upper:]]+$", country))) {
      stop("Country codes must two letter country codes ISO-3166")
    } else {
      param3 <- paste0("&country=", country, collapse="")
    }
  } else {
    param3 <- c()
  }
  
  # Continent
  if (!is.null(continent)) {
    if (!all(continent %in%  c("AF","AS","EU","NA","OC","SA","AN"))) {
      stop("continent must be one or more of {AF,AS,EU,NA,OC,SA,AN}")
    } else {
      param4 <- paste0("&continentCode=", continent, collapse="")
    }
  } else {
    param4 <- c()
  }
  

  # feature class
  if (!is.null(fclass)) {
    if (!all(fclass %in% c("A","H","L","P","R","S","T","U","V"))) {
      stop("Feature class must be one or more of {A,H,L,P,R,S,T,U,V}")
    } else {
      param5 <- paste0("&featureClass=", fclass, collapse="")
    }
  } else {
    param5 <- c()
  }  
  
  # feature code
  if (!is.null(fcode)) {
    if (!all(nchar(fcode)<=5 & nchar(fcode)>=2)) {
      stop("Feature code must be a character string of two to five upper case letters or numbers")
    } else {
      param6 <- paste0("&featureCode=", fcode, collapse="")
    }
  } else {
    param6 <- c()
  }  
  
  # Define URL string to query
  urlstring <- URLencode(paste0("http://api.geonames.org/searchJSON?", 
                                param1, param2, param3, param4, param5, param6, "&username=", user)) 
  
  # Query API
  message(paste("Querying", place, sep = " "), appendLF = TRUE)
  connect <- url(urlstring)
  query <- try(readLines(con=connect, encoding="UTF-8", warn = FALSE), silent = TRUE)
  close(connect)
  
  reply <- fromJSON(paste(query, collapse = "")) # convert to list

  # Exit if there is an error message
  if (names(reply)[1]=="status") {
      stop(paste0(reply$status$message))
  }
  
  else {
    # check if no result is found
    if (reply$totalResultsCount==0) {
      reply <- data.frame("status" = "ZERO_RESULTS")
      message("STATUS: ZERO_RESULTS", appendLF = TRUE)
      return(reply)
    } 
    else {
      # Convert to dataframe
      reply <- lapply(reply[[2]], function(x) { 
        moo <- unlist(x)
        data.frame(t(moo), stringsAsFactors = F)
      })
      reply <- plyr::ldply(reply, rbind)
      
      # sort according to order of fclass
      if (!is.null(fclass)) {
        reply$fcl <- factor(reply$fcl, levels=fclass) 
        reply <- reply[order(reply$fcl),]
        reply$fcl <- as.character(reply$fcl)
      }
      reply$status <- "OK"
      message("STATUS: OK", appendLF = TRUE)
      return(reply)
    }
  }
}