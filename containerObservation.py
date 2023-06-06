import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from datetime import timedelta
import createMap

from folium.features import DivIcon
from streamlit_folium import folium_static
from streamlit_folium import st_folium
import folium

import addFilterToDataframe

def get_long_stays(df, daysTresh):
    # Convert the timestamp column to datetime and sort it
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(['container.name', 'timestamp'])

    # Create a new column that indicates when the place.name changes
    df['place_changed'] = df['place.name'] != df.groupby('container.name')['place.name'].shift()

    # Create a new group ID that increments every time the place.name changes
    df['group_id'] = df.groupby('container.name')['place_changed'].cumsum()

    # Compute the duration of each stay
    df['stay_duration'] = df.groupby(['container.name', 'group_id'])['timestamp'].transform(lambda x: round((x.max() - x.min()).total_seconds() / (24 * 60 * 60)))

    # Keep only the rows where stay_duration is above the threshold
    long_stays = df[df['stay_duration'] >= daysTresh]
    # Calculate the start and end day of each stay
    long_stays['start_day'] = long_stays.groupby(['container.name', 'group_id'])['timestamp'].transform('min')
    long_stays['end_day'] = long_stays.groupby(['container.name', 'group_id'])['timestamp'].transform('max')
    # Select only necessary columns and drop duplicates
    result = long_stays[['container.name', 'container.containerType.name', 'place.name', 'containerData.productName', 'start_day', 'end_day', 'stay_duration']].drop_duplicates()

    # Drop the temporary columns
    long_stays = long_stays.drop(columns=['place_changed', 'group_id'])

    return result, long_stays

def app(df):
    unique_places = df['place.name'].unique()
    with st.sidebar:
        daysTresh = st.slider('Select the minimum ammount of days', min_value=1, max_value=60, value=7, step=1)
        specific_container = st.checkbox('I want to select specific places (Default: All places)')
        if specific_container:
            selected_container = st.multiselect('Select the specific places you want to observe', unique_places)
        else:
            selected_container = unique_places

    results, long_stays = get_long_stays(df, daysTresh)
    results.reset_index(inplace=True, drop=True)
    results['end_day'] = pd.to_datetime(results['end_day'])

    results = results.loc[results['place.name'].isin(selected_container)]

    if len(results) > 0:
        st.subheader('Filter Dataframe')
        st.write('You also have the option to filter the dataframe as you like')
        st.dataframe(addFilterToDataframe.filter_dataframe(results, True, 6), use_container_width=True)
        st.markdown('---')

        st.subheader('Map for Container')
        map_selection = st.selectbox(label='Please Select a Container you want to see.', options=results['container.name'].unique())
        map_df = long_stays[long_stays['container.name'] == map_selection]

        # Call the app() function and store the returned map
        map = createMap.app(map_df)
        st_folium(map, height= 1000,width=2000)

    else:
        st.write('No containers found that match the criteria.')