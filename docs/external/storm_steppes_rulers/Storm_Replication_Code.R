#Clear environment
rm(list = ls())

library(readxl)
library(udpipe)
library(tidyverse)
library(hrbrthemes)
library(viridis)
library(lmtest)
library(sandwich)
library(multiwayvcov)
library(stats)
library(strucchange)
library(survival)
library(lfe)
library(estimatr)
library(fixest)
library(tibble)
#diagram
library(DiagrammeR)
library(DiagrammeRsvg)
library(rsvg)
#output
library(modelsummary)

sessionInfo()
set.seed(42)

############################################
### Load Dynasty, Polity, and Ruler Data ###
############################################

## Download Dynasties Data ##
dynasties <- read.csv('Storm_from_the_Steppes_Eurasian_Dynasties_1000_1799.csv')

#inner_asia dist core ('000 km)
dynasties$inner_asia_core_dist_1000km <- dynasties$inner_asia_core_dist/1000

#state history (log)
dynasties$state_hist_log <- log(dynasties$state_history + 1)

#start century, half, quarter
dynasties$start_century <- floor(dynasties$dyn_start / 100) * 100

#end century, half, quarter
dynasties$end_century <- floor(dynasties$dyn_end / 100) * 100

#Generate Dynasty-polity ID
dynasties$dynpol_id <- unique_identifier(dynasties, fields = c("dynasty_id", "truhart_id"))

#FS Ever Dummy
dynasties$fs_ever <- ifelse(!is.na(dynasties$fs_start), 1, 0)

## Download Polity Data ##
polities <- read.csv('Storm_from_the_Steppes_Eurasian_Polity_Century_1000_1800.csv')

#Inner Asia border dist (1000km)
polities$inner_asia_border_dist_1000km <- polities$inner_asia_border_dist/1000

#Peninsula/Island Dummy
polities$Peninsula_island_dummy <- ifelse(polities$landform == "Peninsula" | polities$landform == "Island", 1, 0)

# Download ruler data
rulers <- read.csv('Storm_from_the_Steppes_Eurasian_Rulers_1000_1799.csv')

#start century, half, quarter
rulers$ruler_start_century <- floor(rulers$start_year / 100) * 100
rulers$ruler_start_half <- floor(rulers$start_year / 50) * 50
rulers$ruler_start_quarter <- floor(rulers$start_year / 25) * 25

#end century, half, quarter
rulers$ruler_end_century <- floor(rulers$end_year / 100) * 100
rulers$ruler_end_half <- floor(rulers$end_year / 50) * 50
rulers$ruler_end_quarter <- floor(rulers$end_year / 25) * 25

#Add "exit" column with 1s for survival models
rulers$exit <- 1

#Convert 0 duration values to 1
rulers$duration2 <- ifelse(rulers$duration==0, rulers$duration+1, rulers$duration)

rulers$previous_duration2 <- ifelse(rulers$previous_duration==0, rulers$previous_duration+1, rulers$previous_duration)

#squared and cubed start year for time trends

rulers$start_year2 <- rulers$start_year^2

rulers$start_year3 <- rulers$start_year^3

#log of previous duration, dynastic order, and polity duration

rulers$previous_duration2log <- log(rulers$previous_duration2 + 1)

rulers$dynastic_orderlog <- log(rulers$dynastic_order + 1)

############################
### Construct Panel Data ###
############################

cent <- seq(1000, 1800, by = 100)
timeframe <- data.frame(cent)

#merge dynasty data with century dataframe
dynasties_panel <- merge(timeframe, dynasties, all.x=TRUE, all.y=TRUE)

#Subset to centuries within dynastic lifespan
dynasties_panel <- subset(dynasties_panel, dynasties_panel$dyn_start <= cent & dynasties_panel$dyn_end >= cent)

#create IACW score in panel data
dynasties_panel$IACW_score <- ifelse(!is.na(dynasties_panel$IACW_primary_start) & dynasties_panel$IACW_primary_start <= dynasties_panel$cent & dynasties_panel$IACW_primary_end >= dynasties_panel$cent, 2, ifelse(dynasties_panel$IACW_partial_start <= dynasties_panel$cent & dynasties_panel$IACW_partial_end >= dynasties_panel$cent, 1, 0))

#Replace NAs with 0s for IACW variable
dynasties_panel$IACW_score[is.na(dynasties_panel$IACW_score)] <- 0

#create dummy for father-to-son in panel data
dynasties_panel$fs_dum <- ifelse(dynasties_panel$fs_start <= dynasties_panel$cent & dynasties_panel$fs_end >= dynasties_panel$cent, 1, 0)

#Replace NAs with 0s for father-to-son variable
dynasties_panel$fs_dum[is.na(dynasties_panel$fs_dum)] <- 0

#Entry ID
dynasties_panel <- tibble::rowid_to_column(dynasties_panel, "entry_id")

### merge dynasty data with polities data ###

dynasties_polities_panel <- merge(dynasties_panel, polities, by.x=c("truhart_id", "cent"), by.y=c("truhart_id", "layer_year"), all.x=TRUE)

dynasties_polities_panel$SUM_IAC_all[is.na(dynasties_polities_panel$SUM_IAC_all) & !is.na(dynasties_polities_panel$entity_area_name)] <- 0
dynasties_polities_panel$SUM_Inter_state[is.na(dynasties_polities_panel$SUM_Inter_state) & !is.na(dynasties_polities_panel$entity_area_name)] <- 0
dynasties_polities_panel$SUM_Intra_state[is.na(dynasties_polities_panel$SUM_Intra_state) & !is.na(dynasties_polities_panel$entity_area_name)] <- 0

## Outcome Variables ##

#create dummy for NON-FS successor in panel data
dynasties_polities_panel$non_fs_successor <- ifelse(dynasties_polities_panel$fs_successor == 0 & dynasties_polities_panel$cent == dynasties_polities_panel$end_century, 1, 0)

#create dummy for conquest in panel data
dynasties_polities_panel$conquest_dum <- ifelse(dynasties_polities_panel$dynastic_end_conquest == 1 & dynasties_polities_panel$cent == dynasties_polities_panel$end_century, 1, 0)

#create dummy for conquest by NON-FS in panel data
dynasties_polities_panel$non_fs_conquest_dum <- dynasties_polities_panel$non_fs_successor*dynasties_polities_panel$conquest_dum

#assign 0 for non-conquest dynastic ends for which the successor's FS status is unknown
dynasties_polities_panel$non_fs_conquest_dum[is.na(dynasties_polities_panel$non_fs_conquest_dum) & (dynasties_polities_panel$conquest_dum==0)] <- 0

#find duplicates
dynasties_polities_panel[duplicated(dynasties_polities_panel$entry_id),]

#Construct geopolitical fragmentation measure
region_fragmentation <- aggregate(cbind(SUM_HYDE_pop) ~ core_region + cent, data = dynasties_polities_panel, sum)
names(region_fragmentation)[names(region_fragmentation)=="SUM_HYDE_pop"] <- "Total_region_pop"

dynasties_polities_panel <- merge(dynasties_polities_panel, region_fragmentation, by.x = c("core_region", "cent"), by.y = c("core_region", "cent"), all.x=TRUE, all.y=FALSE)

