import pandas as pd
import streamlit as st
import numpy as np
import math

#Bereinigung der Fehlmessungen
def app(df, start_place):
    if len(df) < 3:
        return df
    df = df.reset_index(drop=True)

    df['fillingLevel.percent'] = df['fillingLevel.percent'].fillna(0).astype(float)

    full_mask = df['fillingLevel.percent'] >= 90
    in_use_mask = (df['fillingLevel.percent']) < 90 & (df['fillingLevel.percent'] > 10)
    empty_mask = df['fillingLevel.percent'] <= 10
    # Use NumPy's where function to assign values based on the conditions
    df['fillingLevel.state'] = np.where(full_mask, 'Full', np.where(empty_mask, 'empty', 'operative'))

    z = 0
    for c in df['fillingLevel.percent']:
        if z > 2:
            vl = df.loc[z-2, 'fillingLevel.percent']
            le = df.loc[z-1, 'fillingLevel.percent']
            if((vl == 100) and (le != 100) and (c == 100)):
                df.loc[z-1, 'fillingLevel.percent'] = 100
            elif((vl == 0) and (le != 0) and (c == 0)):
                df.loc[z-1,'fillingLevel.percent'] = 0
            elif((vl == 0) and (le != 100) and (c == 0)):
                df.loc[z-1, 'fillingLevel.percent'] = 0
        z=z+1



    ### @Marc
    ### Filling Level Cleanup Anpassen auf basis Filling Level state
    # wenn voll leer voll, dann leer = voll
    # wenn leer voll leer, dann voll = leer  
    """ z = 0
    for container in df['fillingLevel.state']:
        if z > 2:
            container_vl = df.loc[z-2, 'fillingLevel.state']
            container_le = df.loc[z-1, 'fillingLevel.state']

            if((container_vl == 'Full') and (container_le == 'empty') and (container == 'Full')):
                df.loc[z-1, 'fillingLevel.state'] = 'Full'

            elif((container_vl == 'empty') and (container_le == 'Full') and (container == 'empty')):
                df.loc[z-1,'fillingLevel.state'] = 'empty'

            elif((container_vl == 'empty') and (container_le == 'in use') and (container == 'empty')):
                df.loc[z-1, 'fillingLevel.state'] = 'empty'
        z=z+1 """
    

    ### Cleanup wenn place = startplace und fillingState sich am start_place ändert zwischen messungen
    for i in range(1, len(df)-2):
        if df.loc[i, 'place.name'] == start_place and (df.loc[i, 'fillingLevel.state'] == 'empty' or df.loc[i, 'fillingLevel.state'] == 'in use') and df.loc[i-1, 'fillingLevel.state'] == 'Full':
            j = i + 1
            while df.loc[j, 'place.name'] == 'A' and (df.loc[j, 'fillingLevel.state'] == 'empty' or df.loc[i, 'fillingLevel.state'] == 'in use') and j < len(df)-1:
                j += 1
            df.loc[i:j-1, 'fillingLevel.state'] = 'Full'

    return df
    
