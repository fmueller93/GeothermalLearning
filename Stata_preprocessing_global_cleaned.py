import pandas as pd
import numpy as np


# ============================= Load Input Data =============================

# Import data: Enter file path of xlsx file
file_path = 'file_path'
df = pd.read_excel(file_path, sheet_name='Geothermal Projects')
fx_df = pd.read_excel(file_path, sheet_name='FX_Rates')
inflation_df = pd.read_excel(file_path, sheet_name='Inflation_USD')


# ======================== Prepare Project Data =============================

# Sort by 'Start of operations'
df = df.dropna(subset=['Start of operations'])
df = df[df['Start of operations'] <= 2024]
df.sort_values('Start of operations', inplace=True)

# Calculate the cumulative sums for the x-axis/independent variable
for i, row in df.iterrows():
    # Global cumulative sum, considering only specified statuses
    df.at[i, 'Cum_power_el_global'] = df.loc[
        (df['Start of operations'] <= row['Start of operations']) & 
        (df['Status'].isin(['Operational', 'DeOperational', 'Stopped after drilling'])), 
        'El. power gross (MW)'
    ].sum()

    # Country-specific cumulative sum
    df.at[i, 'Cum_power_el_country'] = df.loc[
        (df['Start of operations'] <= row['Start of operations']) & 
         (df['Status'].isin(['Operational', 'DeOperational', 'Stopped after drilling'])) &
        (df['Country'] == row['Country']), 
        'El. power gross (MW)'].sum()

# Add columns for the log values of the above
df['Log_Cum_power_el_global'] = np.log(df['Cum_power_el_global'])
df['Log_Cum_power_el_country'] = np.log(df['Cum_power_el_country'])


# Manually remove one high-cost outlier
df = df[df['Cost (mUSD 2024) / El. Power (MW)'] <= 100]

# Filter to projects with status 'Operational' or 'DeOperational'
df = df[df['Status'].isin(['Operational', 'DeOperational'])]


# ============================= FX Adjustments =============================
# Accounts for the effect of exchange rate fluctuations based on Liliestam et al. (2020). 
# DOI: https://doi.org/10.1038/s41560-019-0531-y

# Step 1: Convert project costs from USD to local currency using the FX rate from the year of transaction.
# For projects originally recorded in local currency, the conversion to USD was already done in Excel.
# This step reverses that process to recover local values.

# Step 2: Analog to eq. (10) of Liliestam et al. (2020), we correct for exchange rate fluctations by applying a fixed FX rate of a base year to our local currency values.
# Specifically, we convert the local currency to USD using the FX rates for our base year 2024.


# Reshape FX rates to long format
year_columns = [col for col in fx_df.columns if isinstance(col, int)]

fx_long = fx_df.melt(
    id_vars=['Country Code'],
    value_vars=year_columns,
    var_name='Year',
    value_name='FX Rate'
)

# Build a lookup dictionary
fx_lookup = {
    (row['Country Code'], row['Year']): row['FX Rate']
    for _, row in fx_long.iterrows()
}

# Convert USD to local currency row-by-row
def convert_to_local(row):
    if row['Country'] == 'USA':
        return row['Transaction Value 1 in USD']  # No conversion needed
    key = (row['Country'], int(row['Year of Transaction']))
    fx_rate = fx_lookup.get(key)
    if fx_rate is not None and pd.notna(row['Transaction Value 1 in USD']):
        return row['Transaction Value 1 in USD'] * fx_rate
    return None

# Apply conversion and create the new local currency column
df['Transaction Value 1 in Local'] = df.apply(convert_to_local, axis=1)

# Lookup for FX rates specifically for the base year (2024)
fx_2024_lookup = {
    row['Country Code']: row['FX Rate']
    for _, row in fx_long[fx_long['Year'] == 2024].iterrows()
}

# Convert local currency to USD using the 2024 FX rates
def convert_local_to_usd_2024(row):
    value_local = row['Transaction Value 1 in Local']
    country_code = row['Country']
    
    # Explicitly handle USA → USD conversion
    if country_code == 'USA':
        return value_local  # No conversion needed, rate is 1
    
    fx_rate_2024 = fx_2024_lookup.get(country_code)
    if pd.notna(value_local) and fx_rate_2024 and fx_rate_2024 != 0:
        return value_local / fx_rate_2024
    return None

# Apply conversion and create the new FX adjusted USD column
df['Transaction Value 1 in USD (FX adj)'] = df.apply(convert_local_to_usd_2024, axis=1)


# ========================== Inflation Adjustments ==========================
# Adjusts all values to 2024 terms using Consumer Price Indices

# Reshape the inflation data to long format
year_columns = [col for col in inflation_df.columns if isinstance(col, int)]

inflation_long = inflation_df.melt(
    id_vars='Country Code',
    value_vars=year_columns,
    var_name='Year',
    value_name='Index'
)

# Build the lookup dictionary: {(country_code, year): index}
inflation_lookup = {
    (row['Country Code'], row['Year']): row['Index']
    for _, row in inflation_long.iterrows()
}

# Adjust transaction values to 2024 terms using CPI
def adjust_value_cpi_usd(row):
    value = row['Transaction Value 1 in USD']
    if pd.isna(value):
        return None
    year = int(row['Year of Transaction'])
    base = inflation_lookup.get(('USA', year))  # Always USA CPI for USD
    final = inflation_lookup.get(('USA', 2024))
    if base and final:
        return value * (final / base)
    return None

# Adjust fx-adjusted transaction values to 2024 terms using CPI
def adjust_value_cpi_usd_fxadj(row):
    value = row['Transaction Value 1 in USD (FX adj)']
    if pd.isna(value):
        return None
    year = int(row['Year of Transaction'])
    base = inflation_lookup.get(('USA', year))  # Always USA CPI for USD
    final = inflation_lookup.get(('USA', 2024))
    if base and final:
        return value * (final / base)
    return None

# apply inflation adjustments
df['Project Cost (mUSD 2024 CPI)'] = df.apply(adjust_value_cpi_usd, axis=1)
df['Project Cost (mUSD 2024 CPI, FX adj)'] = df.apply(adjust_value_cpi_usd_fxadj, axis=1)


# ======================== Cost-per-MW Calculations =========================

# USD CPI
df['Cost (mUSD 2024 CPI) / El. Power (MW)'] = df.apply(
    lambda row: row['Project Cost (mUSD 2024 CPI)'] / row['El. power gross (MW)']
    if pd.notna(row['Project Cost (mUSD 2024 CPI)']) and 
       pd.notna(row['El. power gross (MW)']) and 
       row['El. power gross (MW)'] != 0
    else None,
    axis=1
)

# USD CPI (FX adjusted)
df['Cost (mUSD 2024 CPI, FX adj) / El. Power (MW)'] = df.apply(
    lambda row: row['Project Cost (mUSD 2024 CPI, FX adj)'] / row['El. power gross (MW)']
    if pd.notna(row['Project Cost (mUSD 2024 CPI, FX adj)']) and 
       pd.notna(row['El. power gross (MW)']) and 
       row['El. power gross (MW)'] != 0
    else None,
    axis=1)

# transform cost-per-MW values to log scale
df['Log_CostMW_USD_CPI'] = np.log(df['Cost (mUSD 2024 CPI) / El. Power (MW)'])
df['Log_CostMW_USD_CPI_FXadj'] = np.log(df['Cost (mUSD 2024 CPI, FX adj) / El. Power (MW)'])


