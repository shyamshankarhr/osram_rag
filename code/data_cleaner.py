import pandas as pd
import numpy as np
import re


def set_column(df, column):
    if df[column].dtype == np.float64:
        return
    unit_split = df[df[column].notna()][column].iloc[0].split() # assumes all the non blank rows have the same unit
    if len(unit_split) < 2:
        df[column] = df[column].str.replace(',','.').replace('-',np.nan).astype(np.float64)
        return
    unit = unit_split[1]  
    df[column] = df[column].str.strip(f' {unit}').str.replace(',','.').replace('-',np.nan).astype(np.float64)
    return


def clean_data(df):

    # Numeric columns in english PDF (common across all files, hence harcoded)
    columns_to_convert = ['nominal_current', 'nominal_wattage', 'nominal_voltage', 'diameter', 'length', 'length_base',
                      'light_center_length', 'cable_length_input', 'electrode_gap_cold', 'product_weight', 'wire_length',
                      'max_ambient_temperature', 'lifespan', 'package_volume', 'gross_weight', 'service_warranty']
    
    for column in columns_to_convert:
        set_column(df, column)

    # Splitting current control range into min and max
    df[['current_control_range_min','current_control_range_max']] = df['current_control_range'].str.strip(' A').str.split('…', expand=True).astype(np.float64)

    # HARDCODED FIX (because of error in data sheet): if value outside the current control range, divide by 100 (because it would be missing the decimal point)
    df['nominal_current'] = np.where(((df['nominal_current']>=df['current_control_range_min'])&(df['nominal_current']<=df['current_control_range_max'])), df['nominal_current'], df['nominal_current']/100.0)

    # Changing date_declaration to datetime format
    df['date_declaration'] = pd.to_datetime(df['date_declaration'])

    # Changing product code to string type (to avoid numeric approximations)
    df['product_code'] = df['product_code'].astype(str)

    # Splitting packaging dimensions into length, width, height
    df[['packaging_length', 'packaging_width', 'packaging_height']] = df['packaging_dimensions'].str.replace('mm','').str.strip().str.split('  x ', expand=True).astype(np.float)

    return df