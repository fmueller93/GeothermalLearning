"""
This script creates a more concise and readable subset of the geothermal data base for processing in Stata.

The script performs the following tasks:
1. Remove projects with start of operations after 2024
2. Replace missing values in "Start of operations" with the "Announcement date" 
and print the number of missing values
3. Calculate the cumulative sums for the x-axis/independent variable and add their log values, 
both for global and national level
4. Remove projects where the status isn't "operational" or "deoperational"
5. Remove projects wihtout cost data

Usage:
    Stata global regression analysis.

Outputs:
    - Saves an xlsx table

Author: Florian Müller
Date: December 2024
"""


import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# Read the Excel file
# Get the current user's username
current_user = os.getlogin()
print(f"Current user: {current_user}")

# Define file paths for each user
file_paths = {
    "mflori": r"C:\Users\mflori\OneDrive - ETH Zurich\Economics of geothermal\data\20240722_Geothermal Database.xlsm",
}

# Select the file path based on the current user
file_path = file_paths.get(current_user)
sheet_name = 'Sheet1'
df = pd.read_excel(file_path, sheet_name=sheet_name)
fx_df = pd.read_excel(file_path, sheet_name='FX_Rates', header=3)
inflation_df = pd.read_excel(file_path, sheet_name='Inflation_USD', header=1)  # Adjust header if needed

# Exlude porjects with "Start of operations" after 2024, drop rows where conversion failed, Convert to integer safely
df['Start of operations'] = pd.to_numeric(df['Start of operations'], errors='coerce')
df = df.dropna(subset=['Start of operations'])
df['Start of operations'] = df['Start of operations'].astype(int)
df['Start of operations'] = pd.to_datetime(df['Start of operations'], format='%Y').dt.year
df = df[df['Start of operations'] <= 2024]

# Sort by 'Start of operations'
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
df['Log_CostMW'] = np.log(df['Cost (mUSD 2024) / El. Power (MW)'])
df['Log_PowerEl'] = np.log(df['El. power gross (MW)'])

# Define nonempty columns, converted these columns to numeric and force errors to NaN, drop rows with NaN or zero
nonempty_columns = [
    'Cost (mUSD 2024) / El. Power (MW)'
]
for col in nonempty_columns:
    df[col] = pd.to_numeric(df[col], errors='coerce')
df = df.dropna(subset=nonempty_columns)  # Drop rows with NaN in any numeric column
df = df[~(df[nonempty_columns] == 0).any(axis=1)]  # Drop rows with zero in any numeric column

# Exclude outliers 
df = df[df['Cost (mUSD 2024) / El. Power (MW)'] <= 100] # Manually remove one point

# Only include rows in the dataframe where "Status" is either "Operational" OR "DeOperational"
df = df[df['Status'].isin(['Operational', 'DeOperational'])]

########################### Currency Calculations #######################################

# Reshape FX rates to long format
year_columns = [col for col in fx_df.columns if isinstance(col, int)]

fx_long = fx_df.melt(
    id_vars=['Country Code'],
    value_vars=year_columns,
    var_name='Year',
    value_name='FX Rate'
)

# Step 1: Build a lookup dictionary
fx_lookup = {
    (row['Country Code'], row['Year']): row['FX Rate']
    for _, row in fx_long.iterrows()
}

# Step 2: Convert USD to local currency row-by-row
def convert_to_local(row):
    if row['Country'] == 'USA':
        return row['Transaction Value 1 in USD']  # No conversion needed
    key = (row['Country'], int(row['Year of Transaction']))
    fx_rate = fx_lookup.get(key)
    if fx_rate is not None and pd.notna(row['Transaction Value 1 in USD']):
        return row['Transaction Value 1 in USD'] * fx_rate
    return None

df['Transaction Value 1 in Local'] = df.apply(convert_to_local, axis=1)

# Lookup for FX rates specifically for the base year (2024)
fx_2024_lookup = {
    row['Country Code']: row['FX Rate']
    for _, row in fx_long[fx_long['Year'] == 2024].iterrows()
}

def convert_local_to_usd_2024(row):
    value_local = row['Transaction Value 1 in Local']
    country_code = row['Country']
    
    # FIX: Explicitly handle USA → USD conversion
    if country_code == 'USA':
        return value_local  # No conversion needed, rate is 1
    
    fx_rate_2024 = fx_2024_lookup.get(country_code)
    if pd.notna(value_local) and fx_rate_2024 and fx_rate_2024 != 0:
        return value_local / fx_rate_2024
    return None

