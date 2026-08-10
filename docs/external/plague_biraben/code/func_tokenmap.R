func_tokenmap <- function(standard, comparator) {
  
  # exact matches (N tokens standard == N tokens comparator)
  fullmerge <- merge(standard, comparator,
                      by=c("start", "end"), all.x=TRUE)
  fullmerge$id.y <- as.character(fullmerge$id.y)
  
  # match when N tokens comparator > N tokens standard
  A <- fullmerge[is.na(fullmerge$id.y),]
  A <- A[order(A$start),]
  
  for (i in 1:nrow(A)) {
    
    subset <- comparator[comparator$start>=A$start[i] & comparator$end<=A$end[i],]
    
    if (nrow(subset)>0) {
      subset <- subset %>% summarise(id=paste(id, collapse=","), entity=sort(entity)[1])
      fullmerge[fullmerge$id.x == A$id.x[i],c("entity.y")] <- subset$entity
      fullmerge[fullmerge$id.x == A$id.x[i],c("id.y")] <- subset$id
    }
    
  }
  
  # match when N tokens comparator < N tokens standard
  B <- comparator[!(comparator$id %in% as.numeric(unlist(strsplit(fullmerge$id.y, ",")))),]
  B <- B[order(B$start),]
  
  for (i in 1:nrow(B)) {
    fullmerge[fullmerge$start>=B$start[i] & fullmerge$end<=B$end[i],c("entity.y")] <- B$entity[i]
    fullmerge[fullmerge$start>=B$start[i] & fullmerge$end<=B$end[i],c("id.y")] <- B$id[i]
    
  }
  
  return(fullmerge)
  
}