#population
dynasties_polities_panel$pol_prop_pop <- dynasties_polities_panel$SUM_HYDE_pop/dynasties_polities_panel$Total_region_pop
dynasties_polities_panel$fs_pol_prop_pop <- dynasties_polities_panel$pol_prop_pop * dynasties_polities_panel$fs_dum

## merge rulers data with panel data ##
rulers <- merge(rulers, dynasties_polities_panel[ , c("dynpol_id", "truhart_id", "fs_ever", "cent", "pol_prop_pop", "state_hist_log", "SUM_IAC_all", "SUM_Inter_state", "SUM_Intra_state", "mean_elevation", "mean_open_terrain", "warm_water_coast", "inner_asia_border_dist", "EPR1_ID", "EPR2_ID", "EPR3_ID")], by.x=c("truhart_id", "ruler_start_century"), by.y=c("truhart_id", "cent"), all.x=TRUE)

#################################################################################
### Figure 1. Prevalence of Father-to-son Succession Systems, 1000-1800 CE ###
#################################################################################

#Subset to Middle East, Europe, Indian Subcontinent, and East Asia
dynasties_polities_panel_FS_proportions <- dynasties_polities_panel[dynasties_polities_panel$core_region != 'Inner_Asia' & dynasties_polities_panel$core_region != 'Southeast_Asia',]

region_agg_sum <- aggregate(cbind(fs_pol_prop_pop) ~ core_region + cent, data = dynasties_polities_panel_FS_proportions, sum)

region_fs <- ggplot(region_agg_sum, aes(x=cent, y=fs_pol_prop_pop, colour = as.factor(core_region), linetype = as.factor(core_region))) +
  geom_line(size = 1) +
  scale_linetype_manual(labels = c("East Asia", "Europe", "Indian Subcontinent", "Middle East"), name = "Region", values = c(1, 2, 3, 4)) +
  scale_color_manual(labels = c("East Asia", "Europe", "Indian Subcontinent", "Middle East"), values = c("black", "black", "darkgray", "darkgray"), name = "Region") +
  ylim(0, 1.01) +
  labs(x = "Year", y = "Proportion FS", color = "Region") +
  theme_bw() +
  theme(
    legend.title = element_text(size = 16, hjust = 0.5),
    legend.text = element_text(size = 12, hjust = 0),
    axis.title.x = element_text(size = 16, hjust = 0.5, margin = margin(t = 15)),
    axis.title.y = element_text(size = 16, hjust = 0.5, margin = margin(r = 15)))

print(region_fs)

ggsave("Figure_1_FS_Proportions.tiff", plot = region_fs, width = 10, height = 6, units = "in", dpi = 300)

###############################################################################################
### Figure 2. Dynastic Average Rule Duration by Border Distance to Inner Asia, 1000-1799 CE ###
###############################################################################################

#Aggregate by dynasty

dynasties_agg_mean <- aggregate(cbind(inner_asia_border_dist, fs_ever, duration) ~ dynpol_id, data = rulers, mean)

dynasties_agg_length <- aggregate(cbind(dynasty_id) ~ dynpol_id, data = rulers, length)

dynasties_agg <- merge(dynasties_agg_mean, dynasties_agg_length, by.x = c("dynpol_id"), by.y = c("dynpol_id"), all.x=TRUE, all.y=FALSE)

#Plot

dynasties_agg_3 <- dynasties_agg[which(dynasties_agg$dynasty_id >= 3),]

dist_duration <- ggplot(dynasties_agg_3, aes(x=inner_asia_border_dist, y=duration)) +
  geom_point(aes(shape=factor(fs_ever), color=factor(fs_ever), size=factor(fs_ever)), size = 2) +
  ylim(0, 50) +
  xlim(0, 2600) +
  scale_shape_manual(labels = c("No", "Yes"),values = c(16, 17), name = "Father-to-son") +
  scale_color_manual(labels = c("No", "Yes"), values = c("gray", "black"), name = "Father-to-son") +
  stat_smooth(method = "lm", fill="lightgray", se = TRUE, colour="black", linetype = "dashed") +
  labs(x = "Border Distance from Inner Asia (km)", y = "Average Rule Duration") +
  theme_bw() +
  theme(
    legend.title = element_text(size = 16, hjust = 0.5),
    legend.text = element_text(size = 12, hjust = 0),
    axis.title.x = element_text(size = 16, hjust = 0.5, margin = margin(t = 15)),
    axis.title.y = element_text(size = 16, hjust = 0.5, margin = margin(r = 15))) +
  scale_x_continuous(breaks=seq(0,2500,500))

dist_duration

ggsave("Figure_2_Dyn_rule_average_by_dist.tiff", plot = dist_duration, width = 10, height = 6, units = "in", dpi = 300)

#########################################################################
### Figure 3. Father-to-son Succession Systems Increase Rule Duration ###
#########################################################################

Argument_diagram <- DiagrammeR::grViz("digraph {
  
graph[layout = dot, rankdir = LR, ranksep=1]

a [label = 'Father-to-son\nSuccession'] 
d [label = 'Young Heir']
b [label = 'Pacific Elite \nCoordination'] 
e [label = 'Low Incumbent \nDeposal Risk']
f [label = 'Lengthy Rule']

a -> b
a -> d
b -> e
d -> e [color = black]
d -> f [color = black]
e -> f
}")

Argument_diagram

Argument_diagram %>% export_svg %>% charToRaw %>% rsvg_png("Figure_3_FS_duration_diagram.tiff", width = 3000, height = 2100)

################################################################################
### Figure 4. Eurasian Rulers Practicing FS Succession Enjoyed Longer Reigns ###
################################################################################

fs_vs_other <- rulers %>%
  ggplot( aes(x=as.factor(father_to_son), y=duration, fill=as.factor(father_to_son))) +
  geom_boxplot(color="black", fill="white") +
  ylim(0, 80) +
  scale_fill_viridis(discrete = TRUE) +
  scale_x_discrete(labels=c("0" = "Other", "1" = "Father-to-son")) +
  geom_jitter(color="grey", size=0.7, alpha=0.5) +
  theme_bw() +
  theme(
    legend.position="none",
    plot.title = element_text(size=16),
    axis.text.x = element_text(size = 16, hjust = 0.5),
    axis.title.x = element_text(size = 16, hjust = 0.5, margin = margin(t = 15)),
    axis.title.y = element_text(size = 16, hjust = 0.5, margin = margin(r = 15))
  ) +
  ggtitle("") +
  xlab("") +
  ylab("Rule Duration")

ggsave("Figure_4_FS_vs_Other.tiff", plot = fs_vs_other, width = 10, height = 6, units = "in", dpi = 300)

#############################################
### Figure 5. Rule Duration by IACW Score ###
##############################################

IACW_score <- rulers %>%
  ggplot( aes(x=as.factor(IACW), y=duration, fill=as.factor(father_to_son))) +
  geom_boxplot(color="black", fill="white") +
  ylim(0, 80) +
  scale_fill_viridis(discrete = TRUE) +
  scale_x_discrete(labels=c("0" = "Non-IACW", "1" = "Partial IACW", "2" = "IACW")) +
  geom_jitter(color="grey", size=0.7, alpha=0.5) +
  theme_bw() +
  theme(
    legend.position="none",
    plot.title = element_text(size=16),
    axis.text.x = element_text(size = 16, hjust = 0.5),
    axis.title.x = element_text(size = 16, hjust = 0.5, margin = margin(t = 15)),
    axis.title.y = element_text(size = 16, hjust = 0.5, margin = margin(r = 15))
  ) +
  ggtitle("") +
  xlab("") +
  ylab("Rule Duration")