# Apply conversion and create the new column
df['Transaction Value 1 in USD (FX adj)'] = df.apply(convert_local_to_usd_2024, axis=1)

# ----- CPI-only inflation adjustments -----
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

def adjust_value_cpi_local(row):
    value = row['Transaction Value 1 in Local']
    if pd.isna(value):
        return None
    country_code = row['Country']
    year = int(row['Year of Transaction'])
    base = inflation_lookup.get((country_code, year))
    final = inflation_lookup.get((country_code, 2024))
    if base and final:
        return value * (final / base)
    return None

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

df['Project Cost (mUSD 2024 CPI)'] = df.apply(adjust_value_cpi_usd, axis=1)
df['Project Cost (mLCU 2024 CPI)'] = df.apply(adjust_value_cpi_local, axis=1)
df['Project Cost (mUSD 2024 CPI, FX adj)'] = df.apply(adjust_value_cpi_usd_fxadj, axis=1)

# ----- Combined (PPI for USA, CPI for others) -----
def adjust_value_combined_usd(row):
    value = row['Transaction Value 1 in USD']
    if pd.isna(value):
        return None
    country_code = row['Country']
    year = int(row['Year of Transaction'])
    if country_code == 'USA':
        base_index = ppi_lookup.get(year)
        final_index = ppi_lookup.get(2024)
        if base_index and final_index:
            return value * (final_index / base_index)
    else:
        base = inflation_lookup.get(("USA", year))
        final = inflation_lookup.get(("USA", 2024))
        if base and final:
            return value * (final / base)
    return None

def adjust_value_combined_usd_fxadj(row):
    value = row['Transaction Value 1 in USD (FX adj)']
    if pd.isna(value):
        return None
    country_code = row['Country']
    year = int(row['Year of Transaction'])
    if country_code == 'USA':
        base_index = ppi_lookup.get(year)
        final_index = ppi_lookup.get(2024)
        if base_index and final_index:
            return value * (final_index / base_index)
    else:
        base = inflation_lookup.get(("USA", year))
        final = inflation_lookup.get(("USA", 2024))
        if base and final:
            return value * (final / base)
    return None

def adjust_value_combined_local(row):
    value = row['Transaction Value 1 in Local']
    if pd.isna(value):
        return None
    country_code = row['Country']
    year = int(row['Year of Transaction'])
    if country_code == 'USA':
        base_index = ppi_lookup.get(year)
        final_index = ppi_lookup.get(2024)
        if base_index and final_index:
            return value * (final_index / base_index)
    else:
        base = inflation_lookup.get((country_code, year))
        final = inflation_lookup.get((country_code, 2024))
        if base and final:
            return value * (final / base)
    return None

df['Project Cost (mUSD 2024 PPI)'] = df.apply(adjust_value_combined_usd, axis=1)
df['Project Cost (mLCU 2024 PPI)'] = df.apply(adjust_value_combined_local, axis=1)
df['Project Cost (mUSD 2024 PPI, FX adj)'] = df.apply(adjust_value_combined_usd_fxadj, axis=1)

# ---------- Cost per MW calculations ----------
# 1) USD CPI-only
df['Cost (mUSD 2024 CPI) / El. Power (MW)'] = df.apply(
    lambda row: row['Project Cost (mUSD 2024 CPI)'] / row['El. power gross (MW)']
    if pd.notna(row['Project Cost (mUSD 2024 CPI)']) and 
       pd.notna(row['El. power gross (MW)']) and 
       row['El. power gross (MW)'] != 0
    else None,
    axis=1
)

# 3) Local CPI-only
df['Cost (mLCU 2024 CPI) / El. Power (MW)'] = df.apply(
    lambda row: row['Project Cost (mLCU 2024 CPI)'] / row['El. power gross (MW)']
    if pd.notna(row['Project Cost (mLCU 2024 CPI)']) and 
       pd.notna(row['El. power gross (MW)']) and 
       row['El. power gross (MW)'] != 0
    else None,
    axis=1
)

