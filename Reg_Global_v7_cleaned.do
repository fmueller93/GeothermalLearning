* Import data: Enter file path of xlsx file
import excel "`file_path'", sheet("Sheet1") firstrow 

*** Global experience models ***
* Figure 2: Global experience (Models 1-4)
reg CostMWLog_CPI DeployedPowerGlobLog, robust
reg CostMWLog_CPI DeployedPowerGlobLog if PlantPowerEl > 4.99, robust
reg CostMWLog_CPI_FX DeployedPowerGlobLog, robust
reg CostMWLog_CPI_FX DeployedPowerGlobLog if PlantPowerEl > 4.99, robust

*** Local experience models ***
* Figure 3: Local experience models
reg CostMWLog DeployedPowerNatLog if Country == "USA", robust
reg CostMWLog DeployedPowerNatLog if Country == "IDN", robust
reg CostMWLog DeployedPowerNatLog if Country == "PHI", robust
reg CostMWLog DeployedPowerNatLog if Country == "TUR", robust
reg CostMWLog DeployedPowerNatLog if Country == "NZL", robust
reg CostMWLog DeployedPowerNatLog if Country == "KEN", robust
reg CostMWLog DeployedPowerNatLog if Country == "GER", robust


*** Supplemental regression analysis ***

* Figure S1: Local experience rate with adjustment for exchange rate fluctuations
reg CostMWLog_CPI_FX DeployedPowerNatLog if Country == "USA", robust
reg CostMWLog_CPI_FX DeployedPowerNatLog if Country == "IDN", robust
reg CostMWLog_CPI_FX DeployedPowerNatLog if Country == "PHI", robust
reg CostMWLog_CPI_FX DeployedPowerNatLog if Country == "TUR", robust
reg CostMWLog_CPI_FX DeployedPowerNatLog if Country == "NZL", robust
reg CostMWLog_CPI_FX DeployedPowerNatLog if Country == "KEN", robust
reg CostMWLog_CPI_FX DeployedPowerNatLog if Country == "GER", robust

* Figure S2: Robustness check: Local experience models with the first data point removed
* Import data: Enter file path of xlsx file with the first data point of each country removed
import excel "`file_path'", sheet("Sheet1") firstrow 
reg CostMWLog DeployedPowerNatLog if Country == "USA", robust
reg CostMWLog DeployedPowerNatLog if Country == "IDN", robust
reg CostMWLog DeployedPowerNatLog if Country == "PHI", robust
reg CostMWLog DeployedPowerNatLog if Country == "TUR", robust
reg CostMWLog DeployedPowerNatLog if Country == "NZL", robust
reg CostMWLog DeployedPowerNatLog if Country == "KEN", robust
reg CostMWLog DeployedPowerNatLog if Country == "GER", robust

* Figure S3: Robustness check: Local experience models with the first two data points removed
* Import data: Enter file path of xlsx file with the first two data points of each country removed
import excel "`file_path'", sheet("Sheet1") firstrow 
reg CostMWLog DeployedPowerNatLog if Country == "USA", robust
reg CostMWLog DeployedPowerNatLog if Country == "IDN", robust
reg CostMWLog DeployedPowerNatLog if Country == "PHI", robust
reg CostMWLog DeployedPowerNatLog if Country == "TUR", robust
reg CostMWLog DeployedPowerNatLog if Country == "NZL", robust
reg CostMWLog DeployedPowerNatLog if Country == "KEN", robust
reg CostMWLog DeployedPowerNatLog if Country == "GER", robust