ggsave("Figure_5_IACW_Score.tiff", plot = IACW_score, width = 10, height = 6, units = "in", dpi = 300)

##################################################################################################################################################
### Table 2. Linear Probability Models: Reliance on Inner Asian Cavalry Warfare Is Negatively Associated with Father-to-son Succession Systems ###
##################################################################################################################################################

## Truncate data to 1000-1700 century snapshots for main analyses ##
dynasties_polities_panel <- dynasties_polities_panel[which(dynasties_polities_panel$cent<1800), ]

#IACW Score + FE
Dyn1 <- lm(fs_dum ~ IACW_score +
             as.factor(core_region) +
             as.factor(cent), 
           data=dynasties_polities_panel)

#IACW Score + Warfare Vars + FE
Dyn2 <- lm(fs_dum ~ IACW_score +
             log(SUM_IAC_all+1) +
             log(SUM_Inter_state+1) +
             log(SUM_Intra_state+1) +
             as.factor(core_region) +
             as.factor(cent), 
           data=dynasties_polities_panel)

#IACW Score + Warfare Vars + Polity Vars + FE
Dyn3 <- lm(fs_dum ~ IACW_score +
             log(SUM_IAC_all+1) +
             log(SUM_Inter_state+1) +
             log(SUM_Intra_state+1) +
             pol_prop_pop +
             state_hist_log +
             log(mean_elevation+1) +
             log(mean_open_terrain+1) +
             warm_water_coast +
             core_latitude +
             as.factor(core_region) +
             as.factor(cent), 
           data=dynasties_polities_panel)

# Robust SEs
vcov1 <- vcovHC(Dyn1, type = "HC0", cluster = ~core_region + cent)
vcov2 <- vcovHC(Dyn2, type = "HC0", cluster = ~core_region + cent)
vcov3 <- vcovHC(Dyn3, type = "HC0", cluster = ~core_region + cent)

# Output
modelsummary(
  list("Model 1" = Dyn1, "Model 2" = Dyn2, "Model 3" = Dyn3),
  vcov = list(vcov1, vcov2, vcov3),
  statistic = "({std.error})",
  coef_order = "traditional",
  stars = c('^' = .1, '*' = .05, '**' = .01),
  fmt = "%.2f",
  gof_omit = "AIC|BIC|Log.Lik",
  output = "Table_2.html"
)

###############################################################################################################
### Table 3. Linear Probability Models: Inner Asian Cavalry Warfare Conditionally Predicts Non-FS Conquests ###
###############################################################################################################

#IACW Battles + FE
Dyn1 <- lm(non_fs_conquest_dum ~ log(SUM_IAC_all+1) +
             as.factor(core_region) +
             as.factor(cent), 
           data=dynasties_polities_panel)

#IACW Battles + Warfare Vars + FE
Dyn2 <- lm(non_fs_conquest_dum ~ log(SUM_IAC_all+1) +
             log(SUM_Inter_state+1) +
             log(SUM_Intra_state+1) +
             as.factor(core_region) +
             as.factor(cent), 
           data=dynasties_polities_panel)

#IACW Battles + Warfare Vars + Polity Vars + FE
Dyn3 <- lm(non_fs_conquest_dum ~ log(SUM_IAC_all+1) +
             log(SUM_Inter_state+1) +
             log(SUM_Intra_state+1) +
             pol_prop_pop +
             state_hist_log +
             log(mean_elevation+1) +
             log(mean_open_terrain+1) +
             warm_water_coast +
             core_latitude +
             as.factor(core_region) +
             as.factor(cent), 
           data=dynasties_polities_panel)

#IACW Battles + FS Dummy + Warfare Vars + Polity Vars + FE
Dyn4 <- lm(non_fs_conquest_dum ~ log(SUM_IAC_all+1) +
             fs_dum +
             log(SUM_Inter_state+1) +
             log(SUM_Intra_state+1) +
             pol_prop_pop +
             state_hist_log +
             log(mean_elevation+1) +
             log(mean_open_terrain+1) +
             warm_water_coast +
             core_latitude +
             as.factor(core_region) +
             as.factor(cent), 
           data=dynasties_polities_panel)

#IACW Battles*FS Dummy Interaction + Warfare Vars + Polity Vars + FE
Dyn5 <- lm(non_fs_conquest_dum ~ fs_dum:log(SUM_IAC_all+1) + 
             log(SUM_IAC_all+1) +
             fs_dum +
             log(SUM_Inter_state+1) +
             log(SUM_Intra_state+1) +
             pol_prop_pop +
             state_hist_log +
             log(mean_elevation+1) +
             log(mean_open_terrain+1) +
             warm_water_coast +
             core_latitude +
             as.factor(core_region) +
             as.factor(cent), 
           data=dynasties_polities_panel)

# Robust SEs
vcov1 <- vcovHC(Dyn1, type = "HC0", cluster = ~core_region + cent)
vcov2 <- vcovHC(Dyn2, type = "HC0", cluster = ~core_region + cent)
vcov3 <- vcovHC(Dyn3, type = "HC0", cluster = ~core_region + cent)
vcov4 <- vcovHC(Dyn4, type = "HC0", cluster = ~core_region + cent)
vcov5 <- vcovHC(Dyn5, type = "HC0", cluster = ~core_region + cent)

# Output
modelsummary(
  list("Model 1" = Dyn1, "Model 2" = Dyn2, "Model 3" = Dyn3, "Model 4" = Dyn4, "Model 5" = Dyn5),
  vcov = list(vcov1, vcov2, vcov3, vcov4, vcov5),
  statistic = "({std.error})",
  stars = c('^' = .1, '*' = .05, '**' = .01),
  fmt = "%.2f",
  gof_omit = "AIC|BIC|Log.Lik",
  coef_order = "traditional",
  output = "Table_3.html"
)

### Structural Break Visuals and Models ###

## Define Case Areas ##

#China Proper
rulers_china_proper <- rulers[which(
  rulers$truhart_id=='10.313' #China (Song)
  | rulers$truhart_id=='10.315' #China (Yuan)
  | rulers$truhart_id=='10.456'#Western Xia
  | rulers$truhart_id=='10.314' #Jin
  | rulers$truhart_id=='10.322'),] #Great Liao

#subset to pre-1368
rulers_china_proper <- rulers_china_proper[which(rulers_china_proper$end_year < 1368),]

#Northern India (Indo-Gangetic Plains; excludes montane polities)
rulers_northern_india <- rulers[which(
  rulers$truhart_id=='11.182' #Chandellas
  | rulers$truhart_id=='11.111' #Ujjain
  | rulers$truhart_id=='11.119' #Dhar
  | rulers$truhart_id=='12.161' #Bengal
  | rulers$truhart_id=='11.923' #Gandhara
  | rulers$truhart_id=='12.305' #Delhi Sultanate
  | rulers$truhart_id=='11.521' #Gujarat
  | rulers$truhart_id=='11.851' #Mewar
  | rulers$truhart_id=='11.870' #Jaisalmer
  | rulers$truhart_id=='11.889' #Jodhpur
  | rulers$truhart_id=='11.892' #Udaipur
  | rulers$truhart_id=='11.5153' #Chaulukyas
  | rulers$truhart_id=='12.307'),] #Varanasi