# 5) USD CPI-only (FX adjusted)
df['Cost (mUSD 2024 CPI, FX adj) / El. Power (MW)'] = df.apply(
    lambda row: row['Project Cost (mUSD 2024 CPI, FX adj)'] / row['El. power gross (MW)']
    if pd.notna(row['Project Cost (mUSD 2024 CPI, FX adj)']) and 
       pd.notna(row['El. power gross (MW)']) and 
       row['El. power gross (MW)'] != 0
    else None,
    axis=1)

# ---------- Log versions ----------
df['Log_CostMW_USD_CPI'] = np.log(df['Cost (mUSD 2024 CPI) / El. Power (MW)'])
df['Log_CostMW_LCU_CPI'] = np.log(df['Cost (mLCU 2024 CPI) / El. Power (MW)'])
df['Log_CostMW_USD_CPI_FXadj'] = np.log(df['Cost (mUSD 2024 CPI, FX adj) / El. Power (MW)'])


# Updated list of columns to keep, including all 4 cost per MW calculations and their log versions:
columns_to_keep = [
    'Source', 'Projectname', 'Country', 'State', 'Status', 'Start of operations', 'El. power gross (MW)',
    'Th. power gross (MW)',
    'Cost (mUSD 2024 CPI) / El. Power (MW)', 
    'Cost (mLCU 2024 CPI) / El. Power (MW)', 
    'Cost (mUSD 2024 CPI, FX adj) / El. Power (MW)', 
    'Project Cost (mUSD 2024 CPI)', 'Project Cost (mUSD 2024)', 
    'Project Cost (mLCU 2024 CPI)', 
    'Project Cost (mUSD 2024 CPI, FX adj)', 
    'Transaction Value 1 in USD', 'Transaction Value 1 in Local', 
    'Transaction Value 1 in USD (FX adj)',  
    'Year of Transaction', 'Transaction value 1', 'Country Code of Currency 1',
    'Cum_power_el_global', 'Log_Cum_power_el_global',
    'Cum_power_el_country', 'Log_Cum_power_el_country',
    'Log_CostMW_USD_CPI', 
    'Log_CostMW_LCU_CPI', 
    'Log_CostMW_USD_CPI_FXadj', 
    'Log_PowerEl',
]
# Select only the columns to keep
df_filtered = df.loc[:, columns_to_keep]

# Print the number of rows in the filtered dataframe
print(f"Number of rows in the filtered dataframe: {len(df_filtered)}")

##################################################################################
# Create new files, one without first and one without first two cost data points #
##################################################################################

# Create new file versions by removing the first or first two cost data points for each country
def remove_first_cost_data(df, num_points):
    """
    Remove the first `num_points` cost data points for each country.
    """
    df = df.sort_values(['Country', 'Start of operations'])  # Sort by Country and Start of operations
    result = pd.DataFrame()  # Placeholder for the modified DataFrame
    
    for country, group in df.groupby('Country'):
        # Exclude the first `num_points` rows for each group
        modified_group = group.iloc[num_points:]
        result = pd.concat([result, modified_group], ignore_index=True)
    
    return result

# Create a version excluding the first cost data point for each country
df_removed_first = remove_first_cost_data(df_filtered, num_points=1)

# Create another version excluding the first two cost data points for each country
df_removed_first_two = remove_first_cost_data(df_filtered, num_points=2)

# Save the new dataframes to separate files
file_paths_save_versioned = {
    "mflori": r"C:\Users\mflori\Desktop\AEGIS\10 Stata\data",
    "finni": r"C:\Users\finni\OneDrive\Dokumente\GitHub\AEGIS\10 Stata\data",
}
file_path_save = file_paths_save_versioned.get(current_user)

# Save all three versions
if file_path_save:
    df_filtered.to_excel(
        os.path.join(file_path_save, 'Data_preprocessed_global.xlsx'),
        index=False, engine='openpyxl'
    )
    df_removed_first.to_excel(
        os.path.join(file_path_save, 'Data_preprocessed_removed_first_cost_point.xlsx'),
        index=False, engine='openpyxl'
    )
    df_removed_first_two.to_excel(
        os.path.join(file_path_save, 'Data_preprocessed_removed_first_two_cost_points.xlsx'),
        index=False, engine='openpyxl'
    )
    print("All files saved successfully!")
else:
    print("File path for saving not found. Please check user configuration.")