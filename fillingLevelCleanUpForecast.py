import pandas as pd
import streamlit as st
import numpy as np
import math

#Bereinigung der Fehlmessungen
def app(df):
    df['fillingLevel.percent'] = df['fillingLevel.percent'].fillna(0)
    if len(df) < 3:
        return df
    df = df.reset_index(drop=True)

    full_mask = df['fillingLevel.percent'] >= 90
    in_use_mask = (df['fillingLevel.percent'] < 90) & (df['fillingLevel.percent'] > 10)
    empty_mask = df['fillingLevel.percent'] <= 10
    # Use NumPy's where function to assign values based on the conditions
    df['fillingLevel.state'] = np.where(full_mask, 'Full', np.where(in_use_mask, 'operative', 'empty'))



    return df
    