#subset to pre-1526
rulers_northern_india <- rulers_northern_india[which(rulers_northern_india$end_year < 1526),]

## China Proper: convert ruler data into panel data (t = quarter) ##
rulers_china_proper_quarter <- aggregate(cbind(duration2, deposed, IACW) ~ ruler_start_quarter, data = rulers_china_proper, mean)

#order chronologically
rulers_china_proper_quarter <- rulers_china_proper_quarter[order(rulers_china_proper_quarter$ruler_start_quarter),]

#create mean duration vector
china_proper_quarter_mean_duration <- rulers_china_proper_quarter$duration2

CP_mean_duration <- zoo(china_proper_quarter_mean_duration)

#lag mean duration
CP_mean_duration_lag <- stats::lag(CP_mean_duration, -1, na.pad = TRUE)

#cbind mean duration and its lag as time series
CP_mean_duration_dat <- ts(drop_na(data.frame(cbind(CP_mean_duration, CP_mean_duration_lag))))

#generate Quandt Likelihood Ratio statistic
CP_mean_duration_qlr <- Fstats(CP_mean_duration ~ CP_mean_duration_lag, data = CP_mean_duration_dat, from=3)

#Identify breakpoints
bp.CP_mean_duration <- breakpoints(CP_mean_duration_qlr)
summary(bp.CP_mean_duration)

#Significance test for that value
sctest(CP_mean_duration_qlr, type = "supF")

## Northern India: convert ruler data into panel data (t = half) ##
rulers_northern_india_half <- aggregate(cbind(duration2, deposed, IACW) ~ ruler_start_half, data = rulers_northern_india, mean)

#order chronologically
rulers_northern_india_half <- rulers_northern_india_half[order(rulers_northern_india_half$ruler_start_half),]

#create mean duration vector
northern_india_half_mean_duration <- rulers_northern_india_half$duration2

NI_mean_duration <- zoo(northern_india_half_mean_duration)

#lag mean duration
NI_mean_duration_lag <- stats::lag(NI_mean_duration, -1, na.pad = TRUE)

#cbind mean duration and its lag as time series
NI_mean_duration_dat <- ts(drop_na(data.frame(cbind(NI_mean_duration, NI_mean_duration_lag))))

#generate Quandt Likelihood Ratio statistic
NI_mean_duration_qlr <- Fstats(NI_mean_duration ~ NI_mean_duration_lag, data = NI_mean_duration_dat, from=3)

#Identify breakpoints
breakpoints(NI_mean_duration_qlr)

#Significance test for that value
sctest(NI_mean_duration_qlr, type = "supF")

#########################################################################################
### Figure 7. Inner Asian Conquests and Rule Duration in Northern India, 1000-1499 CE ###
#########################################################################################

northern_india_plot <- ggplot(rulers_northern_india, aes(x = start_year, y = duration2)) +
  ggtitle("") +
  geom_smooth(span = 0.7, colour = "black") +
  geom_point(aes(shape=factor(father_to_son), color=factor(father_to_son))) +
  scale_color_manual(labels = c("No", "Yes"),values = c("lightgray", "black"), name = "Father-to-son") +
  scale_shape_manual(labels = c("No", "Yes"),values = c(16, 17), name = "Father-to-son") +
  xlim(1000, 1526) +
  ylim(0, 50) +
  xlab("Year") +
  ylab("Rule Duration") +
  geom_vline(xintercept = c(1150),
             linetype = 2,
             color = "darkgray",
             linewidth = 1) + 
  theme_bw() +
  theme(axis.title.x = element_text(size = 16, hjust = 0.5, margin = margin(t = 15)),
        axis.title.y = element_text(size = 16, hjust = 0.5, margin = margin(r = 15)),
        legend.title = element_text(size = 16, hjust = 0.5),
        legend.text = element_text(size = 12, hjust = 0),
        plot.margin = margin(t = 0,  # Top margin
                             r = 0,  # Right margin
                             b = 0,  # Bottom margin
                             l = 0))

northern_india_plot

ggsave("Figure_7_North_India.tiff", plot = northern_india_plot, width = 10, height = 6, units = "in", dpi = 300)

#######################################################################################
### Figure 8. Inner Asian Conquests and Rule Duration in China Proper, 1000-1368 CE ###
#######################################################################################

china_proper_plot <- ggplot(rulers_china_proper, aes(x = start_year, y = duration)) +
  ggtitle("") +
  geom_smooth(span = 0.7, colour = "black") +
  geom_point(aes(shape=factor(father_to_son), color=factor(father_to_son))) +
  scale_color_manual(labels = c("No", "Yes"),values = c("lightgray", "black"), name = "Father-to-son") +
  scale_shape_manual(labels = c("No", "Yes"),values = c(16, 17), name = "Father-to-son") +
  xlim(1000, 1368) +
  ylim(-5, 60) +
  xlab("Year") +
  ylab("Rule Duration") +
  geom_vline(xintercept = c(1150),
             linetype = 2,
             color = "darkgray",
             linewidth = 1) + 
  theme_bw() +
  theme(
    axis.title.x = element_text(size = 16, hjust = 0.5, margin = margin(t = 15)),
    axis.title.y = element_text(size = 16, hjust = 0.5, margin = margin(r = 15)),
    legend.title = element_text(size = 16, hjust = 0.5),
    legend.text = element_text(size = 12, hjust = 0),
    plot.margin = margin(t = 0,  # Top margin
                         r = 0,  # Right margin
                         b = 0,  # Bottom margin
                         l = 0))

china_proper_plot

ggsave("Figure_8_China_Proper.tiff", plot = china_proper_plot, width = 10, height = 6, units = "in", dpi = 300)

###############################
### Supplementary Materials ###
###############################

####################################################################################
### Table A1. Rulers in States with Father-to-son Succession Systems Rule Longer ###
####################################################################################

#FS Succession + FE
Cox1 <- coxph(Surv(duration2) ~ father_to_son + 
                as.factor(core_region) + as.factor(ruler_start_half) +
                start_year + 
                start_year2 + 
                start_year3, data=rulers)

#FS Succession + Ruler & Dynastic Vars + FE
Cox2 <- coxph(Surv(duration2) ~ father_to_son + 
                previous_duration2log + 
                dynastic_orderlog + 
                son + 
                parliament + 
                military_slave_corps +
                IACW +
                as.factor(core_region) + 
                as.factor(ruler_start_half) + 
                start_year + 
                start_year2 + 
                start_year3, data=rulers)

#FS Succession + Ruler & Dynastic Vars + Polity Vars + FE
Cox3 <- coxph(Surv(duration2) ~ father_to_son + 
                previous_duration2log + 
                dynastic_orderlog + 
                son +
                parliament + 
                military_slave_corps +
                IACW +
                log(SUM_IAC_all+1) +
                log(SUM_Inter_state+1) +
                log(SUM_Intra_state+1) +
                pol_prop_pop +
                state_hist_log +
                log(mean_elevation+1) +
                log(mean_open_terrain+1) +
                warm_water_coast +
                core_latitude +
                as.factor(core_region) + 
                as.factor(ruler_start_half) + 
                start_year + 
                start_year2 + 
                start_year3, data=rulers)

modelsummary(
  list("Model 1" = Cox1, "Model 2" = Cox2, "Model 3" = Cox3),
  statistic = "({std.error})",
  stars = c('^' = .1, '*' = .05, '**' = .01),
  fmt = "%.2f",
  coef_order = "traditional",
  output = "Table_A1.html"
)

