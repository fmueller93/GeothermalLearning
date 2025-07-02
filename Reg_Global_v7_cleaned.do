**#

clear

**# ssc install outreg2
**# ssc install estout

* Determine the current username
local current_user = "`c(username)'"
display "`current_user'"

* Select pre-processed Data type (1 = all points, 2 = first removed, 3 = first 2 removed)
local file_choice = 1

* Determine file suffix based on user choice
if `file_choice' == 1 {
    local file_name "Data_preprocessed_global.xlsx"
}
else if `file_choice' == 2 {
    local file_name "Data_preprocessed_removed_first_cost_point.xlsx"
}
else if `file_choice' == 3 {
    local file_name "Data_preprocessed_removed_first_two_cost_points.xlsx"
}

* Define base path depending on user
if "`current_user'" == "mflori" {
    local base_path "C:\Users\mflori\Desktop\AEGIS\10 Stata\data\\"
}
else if "`current_user'" == "finni" {
    local base_path "C:\Users\finni\OneDrive\Dokumente\GitHub\AEGIS\10 Stata\data\\"
}
else {
    display as error "No file path configured for the current user: `current_user'"
    exit
}

* Combine base path and filename
local file_path "`base_path'`file_name'"

display "Current user: `current_user'"
display "Selected file: `file_name'"
display "Base path: `base_path'"
display "Full path: `file_path'"

* Use the dynamically determined file path
import excel "`file_path'", sheet("Sheet1") firstrow 

* Define thresholds and filters
local ElpowergrossMW_threshold 0
local ThpowergrossMW_threshold 0
local Eligible_status1 "Operational"
local Eligible_status2 "DeOperational"
local Earliest_year 0
local Latest_year 9999

* Apply filters dynamically

drop if ElpowergrossMW < `ElpowergrossMW_threshold'
drop if ThpowergrossMW < `ThpowergrossMW_threshold'
drop if !inlist(Status, "`Eligible_status1'", "`Eligible_status2'")
drop if Startofoperations < `Earliest_year' | Startofoperations > `Latest_year'

* Create Filter Description
local filter_description "Filters applied: ElpowergrossMW >= `ElpowergrossMW_threshold'; ThpowergrossMW >= `ThpowergrossMW_threshold'; Status in `Eligible_status1', `Eligible_status2'; Year > `Earliest_year' and < `Latest_year'"

* Generate the standardized variable
gen CostMWLog = .
replace CostMWLog = Log_CostMW_USD_CPI
local cost_type "USD_CPI"

gen CostMWLog_CPI = Log_CostMW_USD_CPI
gen CostMWLog_CPI_FX = Log_CostMW_USD_CPI_FXadj
rename Log_Cum_power~l DeployedPowerGlobLog
rename Log_Cum_power~y DeployedPowerNatLog
destring DeployedPowerNatLog, replace force

describe

*clear previous cache
eststo clear

* Initialize a macro to store LR outputs
local lr_outputs ""

*Model 1) Plain 
reg CostMWLog_CPI DeployedPowerGlobLog, robust
quietly {
 	local lr = round(100 * (1 - 2^(_b[DeployedPowerGlobLog])), 0.1)
                local lr_lb = round(100 * (1 - 2^(_b[DeployedPowerGlobLog] - 1.96 * _se[DeployedPowerGlobLog])), 0.1)
        local lr_ub = round(100 * (1 - 2^(_b[DeployedPowerGlobLog] + 1.96 * _se[DeployedPowerGlobLog])), 0.1)
		local lr_outputs = "[`lr_lb';`lr_ub']"
}
display "LR: `lr'% `lr_outputs'" 

*save to Excel and CSV
outreg2 using "`output_file'", replace ctitle(Plain) label title("Regression results `timestamp'") addtext("Learning Rate","`lr'%" , "Confidence LR [%]","`lr_outputs'") addnote("`filter_description'") excel
eststo: reg CostMWLog_CPI DeployedPowerGlobLog, robust

*Model 2) W/o small projects

reg CostMWLog_CPI DeployedPowerGlobLog if PlantPowerEl > 4.99, robust
quietly {
 	local lr = round(100 * (1 - 2^(_b[DeployedPowerGlobLog])), 0.1)
                local lr_lb = round(100 * (1 - 2^(_b[DeployedPowerGlobLog] - 1.96 * _se[DeployedPowerGlobLog])), 0.1)
        local lr_ub = round(100 * (1 - 2^(_b[DeployedPowerGlobLog] + 1.96 * _se[DeployedPowerGlobLog])), 0.1)
		local lr_outputs = "[`lr_lb';`lr_ub']"
}
display "LR: `lr'% `lr_outputs'" 
eststo: reg CostMWLog_CPI DeployedPowerGlobLog if PlantPowerEl > 4.99, robust

