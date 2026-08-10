# euclidean distance function between two lat/lon coordiates (in km)
calcdist <- function(lon1, lat1, lon2, lat2) {
  
  dlon <- (lon2*pi/180 - lon1*pi/180)
  dlat <- (lat2*pi/180 - lat1*pi/180)
  a = sin(dlat/2)^2 + cos(lat1*pi/180) * cos(lat2*pi/180) * sin(dlon/2)^2
  c = 2 * atan2( sqrt(a), sqrt(1-a) )
  d = 6371 * c
  
  return(d)
}