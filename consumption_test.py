import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from datetime import datetime

import numpy as np
from io import BytesIO
import base64
import pydeck as pdk
import addFilterToDataframe
import placecleanup 
import fillingLevelCleanUpForecast
import json

import altair as alt
import plotly as plt
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go
import plotly.offline as pyoff
import plotly.figure_factory as ff




def consumption(df, selected_places, selected_product, selected_container, all_containers, fillingLvl):

    container_volume = df['container.containerType.maxVolume'][0]
    df = fillingLevelCleanUpForecast.app(df)
    export_start = df['timestamp'].iloc[0]
    export_start = pd.to_datetime(export_start)
    export_start_str = export_start.strftime("%d-%m-%Y")
    export_end = df['timestamp'].iloc[-1]
    export_end = pd.to_datetime(export_end)
    export_end_str = export_end.strftime("%d-%m-%Y")

    # First KPI Row
    a1, a2 = st.columns(2)
    a1.metric('Export Start Time', export_start_str)
    a2.metric('Export End Time', export_end_str)
    
    # Second KPI Row
    a1, a2, a3, a4 = st.columns(4)
    a1.metric('Selected Place: ' , value=selected_places)
    a2.metric('Selected Product: ' , value=selected_product)
    a3.metric('Selected Fillinglevel: ' , value=fillingLvl)
    if all_containers:
        with a4:
            a4.metric('Container: ' , value=len(selected_container))
            with st.expander('Container List'):
                    st.dataframe(selected_container, use_container_width=True)
    else:
        with a4:
            a4.metric('Container: ' , value='See List')
            with st.expander('Container List'):
                st.dataframe(selected_container, use_container_width=True)


    st.markdown('---')
    # Create an empty DataFrame to store the concatenated data
    main_df = pd.DataFrame()

    df = df[['timestamp', fillingLvl, 'Date', 'container.name', 'place.name']]
    df[fillingLvl] = df[fillingLvl].fillna(0)

    # Group by Container and last timestamp and then sum the fillingLevel
    # Show main fillingLevel
    # Sort by 'container.name' and 'timestamp'
    df_sorted = df.sort_values(by=['container.name', 'timestamp'])

    # If you want 'timestamp' to represent only the date (without time component), you can add:
    df['Date'] = df_sorted['timestamp'].dt.date
    df = df.reset_index(drop=True)

    filling_overview = df
    #filling_overview = filling_overview[fillingLvl]
    st.subheader('Customers product stock overview')
    # Group by 'Date' and calculate the sum of 'fillingLevel.weight' for each day
    # Assuming your DataFrame is named df
    filling_overview['timestamp'] = pd.to_datetime(filling_overview['timestamp'])

    # Sort by 'timestamp'
    filling_overview = filling_overview.sort_values(by='timestamp')

    # Group by 'date' and 'container.name', and select the last 'Tagesverbrauch' entry of each day for each container
    df_grouped = filling_overview.groupby(['Date', 'container.name']).last().reset_index()

    # Sum the 'Tagesverbrauch' for each day for every container
    filling_overview_grouped = df_grouped.groupby(['Date'])[fillingLvl].sum().reset_index()

    # Now plot the grouped data
    fig = px.line(filling_overview_grouped, x='Date', y=fillingLvl, markers=True)
    st.plotly_chart(fig, use_container_width=True)
    st.write(f'Average product stock: {round(filling_overview_grouped[fillingLvl].mean(), 2)}')
    st.markdown('---')


    """ TODO: 
     If container is at another place the next day but gets empty in the morning we need to track this too
      example: 
       timestamp fillingLevel place.name 
       01.01 23:00       1000        ectra          <-- this will be last day
       02.01 12:00         0         ectra          <-- we delete this entry
       02.01 23:00         0         on transport   <-- we keep this entry but it wont be calculated because it place changed
    
    """
    container_index = 0
    for container in df['container.name'].unique():
        # Create an empty DataFrame to store the concatenated data
        container_main_df = pd.DataFrame()
        container_df = df.loc[df['container.name'] == container]
        # group the data by date and save only the last entry of each day
        last_day = 0
        index = 0
        skip_counter = True 

        # Data Cleanup
        container_df = container_df.sort_values(by=['timestamp']).reset_index()
        container_df[fillingLvl] = container_df[fillingLvl].fillna(0)
        container_df['Date'] = container_df['Date'].fillna(0)
        container_df['container.name'] = container_df['container.name'].fillna(container).reset_index(drop=True)
        z = 0
        for c in container_df['place.name']:
            if z > 2:
                vl = container_df.loc[z-2, 'place.name']
                le = container_df.loc[z-1, 'place.name']
                if((vl == selected_places) and (le != selected_places) and (c == selected_places)):
                    container_df.loc[z-1, 'place.name'] = selected_places
            z=z+1
        # group the DataFrame by day using pd.Grouper()
        # Data Cleanup Ende

        for day in container_df['timestamp']:
            day_date = day.date()
            container_perday_df = container_df.loc[container_df['timestamp'] == day]
            if len(container_perday_df) >= 1:
                if index == 0 or skip_counter == True:

                    last_day = container_perday_df[fillingLvl].values[0]
                    addition = 0
                    consumption = 0
                    container_per_day_main_df = pd.DataFrame([[
                        0,
                        container,
                        container_perday_df["timestamp"].values[0],
                        day_date,
                        container_perday_df['timestamp'].dt.isocalendar().week.values[0],
                        addition,
                        consumption
                        ]], 
                        columns=["Tagesverbrauch", "container", "timestamp", "date", "Kalenderwoche", "Addition", "Consumption"]) 
                    index += 1
                    skip_counter = False
                else:
                    """ if container == 'ST-FR-0169':
                        st.write(f'Day: {day} Last_day: {last_day}') """
                    if last_day - container_perday_df[fillingLvl].values[0] < -10:
                        addition = 1
                        consumption = 0
                    elif last_day - container_perday_df[fillingLvl].values[0] > 10:
                        addition = 0
                        consumption = 1
                    else:
                        addition = 0
                        consumption = 0
                    if (abs((last_day - container_perday_df[fillingLvl].values[0])) < 10) and abs((last_day - container_perday_df[fillingLvl].values[0])) >0:
                        dif_value = 0
                    else:
                        dif_value = abs((last_day - container_perday_df[fillingLvl].values[0]))
                    container_per_day_main_df = pd.DataFrame([[
                        dif_value,
                        container,
                        container_perday_df["timestamp"].values[0],
                        day_date,
                        container_perday_df['timestamp'].dt.isocalendar().week.values[0],
                        addition,
                        consumption
                        ]], 
                        columns=["Tagesverbrauch", "container", "timestamp", "date", "Kalenderwoche", "Addition", "Consumption"]) 
                    last_day = container_perday_df[fillingLvl].values[0]
                    index += 1
                container_main_df = pd.concat([container_main_df, container_per_day_main_df])
            else:
                skip_counter = True
        # End Day Loop
        main_df = pd.concat([main_df, container_main_df])
        container_index +=1
    # End Container Loop

    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    main_df = main_df.reset_index(drop=True)
    consumption_df = main_df[main_df['Consumption'] == 1]
    addtions_df = main_df[main_df['Addition'] == 1]

    consumption_df['Weekday'] = pd.Categorical(consumption_df['timestamp'].dt.day_name(), categories=weekdays, ordered=True)
    consumption_df = consumption_df.sort_values('date')  # Sort dataframe by 'date'
    # Get the last calendar week
    last_kw = consumption_df['Kalenderwoche'].iloc[-1] - 1
    last_kw_df = consumption_df[consumption_df['Kalenderwoche'] == last_kw]

    # Sort last_kw_df by 'Weekday'
    last_kw_df = last_kw_df.sort_values('Weekday')

    gesamtverbrauch_proTag_letzte_kw = last_kw_df.reset_index().groupby('Weekday')['Tagesverbrauch'].sum().reset_index()['Tagesverbrauch'].sum()
    tagesverbrauch_lastKw_pro_tag_durchschnitt = last_kw_df.reset_index().groupby('Weekday')['Tagesverbrauch'].sum().reset_index()['Tagesverbrauch'].mean()

    tagesverbrauch_pro_tag = consumption_df.reset_index()
    tagesverbrauch_pro_tag['Weekday'] = pd.Categorical(tagesverbrauch_pro_tag['Weekday'], categories=weekdays, ordered=True)

    tagesverbrauch_pro_tag = tagesverbrauch_pro_tag.groupby('Weekday')['Tagesverbrauch'].sum().reset_index().sort_values('Weekday')

    # First KPI Row
    st.subheader('Daily consumption') 
    a1, a2 = st.columns(2)
    a1.metric('Average consumption of the last calenderweek (Week: ' + str(last_kw) + ')', value= round(tagesverbrauch_lastKw_pro_tag_durchschnitt, 2))
    a2.metric('Total consumption of the last calenderweek (Week: ' + str(last_kw) + ')', round(gesamtverbrauch_proTag_letzte_kw, 2))
    fig = px.bar(last_kw_df, x='Weekday', y='Tagesverbrauch', title='Daily consumption of the last Calenderweek')
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('---')

    # Second KPI Rows
    st.subheader('Consumption per calendar week')
    # Sort the dataframe by the "Kalenderwoche" column
    sorted_data = consumption_df.sort_values('Kalenderwoche').reset_index(drop=True)
    # Group the dataframe by the "Kalenderwoche" column and calculate the sum of the "Tagesverbrauch" column for each group
    sum_per_week = sorted_data.groupby('Kalenderwoche')['Tagesverbrauch'].sum().reset_index()
    sum_per_week = sum_per_week[sum_per_week['Tagesverbrauch'] > 10].reset_index()
    # Calculate the mean of the "Tagesverbrauch" column
    mean_tagesverbrauch = sum_per_week['Tagesverbrauch'].mean()
    b1, b2 = st.columns(2)
    b1.metric('Average consumption per calenderweek' , value= round(float(mean_tagesverbrauch), 2))
    b2.metric('Maximum consumption per calendar week (Calenderweek: ' + str(sum_per_week[sum_per_week['Tagesverbrauch'] == sum_per_week['Tagesverbrauch'].max()].reset_index()['Kalenderwoche'][0]) + ')', value= round(sum_per_week['Tagesverbrauch'].max(), 2))
    fig = px.bar(sum_per_week, x='Kalenderwoche', y='Tagesverbrauch')
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('---')
    
    # Third KPI Rows
    st.subheader('Total time period')
    c1, c2 = st.columns(2)
    
    max_consumption_day = str(consumption_df.reset_index().groupby('date')['Tagesverbrauch'].sum().idxmax())
    max_consumption_value = round(consumption_df.reset_index().groupby('date')['Tagesverbrauch'].sum().max(), 2)



    c1.metric('Consumption on average per day', round(consumption_df.reset_index().groupby('date')['Tagesverbrauch'].sum().reset_index()['Tagesverbrauch'].mean(), 2))
    c2.metric(f'Maximum consumption of one day ({max_consumption_day})', value=max_consumption_value)
    #c2.metric('Maximaler Verbrauch eines Tages', value= round(consumption_df.reset_index().groupby('timestamp')['Tagesverbrauch'].sum().reset_index()['Tagesverbrauch'].max(), 2))
    # Create the Plotly line chart
    fig = px.bar(tagesverbrauch_pro_tag, x="Weekday", y='Tagesverbrauch')
    # Update the layout of the chart
    fig.update_layout(
        title='Consumption overview | Standort: ' + selected_places + ' | Produkt: ' + selected_product,
        xaxis_title='Weekday',
        yaxis_title='Consumption'
    )
    # Plot!
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('---')

    csv = sum_per_week.to_json()
    st.download_button(
        key='Consumption',
        label='Download CSV File',
        data=csv,
        file_name='Consumption_export.json',
        )

    st.subheader('Delivery Chart')
    # Create the Plotly line chart
    fig = px.bar(addtions_df, x="Kalenderwoche", y='Tagesverbrauch')
    # Update the layout of the chart
    fig.update_layout(
        title='Standort: ' + selected_places + ' | Produkt: ' + selected_product,
        xaxis_title='Calenderweek',
        yaxis_title='Delivery'
    )
    # Plot!
    st.plotly_chart(fig, use_container_width=True)
    csv = addtions_df.to_csv().encode('utf-8')
    st.download_button(
        key='Additions',
        label='Download CSV File',
        data=csv,
        file_name='Additions_export.csv',
        mime='text/csv',
        )
    st.markdown('---')

