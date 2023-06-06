import streamlit as st
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from io import BytesIO
import altair as alt

from folium.plugins import MarkerCluster
from folium.features import DivIcon
from streamlit_folium import folium_static

import folium

def app(df):
    """ Input: Dataframe with longitude and latitude in format df['location.coordinates']
        Output: folium map with marker for each coordinate """

    df.reset_index(inplace=True, drop=True)

    if len(df.index) >= 2:
        df[['longitude', 'latitude']] = df['location.coordinates'].apply(lambda x: pd.Series(str(x).split(',')))
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['latitude'] = df['latitude'].astype(float)
        df['longitude'] = df['longitude'].astype(float)
        df = df.sort_values('timestamp')

        # Remove rows with NaN in 'latitude' and 'longitude' columns
        df = df.dropna(subset=['latitude', 'longitude'])

        m = folium.Map(location=[df['latitude'].mean(), df['longitude'].mean()], zoom_start=12, tiles="Stamen Terrain")
        colormap = list(plt.get_cmap('rainbow')(np.linspace(0, 1, len(df))))
        
        locations = df[['latitude', 'longitude']].values  # create a list of lists
        marker_cluster = MarkerCluster(locations, spiderfy_on_max_zoom=True).add_to(m)

        prev_row = None  # initialize prev_row
        for index, row in df.iterrows():
            color = 'red' if index == len(df)-1 else 'black'  # change the color for the last entry

            # include timestamp in the marker
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup='Index: {}<br>Timestamp: {}'.format(index, row['timestamp'].strftime("%Y-%m-%d")),
                icon=DivIcon(
                    icon_size=(150,36),
                    icon_anchor=(7,20),
                    html='<div style="font-size: 12pt; color : {}">{}</div>'.format(color, row['timestamp'].strftime("%Y-%m-%d")),
                    )
                ).add_to(marker_cluster)

            if prev_row is not None:
                folium.PolyLine(locations=[(prev_row['latitude'], prev_row['longitude']),
                                           (row['latitude'], row['longitude'])],
                                color=matplotlib.colors.rgb2hex(colormap[index]), 
                                weight=2.5).add_to(m)
            prev_row = row

        return m