*save to Excel and CSV
outreg2 using "`output_file'", append ctitle(w/o small) label title("Regression results `timestamp'") addtext("Learning Rate","`lr'%" , "Confidence LR [%]","`lr_outputs'") addnote("`filter_description'") excel

*Model 3) FX adjusted
reg CostMWLog_CPI_FX DeployedPowerGlobLog, robust
quietly {
 	local lr = round(100 * (1 - 2^(_b[DeployedPowerGlobLog])), 0.1)
                local lr_lb = round(100 * (1 - 2^(_b[DeployedPowerGlobLog] - 1.96 * _se[DeployedPowerGlobLog])), 0.1)
        local lr_ub = round(100 * (1 - 2^(_b[DeployedPowerGlobLog] + 1.96 * _se[DeployedPowerGlobLog])), 0.1)
		local lr_outputs = "[`lr_lb';`lr_ub']"
}
display "LR: `lr'% `lr_outputs'" 
outreg2 using "`output_file'", append ctitle(FX adj) label title("Regression results `timestamp'") addtext("Learning Rate","`lr'%" , "Confidence LR [%]","`lr_outputs'") addnote("`filter_description'") excel
eststo: reg CostMWLog_CPI_FX DeployedPowerGlobLog, robust

*Model 4) FX adjusted, w/o small projects
reg CostMWLog_CPI_FX DeployedPowerGlobLog if PlantPowerEl > 4.99, robust
quietly {
 	local lr = round(100 * (1 - 2^(_b[DeployedPowerGlobLog])), 0.1)
                local lr_lb = round(100 * (1 - 2^(_b[DeployedPowerGlobLog] - 1.96 * _se[DeployedPowerGlobLog])), 0.1)
        local lr_ub = round(100 * (1 - 2^(_b[DeployedPowerGlobLog] + 1.96 * _se[DeployedPowerGlobLog])), 0.1)
		local lr_outputs = "[`lr_lb';`lr_ub']"
}
display "LR: `lr'% `lr_outputs'" 
outreg2 using "`output_file'", append ctitle(w/o small FX adj) label title("Regression results `timestamp'") addtext("Learning Rate","`lr'%" , "Confidence LR [%]","`lr_outputs'") addnote("`filter_description'") excel
eststo: reg CostMWLog_CPI_FX DeployedPowerGlobLog if PlantPowerEl > 4.99, robust

*5) Country analysis
*) USA
sum CostMWLog DeployedPowerNatLog if Country == "USA"
describe CostMWLog DeployedPowerNatLog
reg CostMWLog DeployedPowerNatLog if Country == "USA", robust
quietly {
 	local lr = round(100 * (1 - 2^(_b[DeployedPowerNatLog])), 0.1)
                local lr_lb = round(100 * (1 - 2^(_b[DeployedPowerNatLog] - 1.96 * _se[DeployedPowerNatLog])), 0.1)
        local lr_ub = round(100 * (1 - 2^(_b[DeployedPowerNatLog] + 1.96 * _se[DeployedPowerNatLog])), 0.1)
		local lr_outputs = "[`lr_lb';`lr_ub']"
		}
display "LR: `lr'% `lr_outputs'" 
outreg2 using "`output_file'", append ctitle(USA) label addtext("Learning Rate","`lr'%" , "Confidence LR [%]","`lr_outputs'") excel
eststo: reg CostMWLog DeployedPowerNatLog if Country == "USA", robust

*) IDN
reg CostMWLog DeployedPowerNatLog if Country == "IDN", robust
quietly {
 	local lr = round(100 * (1 - 2^(_b[DeployedPowerNatLog])), 0.1)
                local lr_lb = round(100 * (1 - 2^(_b[DeployedPowerNatLog] - 1.96 * _se[DeployedPowerNatLog])), 0.1)
        local lr_ub = round(100 * (1 - 2^(_b[DeployedPowerNatLog] + 1.96 * _se[DeployedPowerNatLog])), 0.1)
		local lr_outputs = "[`lr_lb';`lr_ub']"
		}
display "LR: `lr'% `lr_outputs'" 
outreg2 using "`output_file'", append ctitle(IDN) label addtext("Learning Rate","`lr'%" , "Confidence LR [%]","`lr_outputs'") excel
eststo: reg CostMWLog DeployedPowerNatLog if Country == "IDN", robust