#########################################################################################################################
### Table A2. Rulers in States with Father-to-son Succession Systems are Less Likely to be Deposed by Domestic Actors ###
#########################################################################################################################

#FS Succession + FE
Cox1 <- coxph(Surv(duration2, deposed) ~ father_to_son + 
                as.factor(core_region) + as.factor(ruler_start_half) +
                start_year + 
                start_year2 + 
                start_year3, data=rulers)

#FS Succession + Ruler & Dynastic Vars + FE
Cox2 <- coxph(Surv(duration2, deposed) ~ father_to_son + 
                previous_duration2log + 
                dynastic_orderlog + 
                son + 
                parliament + 
                military_slave_corps +
                IACW +
                as.factor(core_region) + 
                as.factor(ruler_start_half) + 
                start_year + 
                start_year2 + 
                start_year3, data=rulers)

#FS Succession + Ruler & Dynastic Vars + Polity Vars + FE
Cox3 <- coxph(Surv(duration2, deposed) ~ father_to_son + 
                previous_duration2log + 
                dynastic_orderlog + 
                son +
                parliament + 
                military_slave_corps +
                IACW +
                log(SUM_IAC_all+1) +
                log(SUM_Inter_state+1) +
                log(SUM_Intra_state+1) +
                pol_prop_pop +
                state_hist_log +
                log(mean_elevation+1) +
                log(mean_open_terrain+1) +
                warm_water_coast +
                core_latitude +
                as.factor(core_region) + 
                as.factor(ruler_start_half) + 
                start_year + 
                start_year2 + 
                start_year3, data=rulers)

modelsummary(
  list("Model 1" = Cox1, "Model 2" = Cox2, "Model 3" = Cox3),
  statistic = "({std.error})",
  stars = c('^' = .1, '*' = .05, '**' = .01),
  fmt = "%.2f",
  coef_order = "traditional",
  output = "Table_A2.html"
)

##############################################################################################################################################
### Table A3. Fixed Effects Models: Reliance on Inner Asian Cavalry Warfare Is Negatively Associated with Father-to-son Succession Systems ###
##############################################################################################################################################

#IACW Score + FE
DynA1 <- fixest::feols(fs_dum ~ IACW_score | as.factor(truhart_id) + as.factor(cent), dynasties_polities_panel)

#IACW Score + Warfare Vars + FE
DynA2 <- fixest::feols(fs_dum ~ IACW_score + 
                log(SUM_IAC_all+1) + 
                log(SUM_Inter_state+1)  + 
                log(SUM_Intra_state+1)| as.factor(truhart_id) + as.factor(cent), dynasties_polities_panel)

#IACW Score + Warfare Vars + Polity Vars + FE
DynA3 <- fixest::feols(fs_dum ~ IACW_score + 
                log(SUM_IAC_all+1) + 
                log(SUM_Inter_state+1) + 
                log(SUM_Intra_state+1) +
                pol_prop_pop +
                state_hist_log | as.factor(truhart_id) + as.factor(cent), dynasties_polities_panel)

# Robust SEs
DynA1_robust<- summary(DynA1, vcov = ~truhart_id + cent)
DynA2_robust<- summary(DynA2, vcov = ~truhart_id + cent)
DynA3_robust<- summary(DynA3, vcov = ~truhart_id + cent)

# Output
modelsummary(
  list("Model 1" = DynA1_robust, "Model 2" = DynA2_robust, "Model 3" = DynA3_robust),
  statistic = "({std.error})",
  fmt = "%.2f",
  stars = c('^' = .1, '*' = .05, '**' = .01),
  gof_omit = "AIC|BIC|Log.Lik",
  coef_order = "traditional",
  output = "Table_A3.html"
)

##########################################################################################################################################################
### Table A4. 2SLS Instrumental Variable Models: Reliance on Inner Asian Cavalry Warfare Predicts Lower Likelihood of Father-to-son Succession Systems ###
##########################################################################################################################################################

#IACW Score + FE
IV1 <- iv_robust(fs_dum ~ IACW_score + 
                   as.factor(core_region) + 
                   as.factor(cent) |
                   inner_asia_border_dist_1000km + 
                   as.factor(core_region) + 
                   as.factor(cent), data = dynasties_polities_panel, diagnostics = TRUE, se_type = "HC0")

#IACW Score + Warfare Vars + FE
IV2 <- iv_robust(fs_dum ~ IACW_score + 
                   log(SUM_IAC_all+1) +
                   log(SUM_Inter_state+1) + 
                   log(SUM_Intra_state+1) + 
                   as.factor(core_region) + 
                   as.factor(cent) |
                   inner_asia_border_dist_1000km + 
                   log(SUM_IAC_all+1) +
                   log(SUM_Inter_state+1) + 
                   log(SUM_Intra_state+1) + 
                   as.factor(core_region) + 
                   as.factor(cent), data = dynasties_polities_panel, diagnostics = TRUE, se_type = "HC0")

#IACW Score + Warfare Vars + Polity Vars + FE
IV3 <- iv_robust(fs_dum ~ IACW_score +
                   log(SUM_IAC_all+1) + 
                   log(SUM_Inter_state+1) + 
                   log(SUM_Intra_state+1) + 
                   pol_prop_pop + 
                   state_hist_log + 
                   log(mean_elevation+1) + 
                   log(mean_open_terrain+1) + 
                   warm_water_coast + 
                   core_latitude + 
                   as.factor(core_region) + 
                   as.factor(cent) |
                   inner_asia_border_dist_1000km +   
                   log(SUM_IAC_all+1) +
                   log(SUM_Inter_state+1) + 
                   log(SUM_Intra_state+1) + 
                   pol_prop_pop + 
                   state_hist_log + 
                   log(mean_elevation+1) + 
                   log(mean_open_terrain+1) + 
                   warm_water_coast + 
                   core_latitude + 
                   as.factor(core_region) + 
                   as.factor(cent), data = dynasties_polities_panel, diagnostics = TRUE, se_type = "HC0")

# Prepare first stage F-statistics separately (not a modelsummary option)
gof_f <- tibble(
  term = "First-stage F-statistic",
  `Model 1` = IV1$diagnostic_first_stage_fstatistic[1],
  `Model 2` = IV2$diagnostic_first_stage_fstatistic[1],
  `Model 3` = IV3$diagnostic_first_stage_fstatistic[1], 
)

# Output
modelsummary(
  list("Model 1" = IV1, "Model 2" = IV2, "Model 3" = IV3),
  statistic = "({std.error})",
  fmt = "%.2f",
  stars = c('^' = .1, '*' = .05, '**' = .01),
  gof_omit = "R2|RMSE|AIC|BIC|Log.Lik",
  add_rows = gof_f,
  coef_order = "traditional",
  output = "Table_A4.html"
)

##################################################################################################################
### Table A5. Polity Fixed Effects Models: Inner Asian Cavalry Warfare Conditionally Predicts Non-FS Conquests ###
##################################################################################################################

#IACW Battles + FE
DynA1 <- fixest::feols(non_fs_conquest_dum ~ log(SUM_IAC_all+1) | as.factor(truhart_id) + as.factor(cent), dynasties_polities_panel)

