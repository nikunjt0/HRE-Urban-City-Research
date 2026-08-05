
********************************************************************************
********************************************************************************
***** Replication dofile for "Blood is Thicker than Water:                 *****
***** Family Size and Leader Deposition in Medieval and                    *****
***** Early Modern Europe"                                                 *****
***** Andrej Kokkonen, Jørgen Møller, Suthan Krishnarajan & Anders Sundell *****
********************************************************************************
********************************************************************************

* Install extra commands
ssc install coefplot, replace

* Set directory
cd "/Users/xsunde/Dropbox/War and state building/Replication package/"

use bloodisthicker_data, clear

**** Set font ****
graph set window fontface "CMU Serif"
graph set window fontfacemono "CMU Serif"
graph set window fontfacesans "CMU Serif"
graph set window fontfaceserif "CMU Serif"

* Create additional variables age and tenure variables
gen age2 = age_imputed^2
gen age3 = age_imputed^3

gen tenure2 = tenure_rolling^2
gen tenure3 = tenure_rolling^3

gen spouse_age2 = spouse_age^2
gen spouse_age3 = spouse_age^3

gen ageatdeath = death-birth

* Create dependent variables multiplied by 100
gen deposed_100 = deposed_our*100
gen waronset_civil_100 = waronset_civil_*100
gen naturaldeath_100 = naturaldeath*100

* Create additional family variables
gen malerelatives = children_sons + siblings_brothers + parsib_uncles
gen femalerelatives = children_daughters + siblings_sisters + parsib_aunts

label variable malerelatives "Male relatives"
label variable femalerelatives "Female relatives"

********************************************************************************
******************************** Figure 1 **************************************
********************************************************************************

twoway  (lpoly children_born age_imputed, lcolor(gray)) ///
		(lpoly children_death age_imputed, lcolor(black)) ///
		, scheme(s1mono) plotregion(lwidth(none) margin(zero)) legend(off) ///
		xtitle("Age of monarch", size(large)) ylabel(, labsize(large) angle(horizontal)) ///
		xlabel(, labsize(large)) title(" ", size(large)) ///
		text(0.17 40 "Child born", size(medium) placement(3)) ///
		text(0.05 40 "Child died", size(medium) placement(3))
		
graph export "Output/fig1b.tif", replace

********************************************************************************
******************************** Figure 2 **************************************
********************************************************************************
* Preserves, collapses data to produce the graphs, then restores.

preserve
gen roundage = round(age_imputed)
collapse (mean) children_all children_sons children_daughters children_born children_death siblings_all siblings_brothers siblings_sisters siblings_born siblings_death parsib_all parsib_uncles parsib_aunts, by(roundage)

twoway  (line children_all children_sons children_daughters roundage, lcolor("100 100 100" navy pink)) ///
		, scheme(s1mono) plotregion(lwidth(none) margin(zero)) legend(off) ///
		xtitle("Age of monarch", size(large)) ylabel(0(1)5, labsize(large) angle(horizontal)) ///
		xlabel(, labsize(large)) ///
		text(3.8 45 "All children", size(large) placement(0)) ///
		text(1.9 45 "Sons", size(large) placement(0)) ///
		text(0.8 45 "Daughters", size(large) placement(0)) ///
		name(children, replace) aspect(1)

twoway  (line siblings_all siblings_brothers siblings_sisters roundage, lcolor("100 100 100" navy pink)) ///
		, scheme(s1mono) plotregion(lwidth(none) margin(zero)) legend(off) ///
		xtitle("Age of monarch", size(large)) ylabel(0(1)5, labsize(large) angle(horizontal)) ///
		xlabel(, labsize(large)) ///
		text(2.4 40 "All siblings", size(large) placement(0)) ///
		text(0.6 40 "Brothers", size(large) placement(0)) ///
		text(1.4 40 "Sisters", size(large) placement(0)) ///
		name(siblings, replace) aspect(1)

twoway  (line parsib_all parsib_uncles parsib_aunts roundage, lcolor("100 100 100" navy pink)) ///
		, scheme(s1mono) plotregion(lwidth(none) margin(zero)) legend(off) ///
		xtitle("Age of monarch", size(large)) ylabel(0(1)5, labsize(large) angle(horizontal)) ///
		xlabel(, labsize(large)) ///
		text(1.8 6 "All father's siblings", size(large) placement(3)) ///
		text(0.35 6 "Uncles", size(large) placement(3)) ///
		text(1 6 "Aunts", size(large) placement(3)) ///
		name(parsibs, replace) aspect(1)

graph combine children siblings parsibs, scheme(s1mono) rows(1) xsize(6) ysize(2.5)
graph export "Output/fig2.tif", replace

restore

********************************************************************************
******************************** Figure 3 **************************************
********************************************************************************

reg deposed_our i.children_all_cap
margins, at(children_all_cap=(0/8))
matrix a1 = r(table)

tab children_all_cap, matcell(b1)

reg deposed_our i.siblings_all_cap
margins, at(siblings_all_cap=(0/8))
matrix a2 = r(table)

tab siblings_all_cap, matcell(b2)

