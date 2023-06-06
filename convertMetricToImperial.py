import pandas as pd
import streamlit as st
import numpy as np
import math

#Bereinigung der Fehlmessungen
def app(df):

    # Convert 'fillingLevel.volume' from liter to gallons
    df['fillingLevel.volume'] = df['fillingLevel.volume'] * 0.264172

    # Convert 'fillingLevel.weight' from kilogram to pounds
    df['fillingLevel.weight'] = df['fillingLevel.weight'] * 2.20462

    df['temperature.current'] = (df['temperature.current'] * 9/5 ) +32

    return df