#IACW Battles + Warfare Vars + FE
DynA2 <- fixest::feols(non_fs_conquest_dum ~ log(SUM_IAC_all+1) + 
                log(SUM_Inter_state+1)  + 
                log(SUM_Intra_state+1) | as.factor(truhart_id) + as.factor(cent), dynasties_polities_panel)

#IACW Battles + Warfare Vars + Polity Vars + FE
DynA3 <- fixest::feols(non_fs_conquest_dum ~ log(SUM_IAC_all+1) + 
                log(SUM_Inter_state+1)  + 
                log(SUM_Intra_state+1) + 
                pol_prop_pop + 
                state_hist_log | as.factor(truhart_id) + as.factor(cent), dynasties_polities_panel)

#IACW Battles + FS Dummy + Warfare Vars + Polity Vars + FE
DynA4 <- fixest::feols(non_fs_conquest_dum ~ log(SUM_IAC_all+1) + 
                fs_dum + 
                log(SUM_Inter_state+1) + 
                log(SUM_Intra_state+1) + 
                pol_prop_pop + 
                state_hist_log | as.factor(truhart_id) + as.factor(cent), dynasties_polities_panel)

#IACW Battles*FS Dummy Interaction + Warfare Vars + Polity Vars + FE
DynA5 <- fixest::feols(non_fs_conquest_dum ~ fs_dum:log(SUM_IAC_all+1) + 
                log(SUM_IAC_all+1) + 
                fs_dum + 
                log(SUM_Inter_state+1)  + 
                log(SUM_Intra_state+1) + 
                pol_prop_pop + 
                state_hist_log | as.factor(truhart_id) + as.factor(cent), dynasties_polities_panel)

# Robust SEs
DynA1_robust<- summary(DynA1, vcov = ~truhart_id + cent)
DynA2_robust<- summary(DynA2, vcov = ~truhart_id + cent)
DynA3_robust<- summary(DynA3, vcov = ~truhart_id + cent)
DynA4_robust<- summary(DynA4, vcov = ~truhart_id + cent)
DynA5_robust<- summary(DynA5, vcov = ~truhart_id + cent)

# Output
modelsummary(
  list("Model 1" = DynA1_robust, "Model 2" = DynA2_robust, "Model 3" = DynA3_robust, "Model 4" = DynA4_robust, "Model 5" = DynA5_robust),
  statistic = "({std.error})",
  fmt = "%.2f",
  stars = c('^' = .1, '*' = .05, '**' = .01),
  gof_omit = "AIC|BIC|Log.Lik",
  coef_order = "traditional",
  output = "Table_A5.html"
)

################################################################################################################
### Table A6. FE Models: Reliance on Inner Asian Cavalry Warfare Is Negatively Associated with Rule Duration ###
################################################################################################################

## Duration (All Exits) 250,000 sqkm ##

Cox1 <- coxph(Surv(duration2) ~ IACW + 
                previous_duration2log + 
                dynastic_orderlog + 
                son +
                parliament + 
                military_slave_corps +
                log(SUM_IAC_all+1) +
                log(SUM_Inter_state+1) +
                log(SUM_Intra_state+1) +
                pol_prop_pop +
                state_hist_log +
                log(mean_elevation+1) +
                log(mean_open_terrain+1) +
                warm_water_coast +
                core_latitude +
                strata(as.factor(GRID_ID_250k)) + 
                as.factor(ruler_start_century) + 
                start_year + 
                start_year2 + 
                start_year3, data=rulers)

## Duration (All Exits) 500,000 sqkm ##

Cox2 <- coxph(Surv(duration2) ~ IACW + 
                previous_duration2log + 
                dynastic_orderlog + 
                son +
                parliament + 
                military_slave_corps +
                log(SUM_IAC_all+1) +
                log(SUM_Inter_state+1) +
                log(SUM_Intra_state+1) +
                pol_prop_pop +
                state_hist_log +
                log(mean_elevation+1) +
                log(mean_open_terrain+1) +
                warm_water_coast +
                core_latitude +
                strata(as.factor(GRID_ID_500k)) + 
                as.factor(ruler_start_century) + 
                start_year + 
                start_year2 + 
                start_year3, data=rulers)

## Duration (All Exits) 1,000,000 sqkm ##

Cox3 <- coxph(Surv(duration2) ~ IACW + 
                previous_duration2log + 
                dynastic_orderlog + 
                son +
                parliament + 
                military_slave_corps +
                log(SUM_IAC_all+1) +
                log(SUM_Inter_state+1) +
                log(SUM_Intra_state+1) +
                pol_prop_pop +
                state_hist_log +
                log(mean_elevation+1) +
                log(mean_open_terrain+1) +
                warm_water_coast +
                core_latitude +
                strata(as.factor(GRID_ID_1000k)) + 
                as.factor(ruler_start_century) + 
                start_year + 
                start_year2 + 
                start_year3, data=rulers)

modelsummary(
  list("Model 1" = Cox1, "Model 2" = Cox2, "Model 3" = Cox3),
  statistic = "({std.error})",
  stars = c('^' = .1, '*' = .05, '**' = .01),
  fmt = "%.2f",
  coef_order = "traditional",
  output = "Table_A6.html"
)

#############################################################
### Table B1. Dynasty-Century Data Descriptive Statistics ###
#############################################################

datasummary(
  fs_dum + non_fs_conquest_dum + SUM_IAC_all + SUM_Inter_state + SUM_Intra_state + inner_asia_core_dist_1000km + 
    inner_asia_border_dist_1000km + mean_elevation + mean_open_terrain + warm_water_coast + state_history + pol_prop_pop   ~ N + Mean + SD + Min + Median + Max,
  data = dynasties_polities_panel,
  output = "Table_B1.html"
)

############################################################################################
### Table B2. IACW Score Predicts Father-to-son Succession Systems (Logistic Regression) ###
############################################################################################

#IACW Score + FE
LogitA1 <- glm(fs_dum ~ IACW_score +
                 as.factor(core_region) +
                 as.factor(cent), 
               data=dynasties_polities_panel, family = binomial(link="logit"))

#IACW Score + Warfare Vars + FE
LogitA2 <- glm(fs_dum ~ IACW_score +
                 log(SUM_IAC_all+1) +
                 log(SUM_Inter_state+1) +
                 log(SUM_Intra_state+1) +
                 as.factor(core_region) +
                 as.factor(cent), 
               data=dynasties_polities_panel, family = binomial(link="logit"))

#IACW Score + Warfare Vars + Polity Vars + FE
LogitA3 <- glm(fs_dum ~ IACW_score +
                 log(SUM_IAC_all+1) +
                 log(SUM_Inter_state+1) +
                 log(SUM_Intra_state+1) +
                 pol_prop_pop +
                 state_hist_log +
                 log(mean_elevation+1) +
                 log(mean_open_terrain+1) +
                 warm_water_coast +
                 core_latitude +
                 as.factor(core_region) +
                 as.factor(cent), 
               data=dynasties_polities_panel, family = binomial(link="logit"))

# Robust SEs
vcov1 <- vcovHC(LogitA1, type = "HC0", cluster = ~core_region + cent)
vcov2 <- vcovHC(LogitA2, type = "HC0", cluster = ~core_region + cent)
vcov3 <- vcovHC(LogitA3, type = "HC0", cluster = ~core_region + cent)

