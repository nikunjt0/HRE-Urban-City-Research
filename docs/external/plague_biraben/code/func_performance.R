# Function to calculate Sensitivity, specifitiy, PPV, Accuracy, NPV and F1 score
performance <- function(standard, comparator, comparator_name) {
  
  tp <- sum(ifelse(standard=="location" & comparator=="location", 1, 0))
  fp <- sum(ifelse(standard=="other" & comparator=="location", 1, 0))
  tn <- sum(ifelse(standard=="other" & comparator=="other", 1, 0))
  fn <- sum(ifelse(standard=="location" & comparator=="other", 1, 0))
  total <- tp + tn + fp + fn
  
  accuracy <- (tp + tn) / total
  sensitivity <- tp / (tp + fn)
  specificity <- tn / (tn + fp)
  PPV <- tp / (tp + fp)
  NPV <- tn / (tn + fn)
  f1 <- 2*((PPV*sensitivity)/(PPV + sensitivity))
  expacc <- ((((tp+fn)*(tp+fp))/total)+(((tn+fn)*(tn+fp))/total)) / total
  kappa <- (accuracy - expacc) / (1 - expacc) 
  
  df <- rbind(tp, fp, tn, fn, accuracy, sensitivity, specificity, PPV, NPV, f1, kappa)
  rownames(df) <- c("TP", "FP", "TN", "FN", "Accuracy", "Sensitivity", "Specificity", "PPV", "NPV", "F1", "Cohen's Kappa")
  colnames(df) <- comparator_name
  return(df)
}