def app(df):
    selected_places         = None
    selected_product        = None
    selected_container      = None
    selected_container_type = None
    all_containers          = True
    # Data Cleaning
    df.sort_values(by=['timestamp'])
    df = fillingLevelCleanUpForecast.app(df)
    with st.sidebar:
        unique_places = df['place.name'].unique()

        df['timestamp'] = pd.to_datetime(df['timestamp'])  # ensure datetime format
        unique_years = sorted(df['timestamp'].dt.year.unique())  # extract unique years
        selected_year = st.radio('Select Year', unique_years)
        # filter dataframe for selected year
        df = df[df['timestamp'].dt.year == selected_year]
        df.reset_index(inplace=True, drop=True)
        subset_df = df
        # Select Place
        selected_places = st.selectbox('Select the place you want to observe', unique_places)
        if selected_places is not None:
            subset_df = subset_df.loc[df['place.name'] == selected_places]
            unique_products = subset_df['containerData.productName'].unique()
            # Select Product available at place
            selected_product = st.selectbox('Please select the Product you want to forecast at ' + selected_places, unique_products)
            if selected_product is not None:
                # Select Container types available at place with Product
                subset_df = subset_df.loc[df['containerData.productName'] == selected_product]
                unique_containers_types = subset_df['container.containerType.name'].unique()
                selected_container_type = st.multiselect('Select the Containertypes you want to observe', unique_containers_types, default=unique_containers_types)
                slcFil = st.radio('Select your Filling Level Unit', ['weight', 'volume'])
                if slcFil == 'weight':
                    fillingLvl = 'fillingLevel.weight'
                if slcFil == 'volume':
                    fillingLvl = 'fillingLevel.volume'

                subset_df = subset_df.loc[df['container.containerType.name'].isin(selected_container_type)]
                unique_containers = subset_df['container.name'].unique()
                specific_container = st.checkbox('I want to select specific containers (Default: All container)')
                if specific_container:
                    selected_container = st.multiselect('Please select all containers you want in the forecast', unique_containers)
                    all_containers = False
                    if len(selected_container) > 0:
                        subset_df = subset_df.loc[df['container.name'].isin(selected_container)]
                else:
                    selected_container = unique_containers

    if selected_places is not None and selected_product is not None and len(selected_container_type) > 0:
        subset_df = subset_df.loc[df['container.name'].isin(selected_container)]
        #Convert timestamp to datetime
        subset_df['timestamp'] = subset_df['timestamp'].apply(pd.to_datetime)
        #Reset index and sort by time
        subset_df.sort_values(by='timestamp', ascending=True, inplace = True)
        subset_df.reset_index(drop=True, inplace=True)
        # Define a lambda function to convert each datetime string to formatted date string
        # Convert the 'timestamp' column to a datetime format, excluding the first row if it is a DatetimeIndex
        if isinstance(df['timestamp'][0], pd.DatetimeIndex):
            df['date'] = df['timestamp'].iloc[1:].astype(str).apply(lambda x: datetime.fromisoformat(x[:-6]).strftime("%y-%m-%d"))
        else:
            df['date'] = df['timestamp'].astype(str).apply(lambda x: datetime.fromisoformat(x[:-6]).strftime("%y-%m-%d"))
        user_df = pd.DataFrame(df, columns=['Date', 'Product', 'Fillinglevel percent', 'Place' 'Devicename', 'Containername', 'Coordinates'])
        try:
            consumption(subset_df, selected_places, selected_product, selected_container, all_containers, fillingLvl)
        except:
            st.warning('No consumption found for your selection!')