# Output
modelsummary(
  list("Model 1" = LogitA1, "Model 2" = LogitA2, "Model 3" = LogitA3),
  vcov = list(vcov1, vcov2, vcov3),
  statistic = "({std.error})",
  fmt = "%.2f",
  stars = c('^' = .1, '*' = .05, '**' = .01),
  coef_order = "traditional",
  output = "Table_B2.html"
)

###########################################################################################
### Table B3. IACW Conflict Conditionally Predict Non-FS Conquest (Logistic Regression) ###
###########################################################################################

#IACW Battles + FE
LogitA1 <- glm(non_fs_conquest_dum ~ log(SUM_IAC_all+1) +
                 as.factor(core_region) +
                 as.factor(cent), 
               data=dynasties_polities_panel, family = binomial(link="logit"))

#IACW Battles + Warfare Vars + FE
LogitA2 <- glm(non_fs_conquest_dum ~ log(SUM_IAC_all+1) +
                 log(SUM_Inter_state+1) +
                 log(SUM_Intra_state+1) +
                 as.factor(core_region) +
                 as.factor(cent), 
               data=dynasties_polities_panel, family = binomial(link="logit"))

#IACW Battles + Warfare Vars + Polity Vars + FE
LogitA3 <- glm(non_fs_conquest_dum ~ log(SUM_IAC_all+1) +
                 log(SUM_Inter_state+1) +
                 log(SUM_Intra_state+1) +
                 pol_prop_pop +
                 state_hist_log +
                 log(mean_elevation+1) +
                 log(mean_open_terrain+1) +
                 warm_water_coast +
                 core_latitude +
                 as.factor(core_region) +
                 as.factor(cent), 
               data=dynasties_polities_panel, family = binomial(link="logit"))

#IACW Battles + FS Dummy + Warfare Vars + Polity Vars + FE
LogitA4 <- glm(non_fs_conquest_dum ~ log(SUM_IAC_all+1) +
                 fs_dum +
                 log(SUM_Inter_state+1) +
                 log(SUM_Intra_state+1) +
                 pol_prop_pop +
                 state_hist_log +
                 log(mean_elevation+1) +
                 log(mean_open_terrain+1) +
                 warm_water_coast +
                 core_latitude +
                 as.factor(core_region) +
                 as.factor(cent), 
               data=dynasties_polities_panel, family = binomial(link="logit"))

#IACW Battles*FS Dummy Interaction + Warfare Vars + Polity Vars + FE
LogitA5 <- glm(non_fs_conquest_dum ~ fs_dum:log(SUM_IAC_all+1) + 
                 log(SUM_IAC_all+1) +
                 fs_dum +
                 log(SUM_Inter_state+1) +
                 log(SUM_Intra_state+1) +
                 pol_prop_pop +
                 state_hist_log +
                 log(mean_elevation+1) +
                 log(mean_open_terrain+1) +
                 warm_water_coast +
                 core_latitude +
                 as.factor(core_region) +
                 as.factor(cent), 
               data=dynasties_polities_panel, family = binomial(link="logit"))

# Robust SEs
vcov1 <- vcovHC(LogitA1, type = "HC0", cluster = ~core_region + cent)
vcov2 <- vcovHC(LogitA2, type = "HC0", cluster = ~core_region + cent)
vcov3 <- vcovHC(LogitA3, type = "HC0", cluster = ~core_region + cent)
vcov4 <- vcovHC(LogitA4, type = "HC0", cluster = ~core_region + cent)
vcov5 <- vcovHC(LogitA5, type = "HC0", cluster = ~core_region + cent)

# Output
modelsummary(
  list("Model 1" = LogitA1, "Model 2" = LogitA2, "Model 3" = LogitA3, "Model 4" = LogitA4, "Model 5" = LogitA5),
  vcov = list(vcov1, vcov2, vcov3, vcov4, vcov5),
  statistic = "({std.error})",
  fmt = "%.2f",
  stars = c('^' = .1, '*' = .05, '**' = .01),
  coef_order = "traditional",
  output = "Table_B3.html"
)


#############################################################################
### Table B4. IACW Score Predicts FS Succession (Eurasian pseudo-regions) ###
#############################################################################

## EPR1 ##

EPR1 <- lm(fs_dum ~ IACW_score +
             log(SUM_IAC_all+1) +
             log(SUM_Inter_state+1) +
             log(SUM_Intra_state+1) +
             pol_prop_pop +
             state_hist_log +
             log(mean_elevation+1) +
             log(mean_open_terrain+1) +
             warm_water_coast +
             core_latitude +
             as.factor(EPR1_ID) +
             as.factor(cent), 
           data=dynasties_polities_panel)

## EPR2 ##

EPR2 <- lm(fs_dum ~ IACW_score +
             log(SUM_IAC_all+1) +
             log(SUM_Inter_state+1) +
             log(SUM_Intra_state+1) +
             pol_prop_pop +
             state_hist_log +
             log(mean_elevation+1) +
             log(mean_open_terrain+1) +
             warm_water_coast +
             core_latitude +
             as.factor(EPR2_ID) +
             as.factor(cent), 
           data=dynasties_polities_panel)

## EPR3 ##

EPR3 <- lm(fs_dum ~ IACW_score +
             log(SUM_IAC_all+1) +
             log(SUM_Inter_state+1) +
             log(SUM_Intra_state+1) +
             pol_prop_pop +
             state_hist_log +
             log(mean_elevation+1) +
             log(mean_open_terrain+1) +
             warm_water_coast +
             core_latitude +
             as.factor(EPR3_ID) +
             as.factor(cent), 
           data=dynasties_polities_panel)

# Robust SEs
vcov1 <- vcovHC(EPR1, type = "HC0", cluster = ~core_region + cent)
vcov2 <- vcovHC(EPR2, type = "HC0", cluster = ~core_region + cent)
vcov3 <- vcovHC(EPR3, type = "HC0", cluster = ~core_region + cent)

# Output
modelsummary(
  list("EPR 1" = EPR1, "EPR 2" = EPR2, "EPR 3" = EPR3),
  vcov = list(vcov1, vcov2, vcov3),
  statistic = "({std.error})",
  fmt = "%.2f",
  stars = c('^' = .1, '*' = .05, '**' = .01),
  coef_order = "traditional",
  output = "Table_B4.html"
)

#################################################################################################
### Table B5. IACW Conflict Conditionally Predicts Non-FS Conquests (Eurasian pseudo-regions) ###
#################################################################################################

## EPR1 ##

EPR1 <- lm(non_fs_conquest_dum ~ fs_dum:log(SUM_IAC_all+1) + 
             log(SUM_IAC_all+1) +
             fs_dum +
             log(SUM_Inter_state+1) +
             log(SUM_Intra_state+1) +
             pol_prop_pop +
             state_hist_log +
             log(mean_elevation+1) +
             log(mean_open_terrain+1) +
             warm_water_coast +
             core_latitude +
             as.factor(EPR1_ID) +
             as.factor(cent), 
           data=dynasties_polities_panel)

## EPR2 ##

EPR2 <- lm(non_fs_conquest_dum ~ fs_dum:log(SUM_IAC_all+1) + log(SUM_IAC_all+1) +
             fs_dum +
             log(SUM_Inter_state+1) +
             log(SUM_Intra_state+1) +
             pol_prop_pop +
             state_hist_log +
             log(mean_elevation+1) +
             log(mean_open_terrain+1) +
             warm_water_coast +
             core_latitude +
             as.factor(EPR2_ID) +
             as.factor(cent), 
           data=dynasties_polities_panel)

