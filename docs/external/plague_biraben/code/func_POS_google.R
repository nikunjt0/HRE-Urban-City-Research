func_POS_google <- function(text, authentification, googleAPI, sentence=FALSE) {
  
  baseurl <- "https://language.googleapis.com/v1beta1/documents:analyzeSyntax?key="
  resultJSON <- getURL(paste0(baseurl, googleAPI),
                                    .opts = curlOptions(postfields = toJSON(list(document=list(type ="PLAIN_TEXT",
                                                                                               language="DE",
                                                                                               content = text), 
                                                                                 encodingType = "UTF16")),
                                                        httpheader = c("Content-Type" = "application/json",
                                                                       Authorization = authentification)))
  # Return either full sentences or tokens
  if (sentence==TRUE) {
    out <- fromJSON(resultJSON)[[1]]
  } else {
    out <- fromJSON(resultJSON)[[2]]
    out <- do.call("rbind", lapply(out, function(x) data.frame(t(unlist(x)), stringsAsFactors = F)))
  }
   
  return(out)
}