*) PHI
reg CostMWLog DeployedPowerNatLog if Country == "PHI", robust
quietly {
 	local lr = round(100 * (1 - 2^(_b[DeployedPowerNatLog])), 0.1)
                local lr_lb = round(100 * (1 - 2^(_b[DeployedPowerNatLog] - 1.96 * _se[DeployedPowerNatLog])), 0.1)
        local lr_ub = round(100 * (1 - 2^(_b[DeployedPowerNatLog] + 1.96 * _se[DeployedPowerNatLog])), 0.1)
		local lr_outputs = "[`lr_lb';`lr_ub']"
		}
display "LR: `lr'% `lr_outputs'" 
outreg2 using "`output_file'", append ctitle(PHI) label addtext("Learning Rate","`lr'%" , "Confidence LR [%]","`lr_outputs'") excel
eststo: reg CostMWLog DeployedPowerNatLog if Country == "PHI", robust

*) TUR
reg CostMWLog DeployedPowerNatLog if Country == "TUR", robust
quietly {
 	local lr = round(100 * (1 - 2^(_b[DeployedPowerNatLog])), 0.1)
                local lr_lb = round(100 * (1 - 2^(_b[DeployedPowerNatLog] - 1.96 * _se[DeployedPowerNatLog])), 0.1)
        local lr_ub = round(100 * (1 - 2^(_b[DeployedPowerNatLog] + 1.96 * _se[DeployedPowerNatLog])), 0.1)
		local lr_outputs = "[`lr_lb';`lr_ub']"
		}
display "LR: `lr'% `lr_outputs'" 
outreg2 using "`output_file'", append ctitle(TUR) label addtext("Learning Rate","`lr'%" , "Confidence LR [%]","`lr_outputs'") excel
eststo: reg CostMWLog DeployedPowerNatLog if Country == "TUR", robust

*) NZL
reg CostMWLog DeployedPowerNatLog if Country == "NZL", robust
quietly {
 	local lr = round(100 * (1 - 2^(_b[DeployedPowerNatLog])), 0.1)
                local lr_lb = round(100 * (1 - 2^(_b[DeployedPowerNatLog] - 1.96 * _se[DeployedPowerNatLog])), 0.1)
        local lr_ub = round(100 * (1 - 2^(_b[DeployedPowerNatLog] + 1.96 * _se[DeployedPowerNatLog])), 0.1)
		local lr_outputs = "[`lr_lb';`lr_ub']"
		}
display "LR: `lr'% `lr_outputs'" 
outreg2 using "`output_file'", append ctitle(NZL) label addtext("Learning Rate","`lr'%" , "Confidence LR [%]","`lr_outputs'") excel
eststo: reg CostMWLog DeployedPowerNatLog if Country == "NZL", robust

*) KEN
reg CostMWLog DeployedPowerNatLog if Country == "KEN", robust
quietly {
 	local lr = round(100 * (1 - 2^(_b[DeployedPowerNatLog])), 0.1)
                local lr_lb = round(100 * (1 - 2^(_b[DeployedPowerNatLog] - 1.96 * _se[DeployedPowerNatLog])), 0.1)
        local lr_ub = round(100 * (1 - 2^(_b[DeployedPowerNatLog] + 1.96 * _se[DeployedPowerNatLog])), 0.1)
		local lr_outputs = "[`lr_lb';`lr_ub']"
		}
display "LR: `lr'% `lr_outputs'" 
outreg2 using "`output_file'", append ctitle(KEN) label addtext("Learning Rate","`lr'%" , "Confidence LR [%]","`lr_outputs'") excel
eststo: reg CostMWLog DeployedPowerNatLog if Country == "KEN", robust

*) GER
reg CostMWLog DeployedPowerNatLog if Country == "GER", robust
quietly {
 	local lr = round(100 * (1 - 2^(_b[DeployedPowerNatLog])), 0.1)
                local lr_lb = round(100 * (1 - 2^(_b[DeployedPowerNatLog] - 1.96 * _se[DeployedPowerNatLog])), 0.1)
        local lr_ub = round(100 * (1 - 2^(_b[DeployedPowerNatLog] + 1.96 * _se[DeployedPowerNatLog])), 0.1)
		local lr_outputs = "[`lr_lb';`lr_ub']"
		}
display "LR: `lr'% `lr_outputs'" 
outreg2 using "`output_file'", append ctitle(GER) label addtext("Learning Rate","`lr'%" , "Confidence LR [%]","`lr_outputs'") excel
eststo: reg CostMWLog DeployedPowerNatLog if Country == "GER", robust