## EPR3 ##

EPR3 <- lm(non_fs_conquest_dum ~ fs_dum:log(SUM_IAC_all+1) + 
             log(SUM_IAC_all+1) +
             fs_dum +
             log(SUM_Inter_state+1) +
             log(SUM_Intra_state+1) +
             pol_prop_pop +
             state_hist_log +
             log(mean_elevation+1) +
             log(mean_open_terrain+1) +
             warm_water_coast +
             core_latitude +
             as.factor(EPR3_ID) +
             as.factor(cent), 
           data=dynasties_polities_panel)

# Robust SEs
vcov1 <- vcovHC(EPR1, type = "HC0", cluster = ~core_region + cent)
vcov2 <- vcovHC(EPR2, type = "HC0", cluster = ~core_region + cent)
vcov3 <- vcovHC(EPR3, type = "HC0", cluster = ~core_region + cent)

# Output
modelsummary(
  list("EPR 1" = EPR1, "EPR 2" = EPR2, "EPR 3" = EPR3),
  vcov = list(vcov1, vcov2, vcov3),
  statistic = "({std.error})",
  fmt = "%.2f",
  stars = c('^' = .1, '*' = .05, '**' = .01),
  coef_order = "traditional",
  output = "Table_B5.html"
)

#######################################################################
### Table B6. IACW Score Predicts FS Succession (Fixest Conley SEs) ###
#######################################################################

#IACW Score + FE
Conley1 <- feols(fs_dum ~ IACW_score | 
                   core_region + cent, data = dynasties_polities_panel, vcov_conley(
  lat = "core_latitude",
  lon = "core_longitude",
  cutoff = 2000,
  pixel = 0,
  distance = "spherical",
  ssc = NULL,
  vcov_fix = TRUE
))

#IACW Score + Warfare Vars + FE
Conley2 <- feols(fs_dum ~ IACW_score +
                       log(SUM_IAC_all+1) +
                       log(SUM_Inter_state+1) +
                       log(SUM_Intra_state+1) | 
                       core_region + cent, 
                       data = dynasties_polities_panel, 
                       vcov_conley(
                         lat = "core_latitude",
                         lon = "core_longitude",
                         cutoff = 2000,
                         pixel = 0,
                         distance = "spherical",
                         ssc = NULL,
                         vcov_fix = TRUE
                       ))

#IACW Score + Warfare Vars + Polity Vars + FE
Conley3 <- feols(fs_dum ~ IACW_score +
                       log(SUM_IAC_all+1) +
                       log(SUM_Inter_state+1) +
                       log(SUM_Intra_state+1) + 
                       pol_prop_pop +
                       state_hist_log +
                       log(mean_elevation+1) +
                       log(mean_open_terrain+1) +
                       warm_water_coast | 
                         core_region + cent, 
                       data = dynasties_polities_panel, 
                       vcov_conley(
                         lat = "core_latitude",
                         lon = "core_longitude",
                         cutoff = 2000,
                         pixel = 0,
                         distance = "spherical",
                         ssc = NULL,
                         vcov_fix = TRUE
                       ))


# Output
modelsummary(
  list("Model 1" = Conley1, "Model 2" = Conley2, "Model 3" = Conley3),
  statistic = "({std.error})",
  fmt = "%.2f",
  stars = c('^' = .1, '*' = .05, '**' = .01),
  coef_order = "traditional",
  output = "Table_B6.html"
)


###########################################################################################
### Table B7. IACW Conflict Conditionally Predicts Non-FS Conquests (Fixest Conley SEs) ###
###########################################################################################

#IACW Battles + FE
Conley1 <- feols(non_fs_conquest_dum ~ log(SUM_IAC_all+1) | 
                   core_region + cent, 
                 data = dynasties_polities_panel, 
                 vcov_conley(
                   lat = "core_latitude",
                   lon = "core_longitude",
                   cutoff = 2000,
                   pixel = 0,
                   distance = "spherical",
                   ssc = NULL,
                   vcov_fix = TRUE
                 ))

#IACW Battles + Warfare Vars + FE
Conley2 <- feols(non_fs_conquest_dum ~ log(SUM_IAC_all+1) +
                       log(SUM_Inter_state+1) +
                       log(SUM_Intra_state+1) | 
                   core_region + cent, 
                 data = dynasties_polities_panel, 
                 vcov_conley(
                   lat = "core_latitude",
                   lon = "core_longitude",
                   cutoff = 2000,
                   pixel = 0,
                   distance = "spherical",
                   ssc = NULL,
                   vcov_fix = TRUE
                 ))

#IACW Battles + Warfare Vars + Polity Vars + FE
Conley3 <- feols(non_fs_conquest_dum ~ log(SUM_IAC_all+1) +
                       log(SUM_Inter_state+1) +
                       log(SUM_Intra_state+1) +
                       pol_prop_pop +
                       state_hist_log +
                       log(mean_elevation+1) +
                       log(mean_open_terrain+1) +
                       warm_water_coast | 
                   core_region + cent, 
                 data = dynasties_polities_panel, 
                 vcov_conley(
                   lat = "core_latitude",
                   lon = "core_longitude",
                   cutoff = 2000,
                   pixel = 0,
                   distance = "spherical",
                   ssc = NULL,
                   vcov_fix = TRUE
                 ))

#IACW Battles + FS Dummy + Warfare Vars + Polity Vars + FE
Conley4 <- feols(non_fs_conquest_dum ~ log(SUM_IAC_all+1) +
                       fs_dum +
                       log(SUM_Inter_state+1) +
                       log(SUM_Intra_state+1) +
                       pol_prop_pop +
                       state_hist_log +
                       log(mean_elevation+1) +
                       log(mean_open_terrain+1) +
                       warm_water_coast | 
                   core_region + cent, 
                 data = dynasties_polities_panel, 
                 vcov_conley(
                   lat = "core_latitude",
                   lon = "core_longitude",
                   cutoff = 2000,
                   pixel = 0,
                   distance = "spherical",
                   ssc = NULL,
                   vcov_fix = TRUE
                 ))

#IACW Battles*FS Dummy Interaction + Warfare Vars + Polity Vars + FE
Conley5 <- feols(non_fs_conquest_dum ~ fs_dum:log(SUM_IAC_all+1) +
                       log(SUM_IAC_all+1) +
                       fs_dum +
                       log(SUM_Inter_state+1) +
                       log(SUM_Intra_state+1) +
                       pol_prop_pop +
                       state_hist_log +
                       log(mean_elevation+1) +
                       log(mean_open_terrain+1) +
                       warm_water_coast | 
                   core_region + cent, 
                 data = dynasties_polities_panel, 
                 vcov_conley(
                   lat = "core_latitude",
                   lon = "core_longitude",
                   cutoff = 2000,
                   pixel = 0,
                   distance = "spherical",
                   ssc = NULL,
                   vcov_fix = TRUE
                 ))

# Output
modelsummary(
  list("Model 1" = Conley1, "Model 2" = Conley2, "Model 3" = Conley3, "Model 4" = Conley4, "Model 5" = Conley5),
  statistic = "({std.error})",
  fmt = "%.2f",
  stars = c('^' = .1, '*' = .05, '**' = .01),
  coef_order = "traditional",
  output = "Table_B7.html"
)
