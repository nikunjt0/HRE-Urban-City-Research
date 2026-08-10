# Title: Mapping the plague through natural language processing
# Author: Fabienne Krauer, University of Oslo
# DOI: 10.5281/zenodo.6587267
# Last updated: 22.09.2020

#This function extracts GIS information from Google API with the following tags:
#low level: "locality", "political", "neighborhood", "postal town","adm level 1 to 5", "sublocality", "colloquial area"
#high level: all of the above plus "establishment", "natural feature"

#This function extracts full matches (partial=FALSE) or partial matches (partial=TRUE)

# This function extracts the following information: 
#NAME, STATUS, LAT, LON, ADM1-3 and COUNTRY


library(httr)
library(RCurl)
library(rjson)

geocode.goo <- function(address, country=NULL, language=NULL, level="admin", partial, APIkey) {   

    # Prepare dataframe to hold results
    answer <- data.frame(lat=NA, lon=NA, name=NA, adm3=NA, adm3short=NA, adm2=NA, adm2short=NA, 
                       adm1=NA, adm1short=NA, country=NA, countryshort=NA, type=NA, partial=NA, placeid=NA, 
                       NElat=NA, NElon=NA, SWlat=NA, SWlon=NA, status=NA)
    
    # Prepare input for querying
    location <- chartr(" ", "+", enc2utf8(address))
    
    if (!is.null(country)) {
      country <- paste("&components=country:", country, sep="")
    } else {
      country <- c()
    }
    
    if (!is.null(language)) {
      language <- paste("&language=", language, sep="")
    } else {
      language <- c()
    }
    
    level <- level
    partial <- partial
    location <- paste0(location, language, country)
    url_string <- URLencode(paste("https://maps.googleapis.com/maps/api/geocode/json?address=", location, "&key=", APIkey, sep = ""))
    
    # Query API
    message(paste("Querying", location, "level =", level, "partial =", partial, sep = " "), appendLF = TRUE)
    connect <- url(url_string)
    query <- try(readLines(con=connect, encoding="UTF-8", warn = FALSE), silent = TRUE)
    close(connect)
  
    # Get output as a list
    reply <- fromJSON(paste(query, collapse = ""))
    
    # Extract STATUS from response
    answer$status <- reply[[2]]
    
    # Exit function if status is not OK
    if (reply[[2]] != "OK") {
      message(paste("STATUS:", answer$status, sep = " "), appendLF = TRUE)
      return(answer)
    }
    
    #Assess number of returned results
    resultsize <- length(reply[[1]])
    yy <- 0

    # Loop through returned results and the first entry which yields the desired level of spatial precision
    for (y in 1:resultsize) {
      if (yy>0) {
        break
      }   
      
      if (level=="country" & reply[[1]][[y]]$types[[1]]=="country") {
        yy <- y
        break       
      }
    
      if (level=="admin" & (reply$results[[y]]$types[[1]]=="locality" |
                            reply$results[[y]]$types[[1]]=="political" |
                            reply$results[[y]]$types[[1]]=="neighborhood" |
                            reply$results[[y]]$types[[1]]=="postal_town" |
                            reply$results[[y]]$types[[1]]=="administrative_area_level_4" |
                            reply$results[[y]]$types[[1]]=="administrative_area_level_3" |
                            reply$results[[y]]$types[[1]]=="administrative_area_level_2" |
                            reply$results[[y]]$types[[1]]=="administrative_area_level_1" |
                            reply$results[[y]]$types[[1]]=="sublocality" |
                            reply$results[[y]]$types[[1]]=="colloquial_area")) {
        yy <- y
        break
      }
        
        if (level=="feature" & (reply$results[[y]]$types[[1]]=="establishment" |
                            reply$results[[y]]$types[[1]]=="natural_feature")) {
          yy <- y
          break       
      }
    }  
      
    # Exit function if none of returned result is a locality
    if (yy==0) {
      answer$status <- "ZERO_RESULTS"
      message(paste("STATUS:", answer$status, sep = " "), appendLF = TRUE)
      return(answer)
    }

    
    #Exit function if returned result is partial, but required is full match
    if (!is.null(reply$results[[yy]]$partial_match[[1]]) & partial==FALSE) {
      answer$status <- "ZERO_RESULTS"
      message(paste("STATUS:", answer$status, sep = " "), appendLF = TRUE)
      return(answer) 
    }
    
    message(paste("Status:", answer$status, sep = " "), appendLF = TRUE)
    
          
    # Extract desired information from first reponse with locality data
    answer$lat <- unlist(reply$results[[yy]]$geometry$location["lat"]) #LAT
    answer$lon <- unlist(reply$results[[yy]]$geometry$location["lng"]) #LON
    if (length(reply$results[[yy]]$address_components)==0) {
      
      answer$name <- reply$results[[yy]]$formatted_address #NAME
    } 
    else {
      answer$name <- reply$results[[yy]]$address_components[[1]]$long_name #NAME
    }
    answer$type <- reply$results[[yy]]$types[[1]] #TYPE
    answer$placeid <- reply$results[[yy]]$place_id # Place ID
    answer$NElat <- unlist(reply$results[[yy]]$geometry$viewport$northeast["lat"]) # viewport coordinates
    answer$NElon <- unlist(reply$results[[yy]]$geometry$viewport$northeast["lng"]) # viewport coordinates
    answer$SWlat <- unlist(reply$results[[yy]]$geometry$viewport$southwest["lat"]) # viewport coordinates
    answer$SWlon <- unlist(reply$results[[yy]]$geometry$viewport$southwest["lng"]) # viewport coordinates

    listsize <- length(reply$results[[yy]]$address_components) #assess number of address component with locality data
    
    if (length(reply$results[[yy]]$address_components)>0) {
      
      #Loop through address component elements to extract ADM information  
      for (xx in 1:listsize) {
        
        #ADM3
        if (reply$results[[yy]]$address_components[[xx]][[3]][[1]]=="administrative_area_level_3") {
          answer$adm3 <- reply$results[[yy]]$address_components[[xx]][[1]]
          answer$adm3short <- reply$results[[yy]]$address_components[[xx]][[2]]
        }
        #ADM2
        if (reply$results[[yy]]$address_components[[xx]][[3]][[1]]=="administrative_area_level_2") {
          answer$adm2 <- reply$results[[yy]]$address_components[[xx]][[1]]
          answer$adm2short <- reply$results[[yy]]$address_components[[xx]][[2]]
        }
        #ADM1
        if (reply$results[[yy]]$address_components[[xx]][[3]][[1]]=="administrative_area_level_1") {
          answer$adm1 <- reply$results[[yy]]$address_components[[xx]][[1]]
          answer$adm1short <- reply$results[[yy]]$address_components[[xx]][[2]]
        }
        #country and country code
        if (reply$results[[yy]]$address_components[[xx]][[3]][[1]]=="country") {
          answer$country <- reply$results[[yy]]$address_components[[xx]][[1]]
          answer$countryshort <- reply$results[[yy]]$address_components[[xx]][[2]]
        }
        
      }
      
    }
    
    # Tag if match is PARTIAL
    if (!is.null(reply$results[[yy]]$partial_match[[1]])) {
      answer$partial <- reply$results[[1]]$partial_match
    }
  
  return(answer)
    
}