gen graph_nr = .
gen graph_childcoef = .
gen graph_siblingcoef = .
gen graph_childn = .
gen graph_siblingn = .
forvalues g = 1/9 {
replace graph_nr = `g'-1 in `g'
replace graph_childcoef = a1[1, `g'] in `g'
replace graph_siblingcoef = a2[1, `g'] in `g'
replace graph_childn = b1[`g', 1] in `g'
replace graph_siblingn = b2[`g', 1] in `g'
}

sum graph_childn
gen graph_childweight = sqrt(graph_childn/150)

sum graph_siblingn
gen graph_siblingweight = sqrt(graph_siblingn/150)

replace graph_childcoef=graph_childcoef*100
replace graph_siblingcoef=graph_siblingcoef*100

format %9.1f graph_childcoef graph_siblingcoef

forvalues l = 0/8 {
local l2 = `l'+1
local w = graph_childweight in `l2'
local string1 = "`string1'" + "(scatter graph_childcoef graph_nr if graph_nr==`l', msymbol(circle) mcolor(black) msize(*`w'))"
}
twoway  `string1' ///
		, legend(off) scheme(s1mono) plotregion(lwidth(none)) aspect(1) ///
		ylabel(0(0.5)2.5, labsize(vlarge) angle(horizontal)) ///
		xlabel(0/8, labsize(vlarge)) xscale(range(-1 8)) ///
		xtitle("Children", size(vlarge)) ytitle("Deposed", size(vlarge)) name(childrendeposed, replace)

forvalues l = 0/8 {
local l2 = `l'+1
local w = graph_siblingweight in `l2'
local string2 = "`string2'" + "(scatter graph_siblingcoef graph_nr if graph_nr==`l', msymbol(circle) mcolor(black) msize(*`w'))"
}		
twoway  `string2' ///
		, legend(off) scheme(s1mono) plotregion(lwidth(none)) aspect(1) ///
		ylabel(0(0.5)2.5, labsize(vlarge) angle(horizontal)) ///
		xlabel(0/8, labsize(vlarge)) xscale(range(-1 8)) ///
		xtitle("Siblings", size(vlarge)) ytitle("Deposed", size(vlarge)) name(siblingdeposed, replace)		

graph combine childrendeposed siblingdeposed, scheme(s1mono) xsize(4) ysize(2)
graph export "Output/fig3.tif", replace
drop graph_nr graph_childcoef graph_siblingcoef graph_childn graph_siblingn graph_childweight graph_siblingweight

********************************************************************************
********************************* Table 2 **************************************
********************************************************************************
global controls "monarch_queen married primogeniture dum_illeg dum_zanden age_imputed age2 age3 tenure_rolling tenure2 tenure3 i.century i.id_country"

reg deposed_100 family_all $controls if dum_interregnum==0, cluster(id_monarch)
eststo m1
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

reg deposed_100 children_all siblings_all parsib_all $controls if dum_interregnum==0, cluster(id_monarch)
eststo m2
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

reg deposed_100 children_sons children_daughters siblings_brothers siblings_sisters parsib_uncles parsib_aunts $controls if dum_interregnum==0, cluster(id_monarch)
eststo m3
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

esttab m1 m2 m3 using "Output/table3.tex", style(tex) nogap replace t label b(3) star(* 0.05 ** 0.01 *** 0.001) ///
stats(N age tenure country century r2_a, fmt(0 0 0 0 0 3) labels("N" "Age controls:" "Tenure controls:" "Century fixed effects:" "Country fixed effects:" "R2(adj):")) ///
title() noomitted eqlabels(none) compress nodep drop(age_imputed age2 age3 tenure_rolling tenure2 tenure3 *.id_country *.century) ///
order(family_all children_all siblings_all parsib_all children_sons children_daughters siblings_brothers siblings_sisters parsib_uncles parsib_aunts) nomtitles

********************************************************************************
******************************** Figure 4 **************************************
********************************************************************************
* Run Table 3 analysis first *

coefplot m1 m2 m3, keep(family_all children_all siblings_all parsib_all ///
children_sons children_daughters siblings_brothers siblings_sisters parsib_uncles parsib_aunts) offset(0) ///
legend(off) scheme(s1mono) plotregion(lwidth(none))  msymbol(circle) mcolor(black) ciopts(color(black black)) ///
xline(0, lcolor(red) lpattern(dash)) xlabel(, labsize(small)) grid(none) ///
levels(95 90) ///
groups(family_all = "Model 1" children_all siblings_all parsib_all = "Model 2" ///
children_sons children_daughters siblings_brothers siblings_sisters parsib_uncles parsib_aunts = "Model 3", labsize(medium)) ///
aspect(2)

graph export "Output/fig4.tif", replace


********************************************************************************
******************************** Figure 5 **************************************
********************************************************************************

global controls "monarch_queen married primogeniture dum_illeg dum_zanden age_imputed age2 age3 tenure_rolling tenure2 tenure3 i.century i.id_country"
reg deposed_100 i.family_all $controls if dum_interregnum==0, cluster(id_monarch)
margins, at(family_all=(0(1)10)) atmeans
marginsplot, recastci(rarea) ci1opts(color(gray%75) lwidth(none)) recast(line) plot1opts(color(black)) yline(0, lpattern(dash) lcolor(red)) ///
title(" ") ytitle("Estimated annual deposition-risk", size(medium)) ylabel(0(1)4, labsize(small) angle(horizontal)) ///
xlabel(, labsize(small)) xtitle("Number of living family members", size(medium)) scheme(s1mono) ///
plotregion(lwidth(none)) name(flexible_living, replace)

graph export "Output/fig5.tif", replace


********************************************************************************
******************************** Figure 6 **************************************
********************************************************************************

global controls2 "monarch_queen married primogeniture dum_illegitimate dum_zanden age_imputed age2 age3 tenure_rolling tenure2 tenure3 i.century"
mlogit deposedcat_perp family_all $controls2 if dum_interregnum==0, cluster(id_monarch)
eststo ml1
estadd local controls "Yes"
estadd local country "No"
estadd local century "Yes"

mlogit deposedcat_perp children_all siblings_all parsib_all $controls2 if dum_interregnum==0, cluster(id_monarch)
eststo ml2
estadd local controls "Yes"
estadd local country "No"
estadd local century "Yes"

mlogit deposedcat_perp malerelatives femalerelatives $controls2 if dum_interregnum==0, cluster(id_monarch)
eststo ml3
estadd local controls "Yes"
estadd local country "No"
estadd local century "Yes"

mlogit deposedcat_perp children_sons children_daughters siblings_brothers siblings_sisters parsib_uncles parsib_aunts $controls2 if dum_interregnum==0, cluster(id_monarch)
eststo ml4
estadd local controls "Yes"
estadd local country "No"
estadd local century "Yes"

esttab ml1 ml2 ml3  ml4, unstack nogap replace t label b(3) star(* 0.05 ** 0.01 *** 0.001) ///
stats(N controls country century r2_p, fmt(0 0 0 3) labels("N" "Controls" "Century fixed effects:" "Pseudo R2")) ///) ///
title() noomitted eqlabels(none) compress nodep drop(age_imputed age2 age3 tenure_rolling tenure2 tenure3 *.century) ///
order(family_all children_all siblings_all parsib_all malerelatives femalerelatives children_sons children_daughters siblings_brothers siblings_sisters parsib_uncles parsib_aunts) ///
mtitles("Family" "Family" "Family" "Family" "Family")


estimates restore ml1
margins, dydx(family_all) predict(outcome(1)) predict(outcome(2)) post
estimates store marg1

estimates restore ml2
margins, dydx(children_all siblings_all parsib_all) predict(outcome(1)) predict(outcome(2)) post
estimates store marg2

estimates restore ml3
margins, dydx(malerelatives femalerelatives) predict(outcome(1)) predict(outcome(2)) post
estimates store marg3

estimates restore ml4
margins, dydx(children_sons children_daughters siblings_brothers siblings_sisters parsib_uncles parsib_aunts) predict(outcome(1)) predict(outcome(2)) post
estimates store marg4

coefplot(marg1, keep(family_all:1._predict) label("Family") mcolor(gs11) msymbol(circle) ciopts(lcolor(gs11 gs11)) msize(small) offset(-0.1)) ///
 (marg1, keep(family_all:2._predict) label("Other") mcolor(black) msize(small)  offset(0.1)) ///
 (marg2, keep(children_all:1._predict) label(" ") nokey mcolor(gs11) msymbol(circle) ciopts(lcolor(gs11 gs11)) msize(small) offset(-0.1)) ///
 (marg2, keep(children_all:2._predict) label(" ") nokey mcolor(black) msize(small)  offset(0.1))  ///
  (marg2, keep(siblings_all:1._predict) label(" ") nokey mcolor(gs11) msymbol(circle) ciopts(lcolor(gs11 gs11)) msize(small)  offset(-0.1)) ///
 (marg2, keep(siblings_all:2._predict) label(" ") nokey mcolor(black) msize(small)  offset(0.1))  ///
  (marg2, keep(parsib_all:1._predict) label(" ") nokey mcolor(gs11) msymbol(circle) ciopts(lcolor(gs11 gs11)) msize(small) offset(-0.1)) ///
 (marg2, keep(parsib_all:2._predict) label(" ") nokey mcolor(black) msize(small)  offset(0.1))  ///
  (marg3, keep(malerelatives:1._predict) label(" ") nokey mcolor(gs11) msymbol(circle) ciopts(lcolor(gs11 gs11)) msize(small) offset(-0.1)) ///
 (marg3, keep(malerelatives:2._predict) label(" ") nokey mcolor(black) msize(small)  offset(0.1))  ///
  (marg3, keep(femalerelatives:1._predict) label(" ") nokey mcolor(gs11) msymbol(circle) ciopts(lcolor(gs11 gs11)) msize(small) offset(-0.1)) ///
 (marg3, keep(femalerelatives:2._predict) label(" ") nokey mcolor(black) msize(small)  offset(0.1))  ///
 (marg4, keep(children_sons:1._predict) 		label(" ") nokey mcolor(gs11) msymbol(circle) ciopts(lcolor(gs11 gs11)) msize(small) offset(-0.1))   ///
 (marg4, keep(children_sons:2._predict)			label(" ") nokey mcolor(black) msize(small)  offset(0.1))   ///
 (marg4, keep(children_daughters:1._predict) 	label(" ") nokey mcolor(gs11) msymbol(circle) ciopts(lcolor(gs11 gs11)) msize(small) offset(-0.1)) ///
 (marg4, keep(children_daughters:2._predict) 	label(" ") nokey mcolor(black) msize(small) offset(0.1))   ///
 (marg4, keep(siblings_brothers:1._predict) 	label(" ") nokey mcolor(gs11) msymbol(circle) ciopts(lcolor(gs11 gs11)) msize(small) offset(-0.1)) ///
 (marg4, keep(siblings_brothers:2._predict) 	label(" ") nokey mcolor(black) msize(small) offset(0.1))   ///
 (marg4, keep(siblings_sisters:1._predict) 		label(" ") nokey mcolor(gs11) msymbol(circle) ciopts(lcolor(gs11 gs11)) msize(small) offset(-0.1)) ///
 (marg4, keep(siblings_sisters:2._predict) 		label(" ") nokey mcolor(black) msize(small) offset(0.1))   ///
 (marg4, keep(parsib_uncles:1._predict) 		label(" ") nokey mcolor(gs11) msymbol(circle) ciopts(lcolor(gs11 gs11)) msize(small) offset(-0.1)) ///
 (marg4, keep(parsib_uncles:2._predict) 		label(" ") nokey mcolor(black) msize(small) offset(0.1))   ///
 (marg4, keep(parsib_aunts:1._predict) 			label(" ") nokey mcolor(gs11) msymbol(circle) ciopts(lcolor(gs11 gs11)) msize(small) offset(-0.1)) ///
 (marg4, keep(parsib_aunts:2._predict) 			label(" ") nokey mcolor(black)  msize(small) offset(0.1))   ///
 , swapnames xline(0, lpattern(dash) lcolor(red)) legend(rows(1))  scheme(s1mono) plotregion(lwidth(none)) ///
msymbol(circle) ciopts(color(black black)) legend(off) ///
level(95 90) aspect(2) ///
xlabel(-0.01 "-1" -0.005 "-0.5" 0 "0" 0.005 "0.5", labsize(small)) ylabel(, labsize(small)) grid(none) ///
groups(family_all = "Model 1" children_all siblings_all parsib_all = "Model 2" ///
malerelatives femalerelatives = "Model 3" ///
children_sons children_daughters siblings_brothers siblings_sisters parsib_uncles parsib_aunts = "Model 4", labsize(small))

graph export "Output/fig6.tif", replace

********************************************************************************
********************************************************************************
************ Replication dofile for Online appendix ****************************
********************************************************************************
********************************************************************************

********************************************************************************
******************************** Appendix 1.1 **********************************
********************************************************************************

table country, contents(min year max year)

********************************************************************************
******************************** Appendix 1.2 **********************************
********************************************************************************
* Preserves, collapses data to produce the graph, then restores.

preserve
gen roundage = round(age_imputed)
collapse (mean) married, by(roundage)

twoway  (line married roundage, lcolor(black)) ///
		, scheme(s1mono) plotregion(lwidth(none) margin(zero)) legend(off) ///
		xtitle("Age of monarch", size(small)) ylabel(0(0.1)1, labsize(small) angle(horizontal)) ///
		xlabel(, labsize(small)) ytitle(" ") ///
		name(married, replace)

graph export "Output/appendix_figA1.pdf", replace		
restore


********************************************************************************
******************************** Appendix 2.1 **********************************
********************************************************************************
global controls "monarch_queen married primogeniture dum_illeg dum_zanden age_imputed age2 age3 tenure_rolling tenure2 tenure3 i.id_country i.century"

reg waronset_civil_100 family_all $controls if dum_interregnum==0, cluster(id_monarch)
eststo c1
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

reg waronset_civil_100 children_all siblings_all parsib_all $controls if dum_interregnum==0, cluster(id_monarch)
eststo c2
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

reg waronset_civil_100 children_sons children_daughters siblings_brothers siblings_sisters parsib_uncles parsib_aunts $controls if dum_interregnum==0, cluster(id_monarch)
eststo c3
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

esttab c1 c2 c3 using "Output/appendix_tableA2.tex", style(tex) nogap replace t label b(3) star(* 0.05 ** 0.01 *** 0.001) ///
stats(N age tenure country century r2_a, fmt(0 0 0 0 0 3) labels("N" "Age controls:" "Tenure controls:" "Century fixed effects:" "Country fixed effects:" "R2(adj):")) ///
title() noomitted eqlabels(none) compress nodep drop(age_imputed age2 age3 tenure_rolling tenure2 tenure3 *.id_country *.century) ///
order(family_all children_all siblings_all parsib_all children_sons children_daughters siblings_brothers siblings_sisters parsib_uncles parsib_aunts) nomtitles


********************************************************************************
******************************** Appendix 2.2 **********************************
********************************************************************************
global controls "monarch_queen married primogeniture dum_illeg dum_zanden age_imputed age2 age3 tenure_rolling tenure2 tenure3 i.id_country i.century"

logit deposed_our family_all $controls if dum_interregnum==0, cluster(id_monarch)
eststo m1
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

logit deposed_our children_all siblings_all parsib_all $controls if dum_interregnum==0, cluster(id_monarch)
eststo m2
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

logit deposed_our children_sons children_daughters siblings_brothers siblings_sisters parsib_uncles parsib_aunts $controls if dum_interregnum==0, cluster(id_monarch)
eststo m3
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

esttab m1 m2 m3 using "Output/appendix_tableA3.tex", style(tex) nogap replace t label b(3) star(* 0.05 ** 0.01 *** 0.001) ///
stats(N age tenure country century r2_p, fmt(0 0 0 0 0 3) labels("N" "Age controls:" "Tenure controls:" "Century fixed effects:" "Country fixed effects:" "Pseudo R2")) ///
title() noomitted eqlabels(none) compress nodep drop(age_imputed age2 age3 tenure_rolling tenure2 tenure3 *.id_country *.century) ///
order(family_all children_all siblings_all parsib_all children_sons children_daughters siblings_brothers siblings_sisters parsib_uncles parsib_aunts) nomtitles


********************************************************************************
******************************** Appendix 2.3 **********************************
********************************************************************************
gen testtime = tenure_rolling+1

stset testtime, id(id_reign) failure(deposed_our)

global survivalcontrols "monarch_queen married primogeniture dum_illeg dum_zanden age_imputed age2 age3 i.id_country i.century"

stcox family_all $survivalcontrols if dum_interregnum==0
eststo m1
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"

stcox  children_all siblings_all parsib_all $survivalcontrols if dum_interregnum==0
eststo m2
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"

stcox children_sons children_daughters siblings_brothers siblings_sisters parsib_uncles parsib_aunts $survivalcontrols if dum_interregnum==0
eststo m3
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"

esttab m1 m2 m3 using "Output/appendix_tableA4.tex", style(tex) nogap replace t label b(3) star(* 0.05 ** 0.01 *** 0.001) ///
stats(N age country century, fmt(0 0 0 0) labels("N" "Age controls:" "Country fixed effects:" "Century fixed effects:")) ///
title() noomitted eqlabels(none) compress nodep drop(age_imputed age2 age3 *.id_country *.century) ///
order(family_all children_all siblings_all parsib_all children_sons children_daughters siblings_brothers siblings_sisters parsib_uncles parsib_aunts) nomtitles

********************************************************************************
******************************** Appendix 2.4 **********************************
********************************************************************************
global cc_controls "monarch_queen married primogeniture dum_illeg dum_zanden age_imputed age2 age3 tenure_rolling tenure2 tenure3 i.countrycentury"

reg deposed_100 family_all $cc_controls if dum_interregnum==0, cluster(id_monarch)
eststo cc1
estadd local countrycentury "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

reg deposed_100 children_all siblings_all $cc_controls if dum_interregnum==0, cluster(id_monarch)
eststo cc2
estadd local countrycentury "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

reg deposed_100 children_sons children_daughters siblings_brothers siblings_sisters parsib_uncles parsib_aunts $cc_controls if dum_interregnum==0, cluster(id_monarch)
eststo cc3
estadd local countrycentury "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

esttab cc1 cc2 cc3 using "Output/appendix_tableA5.tex", style(tex) nogap replace t label b(3) star(* 0.05 ** 0.01 *** 0.001) ///
stats(N age tenure countrycentury r2_a, fmt(0 0 0 0 3) labels("N" "Age controls:" "Tenure controls:" "Country-century fixed effects:" "R2(adj):")) ///
title() noomitted eqlabels(none) compress nodep drop(age_imputed age2 age3 tenure_rolling tenure2 tenure3 *.countrycentury) ///
order(family_all children_all siblings_all parsib_all children_sons children_daughters siblings_brothers siblings_sisters parsib_uncles parsib_aunts) nomtitles


********************************************************************************
******************************** Appendix 2.5 **********************************
********************************************************************************
global controls "monarch_queen married primogeniture dum_illeg dum_zanden age_imputed age2 age3 tenure_rolling tenure2 tenure3 i.id_country i.century"
reg deposed_100 c.family_all##c.family_all $controls if dum_interregnum==0, cluster(id_monarch)
eststo m1
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

esttab m1 using "Output/appendix_tableA6.tex", style(tex) nogap replace t label b(3) star(* 0.05 ** 0.01 *** 0.001) ///
stats(N age tenure country century r2_a, fmt(0 0 0 0 0 3) labels("N" "Age controls:" "Tenure controls:" "Century fixed effects:" "Country fixed effects:" "R2(adj):")) ///
title() noomitted eqlabels(none) compress nodep drop(*.id_country *.century age_imputed age2 age3 tenure_rolling tenure2 tenure3) ///
order(family_all) nomtitles

********************************************************************************
******************************** Appendix 2.6 **********************************
********************************************************************************

* Only with country and century FE *
global controls2 "i.id_country i.century"
reg deposed_100 family_all $controls2 if dum_interregnum==0, cluster(id_monarch)
eststo m1
estadd local country "Yes"
estadd local century "Yes"
estadd local age "No"
estadd local tenure "No"

reg deposed_100 children_all siblings_all parsib_all $controls2 if dum_interregnum==0, cluster(id_monarch)
eststo m2
estadd local country "Yes"
estadd local century "Yes"
estadd local age "No"
estadd local tenure "No"

reg deposed_100 children_sons children_daughters siblings_brothers siblings_sisters parsib_uncles parsib_aunts $controls2 if dum_interregnum==0, cluster(id_monarch)
eststo m3
estadd local country "Yes"
estadd local century "Yes"
estadd local age "No"
estadd local tenure "No"

* Without country and century FE *
reg deposed_100 family_all if dum_interregnum==0, cluster(id_monarch)
eststo m4
estadd local country "No"
estadd local century "No"
estadd local age "No"
estadd local tenure "No"

reg deposed_100 children_all siblings_all parsib_all if dum_interregnum==0, cluster(id_monarch)
eststo m5
estadd local country "No"
estadd local century "No"
estadd local age "No"
estadd local tenure "No"

reg deposed_100 children_sons children_daughters siblings_brothers siblings_sisters parsib_uncles parsib_aunts if dum_interregnum==0, cluster(id_monarch)
eststo m6
estadd local country "No"
estadd local century "No"
estadd local age "No"
estadd local tenure "No"

esttab m1 m2 m3 m4 m5 m6 using "Output/appendix_tableA7.tex", style(tex) nogap replace t label b(3) star(* 0.05 ** 0.01 *** 0.001) ///
stats(N age tenure country century r2_a, fmt(0 0 0 0 0 3) labels("N" "Age controls:" "Tenure controls:" "Century fixed effects:" "Country fixed effects:" "R2(adj):")) ///
title() noomitted eqlabels(none) compress nodep drop(*.id_country *.century) ///
order(family_all children_all siblings_all parsib_all children_sons children_daughters siblings_brothers siblings_sisters parsib_uncles parsib_aunts) nomtitles


********************************************************************************
******************************** Appendix 2.7 **********************************
********************************************************************************

global controls2 "monarch_queen married primogeniture dum_illegitimate dum_zanden age_imputed age2 age3 tenure_rolling tenure2 tenure3 i.century"
mlogit deposedcat_perp family_all $controls2 if dum_interregnum==0, cluster(id_monarch)
eststo ml1
estadd local controls "Yes"
estadd local country "No"
estadd local century "Yes"

mlogit deposedcat_perp children_all siblings_all parsib_all $controls2 if dum_interregnum==0, cluster(id_monarch)
eststo ml2
estadd local controls "Yes"
estadd local country "No"
estadd local century "Yes"

mlogit deposedcat_perp malerelatives femalerelatives $controls2 if dum_interregnum==0, cluster(id_monarch)
eststo ml3
estadd local controls "Yes"
estadd local country "No"
estadd local century "Yes"

mlogit deposedcat_perp children_sons children_daughters siblings_brothers siblings_sisters parsib_uncles parsib_aunts $controls2 if dum_interregnum==0, cluster(id_monarch)
eststo ml4
estadd local controls "Yes"
estadd local country "No"
estadd local century "Yes"

esttab ml1 ml2 ml3 ml4 using "Output/appendix_tableA8.tex", style(tex) unstack nogap replace t label b(3) star(* 0.05 ** 0.01 *** 0.001) ///
stats(N controls country century r2_p, fmt(0 0 0 3) labels("N" "Controls" "Century fixed effects:" "Pseudo R2")) ///) ///
title() noomitted eqlabels(none) compress nodep drop(age_imputed age2 age3 tenure_rolling tenure2 tenure3 *.century) ///
order(family_all children_all siblings_all parsib_all malerelatives femalerelatives children_sons children_daughters siblings_brothers siblings_sisters parsib_uncles parsib_aunts) ///
mtitles("Family" "Family" "Family" "Family" "Family")


********************************************************************************
******************************** Appendix 3.1 **********************************
********************************************************************************
global controls "monarch_queen married primogeniture dum_illeg dum_zanden age_imputed age2 age3 tenure_rolling tenure2 tenure3 i.id_country i.century"

label variable waryear_civil_ "Ongoing civil war"

reg children_born $controls ln_area if dum_interregnum==0, cluster(id_monarch)
estimates store fert1
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

reg children_born waryear_civil_ ln_area $controls if dum_interregnum==0, cluster(id_monarch)
estimates store fert2
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

reg children_born ln_area spouse_age spouse_age2 spouse_age3 $controls if dum_interregnum==0, cluster(id_monarch)
estimates store fert3
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

esttab fert1 fert2 fert3 using "Output/appendix_tableA9.tex", style(tex)  nogap replace t label b(3) star(* 0.05 ** 0.01 *** 0.001) ///
stats(N age tenure century country  r2_a, fmt(0 0 0 0 0 3) labels("N" "Age controls:" "Tenure controls:" "Century fixed effects:" "Country fixed effects:" "R2(adj)")) ///
title() noomitted eqlabels(none) compress nodep drop(age_imputed age2 age3 tenure_rolling tenure2 tenure3 *.id_country *.century) ///
order(waryear_civil_) nomtitles

********************************************************************************
******************************** Appendix 3.2 **********************************
********************************************************************************
global controls "monarch_queen married primogeniture dum_illeg dum_zanden age_imputed age2 age3 tenure_rolling tenure2 tenure3 i.id_country i.century"

reg naturaldeath_100 family_all $controls if dum_interregnum==0, cluster(id_monarch)
eststo m1
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

reg naturaldeath_100 children_all siblings_all parsib_all $controls if dum_interregnum==0, cluster(id_monarch)
eststo m2
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

reg naturaldeath_100 children_sons children_daughters siblings_brothers siblings_sisters parsib_uncles parsib_aunts $controls if dum_interregnum==0, cluster(id_monarch)
eststo m3
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

esttab m1 m2 m3 using "Output/appendix_tableA10.tex", style(tex) nogap replace t label b(3) star(* 0.05 ** 0.01 *** 0.001) ///
stats(N age tenure country century r2_a, fmt(0 0 0 0 0 3) labels("N" "Age controls:" "Tenure controls:" "Century fixed effects:" "Country fixed effects:" "R2(adj):")) ///
title() noomitted eqlabels(none) compress nodep drop(age_imputed age2 age3 tenure_rolling tenure2 tenure3 *.id_country *.century) ///
order(family_all children_all siblings_all parsib_all children_sons children_daughters siblings_brothers siblings_sisters parsib_uncles parsib_aunts) nomtitles

********************************************************************************
******************************** Appendix 3.3 **********************************
********************************************************************************
global splitcontrols "monarch_queen married primogeniture dum_illeg dum_zanden age_imputed age2 age3 tenure_rolling tenure2 tenure3 i.century"

**** SPLIT SAMPLE ****
reg deposed_100 family_all $splitcontrols if dum_interregnum==0, cluster(id_monarch)
eststo m1
estadd local country "No"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

reg deposed_100 family_all $splitcontrols if dum_interregnum==0 & ageatdeath>=65 & ageatdeath<., cluster(id_monarch)
eststo m2
estadd local country "No"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

reg deposed_100 family_all $splitcontrols  if dum_interregnum==0 & ageatdeath<47, cluster(id_monarch)
eststo m3
estadd local country "No"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"


esttab m1 m2 m3 using "Output/appendix_tableA11.tex", style(tex) nogap replace t label b(3) star(* 0.05 ** 0.01 *** 0.001) ///
stats(N age tenure country century r2_a, fmt(0 0 0 0 0 3) labels("N" "Age controls:" "Tenure controls:" "Century fixed effects:" "Country fixed effects:" "R2(adj):")) ///
title() noomitted eqlabels(none) compress nodep drop(age_imputed age2 age3 tenure_rolling tenure2 tenure3 *.century) ///
order(family_all) mtitles("Full sample" "Died old (65+)" "Died young (<47)")


********************************************************************************
******************************** Appendix 3.4 **********************************
********************************************************************************

xtset id_reign year

gen family_death = children_death + siblings_death + parsib_death

gen lag = .
gen average_childrendeath = .
gen average_siblingsdeath = .
gen average_parsibdeath = .
gen average_familydeath = .

gen average_children = .
gen average_siblings = .
gen average_parsib = .
gen average_family = .

local counter = 1
forvalues l = 10(-1)0 {
sum children_death if f`l'.deposed_our==1
replace average_childrendeath = r(mean) in `counter'

sum siblings_death if f`l'.deposed_our==1
replace average_siblingsdeath = r(mean) in `counter'

sum parsib_death if f`l'.deposed_our==1
replace average_parsibdeath = r(mean) in `counter'

sum family_death if f`l'.deposed_our==1
replace average_familydeath = r(mean) in `counter'

sum children_all if f`l'.deposed_our==1
replace average_children = r(mean) in `counter'

sum siblings_all if f`l'.deposed_our==1
replace average_siblings = r(mean) in `counter'

sum parsib_all if f`l'.deposed_our==1
replace average_parsib = r(mean) in `counter'

sum family_all if f`l'.deposed_our==1
replace average_family = r(mean) in `counter'

replace lag = `l' in `counter'
local counter = `counter'+1

}

replace lag = lag*-1



twoway  (scatter average_familydeath lag, msymbol(circle) mcolor(navy) msize(medium)) ///
		, aspect(1) plotregion(lwidth(none)) scheme(s1mono) ylabel(0(0.05)0.15, labsize(small) angle(horizontal)) ///
		xlabel(-10(2)0, labsize(small)) xline(0, lpattern(dash) lcolor(red)) ///
		xtitle("Years before deposition", size(small)) ytitle("Average family death", size(small)) name(familydeath, replace)
		
twoway  (scatter average_childrendeath lag, msymbol(circle) mcolor(navy) msize(medium)) ///
		, aspect(1) plotregion(lwidth(none)) scheme(s1mono) ylabel(0(0.05)0.15, labsize(small) angle(horizontal)) ///
		xlabel(-10(2)0, labsize(small)) xline(0, lpattern(dash) lcolor(red)) ///
		xtitle("Years before deposition", size(small)) ytitle("Average children death", size(small)) name(childrendeath, replace)
		
twoway  (scatter average_siblingsdeath lag, msymbol(circle) mcolor(navy) msize(medium)) ///
		, aspect(1) plotregion(lwidth(none)) scheme(s1mono) ylabel(0(0.05)0.15, labsize(small) angle(horizontal)) ///
		xlabel(-10(2)0, labsize(small)) xline(0, lpattern(dash) lcolor(red)) ///
		xtitle("Years before deposition", size(small)) ytitle("Average siblings death", size(small)) name(siblingsdeath, replace)		

twoway  (scatter average_parsibdeath lag, msymbol(circle) mcolor(navy) msize(medium)) ///
		, aspect(1) plotregion(lwidth(none)) scheme(s1mono) ylabel(0(0.05)0.15, labsize(small) angle(horizontal)) ///
		xlabel(-10(2)0, labsize(small)) xline(0, lpattern(dash) lcolor(red)) ///
		xtitle("Years before deposition", size(small)) ytitle("Average uncles and aunts death", size(small)) name(parsibdeath, replace)		

		
twoway  (scatter average_family lag, msymbol(circle) mcolor(navy) msize(medium)) ///
		, aspect(1) plotregion(lwidth(none)) scheme(s1mono) ylabel(0(0.5)3, labsize(small) angle(horizontal)) ///
		xlabel(-10(2)0, labsize(small)) xline(0, lpattern(dash) lcolor(red)) ///
		xtitle("Years before deposition", size(small)) ytitle("Average family", size(small)) name(family, replace)
		
twoway  (scatter average_children lag, msymbol(circle) mcolor(navy) msize(medium)) ///
		, aspect(1) plotregion(lwidth(none)) scheme(s1mono) ylabel(0(0.5)3, labsize(small) angle(horizontal)) ///
		xlabel(-10(2)0, labsize(small)) xline(0, lpattern(dash) lcolor(red)) ///
		xtitle("Years before deposition", size(small)) ytitle("Average children", size(small)) name(children, replace)
		
twoway  (scatter average_siblings lag, msymbol(circle) mcolor(navy) msize(medium)) ///
		, aspect(1) plotregion(lwidth(none)) scheme(s1mono) ylabel(0(0.5)3, labsize(small) angle(horizontal)) ///
		xlabel(-10(2)0, labsize(small)) xline(0, lpattern(dash) lcolor(red)) ///
		xtitle("Years before deposition", size(small)) ytitle("Average siblings", size(small)) name(siblings, replace)				
		
twoway  (scatter average_parsib lag, msymbol(circle) mcolor(navy) msize(medium)) ///
		, aspect(1) plotregion(lwidth(none)) scheme(s1mono) ylabel(0(0.5)3, labsize(small) angle(horizontal)) ///
		xlabel(-10(2)0, labsize(small)) xline(0, lpattern(dash) lcolor(red)) ///
		xtitle("Years before deposition", size(small)) ytitle("Average uncles and aunts", size(small)) name(parsib, replace)						
		
graph combine children siblings parsib family childrendeath siblingsdeath parsibdeath familydeath, rows(2) cols(4) scheme(s1mono) xsize(4) ysize(2)
graph export "Output/appendix_figA2.pdf", replace		

********************************************************************************
******************************** Appendix 3.5 **********************************
********************************************************************************

forvalues n = 1(1)5 {
tssmooth ma waryear_civil_`n' = waryear_civil_, window(`n' 0 0)

tssmooth ma waryear_int_`n' = waryear_int_, window(`n' 0 0)

tssmooth ma family_death_`n' = family_death, window(`n' 0 0)

tssmooth ma children_death_`n' = children_death, window(`n' 0 0)

tssmooth ma siblings_death_`n' = siblings_death, window(`n' 0 0)

tssmooth ma parsib_death_`n' = parsib_death, window(`n' 0 0)

gen family_all_lag`n'=.
replace family_all_lag`n'= family_all[_n-`n'] if id_reign == id_reign[_n-`n']

gen children_all_lag`n'=.
replace children_all_lag`n'= children_all[_n-`n'] if id_reign == id_reign[_n-`n']

gen siblings_all_lag`n'=.
replace siblings_all_lag`n'= siblings_all[_n-`n'] if id_reign == id_reign[_n-`n']

gen parsib_all_lag`n'=.
replace parsib_all_lag`n'= parsib_all[_n-`n'] if id_reign == id_reign[_n-`n']

}


eststo clear

forvalues n = 1(1)5 {

reg deposed_100 family_all monarch_queen married primogeniture dum_illegitimate dum_zanden family_death_`n' age_imputed age2 age3 tenure_rolling tenure2 tenure3 i.id_country i.century i.century if dum_interregnum==0, cluster(id_monarch)
eststo m1_`n'
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

reg deposed_100 children_all siblings_all parsib_all monarch_queen married primogeniture dum_illegitimate dum_zanden  children_death_`n' siblings_death_`n' dum_zanden age_imputed age2 age3 tenure_rolling tenure2 tenure3 i.id_country i.century if dum_interregnum==0, cluster(id_monarch)
eststo m2_`n'
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

}

esttab m1_1 m1_5 m2_1 m2_5 using "Output/appendix_tableA12.tex", style(tex) nogap replace t label b(3) star(* 0.05 ** 0.01 *** 0.001) ///
stats(N age tenure country century r2_a, fmt(0 0 0 0 0 3) labels("N" "Age controls:" "Tenure controls:" "Century fixed effects:" "Country fixed effects:" "R2(adj)")) ///
title() noomitted eqlabels(none) compress nodep drop(age_imputed age2 age3 tenure_rolling tenure2 tenure3 *.id_country *.century) ///
order(family_all children_all siblings_all parsib_all) mtitles("1 year" "5 years" "1 year" "5 years")

eststo clear

forvalues n = 1(1)5 {

reg deposed_100 family_all monarch_queen married primogeniture dum_illegitimate dum_zanden waryear_civil_`n' waryear_int_`n' age_imputed age2 age3 tenure_rolling tenure2 tenure3 i.id_country i.century i.century if dum_interregnum==0, cluster(id_monarch)
eststo m1_`n'
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

reg deposed_100 children_all siblings_all parsib_all monarch_queen married primogeniture dum_illegitimate dum_zanden waryear_civil_`n' waryear_int_`n' age_imputed age2 age3 tenure_rolling tenure2 tenure3 i.id_country i.century if dum_interregnum==0, cluster(id_monarch)
eststo m2_`n'
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

}

esttab m1_1 m1_5 m2_1 m2_5 using "Output/appendix_tableA13.tex", style(tex) nogap replace t label b(3) star(* 0.05 ** 0.01 *** 0.001) ///
stats(N age tenure country century r2_a, fmt(0 0 0 0 0 3) labels("N" "Age controls:" "Tenure controls:" "Century fixed effects:" "Country fixed effects:" "R2(adj)")) ///
title() noomitted eqlabels(none) compress nodep drop(age_imputed age2 age3 tenure_rolling tenure2 tenure3 *.id_country *.century) ///
order(family_all children_all siblings_all parsib_all) mtitles("1 year" "5 years" "1 year" "5 years")


********************************************************************************
******************************** Appendix 3.6 **********************************
********************************************************************************

eststo clear

capture drop l1_family_all-l5_siblings_all
foreach n in 1 3 5 {

gen l`n'_family_all = l`n'.family_all
label variable l`n'_family_all "Family size\textsubscript{t-`n'}"

gen l`n'_children_all = l`n'.children_all
label variable l`n'_children_all "Children\textsubscript{t-`n'}"

gen l`n'_siblings_all = l`n'.siblings_all
label variable l`n'_siblings_all "Siblings\textsubscript{t-`n'}"

gen l`n'_parsib_all = l`n'.parsib_all
label variable l`n'_parsib_all "Uncles and aunts\textsubscript{t-`n'}"

}


foreach n in 1 3 5 {

reg deposed_100 l`n'_family_all monarch_queen married primogeniture dum_illegitimate dum_zanden age_imputed age2 age3 tenure_rolling tenure2 tenure3 i.id_country i.century if dum_interregnum==0, cluster(id_monarch)
eststo m1_`n'
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

reg deposed_100 l`n'_children_all l`n'_siblings_all l`n'_parsib_all monarch_queen married primogeniture dum_illegitimate dum_zanden age_imputed age2 age3 tenure_rolling tenure2 tenure3 i.id_country i.century if dum_interregnum==0, cluster(id_monarch)
eststo m2_`n'
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

}


esttab m1_1 m1_3 m1_5 m2_1 m2_3 m2_5 using "Output/appendix_tableA14.tex", style(tex) nogap replace t label b(3) star(* 0.05 ** 0.01 *** 0.001) ///
stats(N age tenure country century r2_a, fmt(0 0 0 0 0 3) labels("N" "Age controls:" "Tenure controls:" "Century fixed effects:" "Country fixed effects:" "R2(adj)")) ///
title() noomitted eqlabels(none) compress nodep drop(age_imputed age2 age3 tenure_rolling tenure2 tenure3 *.id_country *.century) ///
order(l1_family_all l3_family_all l5_family_all l1_children_all l1_siblings_all l1_parsib_all l3_children_all l3_siblings_all l3_parsib_all l5_children_all l5_siblings_all l5_parsib_all) mtitles("1 year" "3 years" "5 years"  "1 year" "3 years" "5 years")


********************************************************************************
******************************** Appendix 3.7 **********************************
********************************************************************************
* Creat proxy variables
gen temp_childrenatstart = children_all if tenure_rolling==0
egen childrenatstart = min(temp_childrenatstart), by(id_reign)

gen temp_siblingsatstart = siblings_all if tenure_rolling==0
egen siblingsatstart = min(temp_siblingsatstart), by(id_reign)

gen temp_parsibatstart = parsib_all if tenure_rolling==0
egen parsibatstart = min(temp_parsibatstart), by(id_reign)

gen temp_familyatstart = family_all if tenure_rolling==0
egen familyatstart = min(temp_familyatstart), by(id_reign)

drop temp_childrenatstart temp_siblingsatstart temp_parsibatstart temp_familyatstart

gen sum_births_children = 0
gen sum_deaths_children = 0
gen sum_births_siblings = 0
gen sum_births_parsibs = 0

forvalues nr = 1/20 {
egen sibling`nr'_totalbirth = min(sibling`nr'_birth), by(id_monarch)
egen sibling`nr'_totalsex = max(sibling`nr'_sex), by(id_monarch)

egen parsib`nr'_totalbirth = min(parsib`nr'_birth), by(id_monarch)
egen parsib`nr'_totalsex = max(parsib`nr'_sex), by(id_monarch)

egen birthtempchild`nr' = min(child`nr'_birth), by(id_reign)
egen deathtempchild`nr' = min(child`nr'_death), by(id_reign)

replace sum_births_children = sum_births_children+1 if birthtempchild`nr'<=year & deathtempchild`nr'<.
replace sum_deaths_children = sum_deaths_children+1 if deathtempchild`nr'<=year & birthtempchild`nr'<.

drop birthtempchild`nr' deathtempchild`nr'

replace sum_births_siblings = sum_births_siblings+1 if sibling`nr'_totalbirth<=year
replace sum_births_parsibs = sum_births_parsibs+1 if parsib`nr'_totalbirth<=year
}
gen sum_births_family = sum_births_children+sum_births_siblings+sum_births_parsibs


label variable sum_births_family "Sum of births of members of family"
label variable sum_births_children "Sum of births of children"
label variable sum_births_siblings "Sum of births of siblings"
label variable sum_births_parsibs "Sum of births of uncles and aunts"
label variable familyatstart "Family at start of reign"
label variable childrenatstart "Children at start of reign"
label variable siblingsatstart "Siblings at start of reign"
label variable parsibatstart "Uncles and aunts at start of reign"



global controls "monarch_queen married primogeniture dum_illegitimate dum_zanden age_imputed age2 age3 tenure_rolling tenure2 tenure3 i.id_country i.century"

reg deposed_100 marriageyears $controls if dum_interregnum==0, cluster(id_monarch)
eststo proxy1
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

reg deposed_100 sum_births_family $controls if dum_interregnum==0, cluster(id_monarch)
eststo proxy2
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

reg deposed_100 sum_births_children sum_births_siblings sum_births_parsib $controls if dum_interregnum==0, cluster(id_monarch)
eststo proxy3
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

reg deposed_100 familyatstart $controls  if dum_interregnum==0, cluster(id_monarch)
eststo proxy4
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

reg deposed_100 childrenatstart siblingsatstart parsibatstart $controls  if dum_interregnum==0, cluster(id_monarch)
eststo proxy5
estadd local country "Yes"
estadd local century "Yes"
estadd local age "Yes"
estadd local tenure "Yes"

esttab proxy1 proxy2 proxy3 proxy4 proxy5 using "Output/appendix_tableA15.tex", style(tex) nogap replace t label b(3) star(* 0.05 ** 0.01 *** 0.001) ///
stats(N age tenure country century r2_a, fmt(0 0 0 0 0 3) labels("N" "Age controls:" "Tenure controls:" "Country fixed effects:" "Century fixed effects:" "R2(adj)")) ///) ///
title() noomitted eqlabels(none) compress nodep drop(age_imputed age2 age3 tenure_rolling tenure2 tenure3 *.id_country *.century) ///
order(marriageyears sum_births_family sum_births_children sum_births_siblings sum_births_parsibs familyatstart childrenatstart siblingsatstart parsibatstart) ///
nomtitles

