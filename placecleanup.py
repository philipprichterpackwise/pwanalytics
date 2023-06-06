import pandas as pd
import streamlit as st

def app(df):
    if len(df) < 3:
        return df
    df = df.reset_index(drop=True)
    #p = 0
    #for place in df['place.name']:
    #    if place != 'on Transport':
    #        if p > 1:
    #            pvl = df.loc[p-2, 'place.name']
    #            ple = df.loc[p-1, 'place.name']
    #            if pvl == place and ple != place:
    #                df.loc[p-1, 'place.name'] = place
    #        p += 1
    # The overall purpose of the code is to iterate through the 'place.name' column of the DataFrame
    # and overwrite any 'on Transport' values that occur between two identical place names with 
    # the name of the place. The inner loop that starts with for j in range(i-1, -1, -1) goes backwards 
    # from the current index to find the first row with a place name that is not 'on Transport'. 
    # This allows the code to overwrite all 'on Transport' values between two identical place names, 
    # even if there are multiple 'on Transport' values in a row.
    """ last_place = ''
    for i, place in enumerate(df['place.name']):
        if place != 'on Transport':
            if last_place == place:
                for j in range(i-1, -1, -1):
                    if df.loc[j, 'place.name'] != 'on Transport':
                        break
                    df.loc[j, 'place.name'] = place
            else:
                last_place = place """
    return df
