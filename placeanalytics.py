import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import requests
from streamlit_lottie import st_lottie

import json

import pydeck as pdk
import addFilterToDataframe
import fillingLevelCleanUp


def split_in_3(data):
    result = []
    for i in range(0, len(data), 3):
        group = data[i:i+3]
        result.append(group)
    return result

def convert_df_csv(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('utf-8')

def filter_duration(df):
        filter_query1= ''
        filter_type_value = st.selectbox("Filter duration:", ['lower than', 'greater than', 'equal'], key='type-filter')
        amount = st.number_input("Enter amount:", value=0,key='amount')
        for i in df['Duration']:
            if filter_type_value:
                if filter_type_value == 'lower than':
                    filter_query1 += f"`{i}` < {amount} & "
                elif filter_type_value == 'greater than':
                    filter_query1 += f"`{i}` > {amount} & "
                elif filter_type_value == 'equal':
                    filter_query1 == f"`{i}` < {amount} & "
        filter_query1 = filter_query1[:-3]  # remove the last ' & '
        filtered_df = df.query(filter_query1)
        return filtered_df
    
def filterplaces(df):
    places = df['place.name'].unique()
    containers = df['container.name'].unique()

    with st.sidebar:
            selectPlace = st.multiselect('Select the places you would like to observe', places, key='place', default=places)
            #selectContainers = st.multiselect('Select the containers you would like to observe', containers, key='container', default=containers)
            if selectPlace is not None:
                df_filter = df[df['place.name'].isin(selectPlace)]
            """ if selectContainers is not None:
                df_filter = df[df['container.name'].isin(selectContainers)]
            selectState = st.multiselect('Select the Filling Level State you would like to observe', ['Full', 'operative', 'empty'], default=['Full', 'operative', 'empty'])
            if selectState is not None:
                df_filter = df_filter[df_filter['fillingLevel.state'].isin(selectState)] """
            st.markdown('---')
            selectState = ['Full', 'operative', 'empty']
            selectContainers = containers
    return df_filter, selectPlace, selectState, selectContainers

def containerStayDuration(df):
    all_container_data = pd.DataFrame()
    df, slc_places, selectState, selectContainers = filterplaces(df)
    df['container.name'].isin(selectContainers)
    grouped_containers = df.groupby('container.name')
    
    for container, container_df in grouped_containers:
        filtered_df = df[df['container.name'] == container]
        filtered_df = filtered_df.sort_values(by='timestamp').drop_duplicates(subset=['Date'],keep='last')
        filtered_df.reset_index(inplace=True, drop=True)
        filtered_df = fillingLevelCleanUp.app(filtered_df, slc_places)
        filtered_df = filtered_df.groupby(['place.name', 'container.name','fillingLevel.state']).size().reset_index(name='Stay in days')
        all_container_data = pd.concat([all_container_data, filtered_df])
    
    # Calculate the total duration of time and count the number of visits for each container at each place
    total_duration = all_container_data.groupby(['place.name'])['Stay in days'].sum().reset_index()
    total_duration.columns = ['Places', 'Stay in days']
    total_duration['Stay in days'] = total_duration['Stay in days'].astype('int')

    #Stay per filling Level State
    #Container Count  mit in Tabelle auf
    total_duration_state = all_container_data.groupby(['place.name','fillingLevel.state'])['Stay in days'].sum().reset_index()
    #st.dataframe(total_duration_state)
    total_duration_state.columns = ['Place', 'Filling Level State', 'Stay in days']
    total_duration_state['Stay in days'] = total_duration_state['Stay in days'].astype('int')
    all_container_data.reset_index(drop=True, inplace=True)

    """ Calculating Avg based on Container, Place and State """
    # Create an empty dataframe to store the results
    result_df = pd.DataFrame(columns=['Place', 'State', 'Stay in days (Avg)'])

    # Loop through each place and state combination
    for place in slc_places:
        for state in selectState:
            # Filter the data by place and state
            filtered_data = all_container_data[(all_container_data['place.name'] == place) & (all_container_data['fillingLevel.state'] == state)]
            # Calculate the average stay duration
            avg_stay = round(filtered_data['Stay in days'].mean(), 2)
            # Append the result to the result dataframe
            new_row = pd.DataFrame({'Place': place, 'State': state, 'Stay in days (Avg)': avg_stay}, index=[0])
            result_df = pd.concat([result_df, new_row], ignore_index=True)


    # Display the result dataframe
    new_df = result_df.dropna(subset=['Stay in days (Avg)'])
    
    """ Mergin Dataframes together """
    # Assuming 'new_df' is the dataframe containing the new data
    # Assuming 'total_duration_state' is the dataframe containing the old data
    merged_df_with_avg = pd.merge(total_duration_state, new_df, how='left', left_on=['Place', 'Filling Level State'], right_on=['Place', 'State'])

    # Drop the 'State' column as it is no longer needed
    merged_df_with_avg.drop('State', axis=1, inplace=True)
    # Drop rows with NaN values
    merged_df_with_avg.dropna(subset=['Stay in days'], inplace=True)

    # Set the index to 'Place' and 'Filling Level State'


    export_start = df['Date'].iloc[0]
    export_start = pd.to_datetime(export_start)
    export_start_str = export_start.strftime("%d.%m.%Y")
    export_end = df['Date'].iloc[-1]
    export_end = pd.to_datetime(export_end)
    export_end_str = export_end.strftime("%d.%m.%Y")

    container_in_obs = all_container_data['container.name'].unique()
    # First KPI Row
    a1, a2 = st.columns(2)
    a1.metric('Export Start Time', export_start_str)
    a2.metric('Export End Time', export_end_str)
#
    # Second KPI Row
    col1, col2 = st.columns(2)
    with col1:
        col1.metric('Amount of containers in obversation', len(container_in_obs))
        with st.expander('Container in observation'):
            st.dataframe(all_container_data['container.name'].unique(), use_container_width=True)

    with col2:
        col2.metric('Amount of supplied places/customers', len(all_container_data['place.name'].unique()))
        with st.expander('Places/Customers list'):
            st.dataframe(all_container_data['place.name'].unique(), use_container_width=True)
#
    merged_df_with_avg[['Stay in days', 'Stay in days (Avg)']] = merged_df_with_avg[['Stay in days', 'Stay in days (Avg)']].astype(float)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader('Total Duration per Filling Level State')
        #total_duration_state = filter_duration(total_duration_state)
        with st.expander('Complete List'):
            st.dataframe(merged_df_with_avg, use_container_width=True)
        #fig_fil_state_cont_histo = px.histogram(total_duration_state, x='Place', y='Filling Level State', color='Duration',barmode='group', width=800, title="Data Stuff")
        fig_fil_state_cont_bar = px.bar(merged_df_with_avg, x='Place', y='Stay in days', color='Filling Level State', title="Total Duration")
        st.plotly_chart(fig_fil_state_cont_bar, use_container_width=True)
        # create a streamlit button to download the csv file

        csv = convert_df_csv(merged_df_with_avg)
        st.download_button(
            label='Download CSV File',
            data=csv,
            file_name='Packwiseflow_Cycle_export.csv',
            mime='text/csv',
            )

    with c2:
        st.subheader('Average Duration per Filling Level State')
        #total_duration_state = filter_duration(total_duration_state)
        with st.expander('Complete List'):
            st.dataframe(merged_df_with_avg, use_container_width=True)
        #fig_fil_state_cont_histo = px.histogram(total_duration_state, x='Place', y='Filling Level State', color='Duration',barmode='group', width=800, title="Data Stuff")
        fig_fil_state_cont_bar = px.bar(merged_df_with_avg, x='Place', y='Stay in days (Avg)', color='Filling Level State', text='Stay in days (Avg)', title="Average Duration")
        st.plotly_chart(fig_fil_state_cont_bar, use_container_width=True)


    placeContainerCount(df, slc_places, export_start_str, export_end_str, merged_df_with_avg, container_in_obs)

def load_lottieurl(url :str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()


def placeContainerCount(df, slc_places, export_start_str, export_end_str, merged_df_with_avg, container_in_obs):
    df = df.reset_index(drop=True)
    all_container_data = pd.DataFrame()
    grouped_containers = df.groupby('container.name')
    for container, container_df in grouped_containers:
        filtered_df = df[df['container.name'] == container]
        filtered_df = filtered_df.sort_values(by='timestamp').drop_duplicates(subset=['Date'],keep='last')
        filtered_df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        filtered_df.reset_index(inplace=True, drop=True)
        #Cleaning Container data
        cleaned_ContainerData = fillingLevelCleanUp.app(filtered_df, slc_places)
        container_place = cleaned_ContainerData.groupby(['container.name','place.name', 'fillingLevel.state'])['Date'].nunique().reset_index()
        ###Debug
        #st.dataframe(container_place)
#
        all_container_data = pd.concat([all_container_data, container_place])
    
    #all_container_data = all_container_data.sort_values(by='Date')
    all_container_data = all_container_data.reset_index(drop=True)


    ####Debug
    #st.dataframe(all_container_data, use_container_width=True)
    st.dataframe(addFilterToDataframe.filter_dataframe(all_container_data, False, 1), use_container_width=True)
    for place in slc_places:
        plc_ovw = all_container_data.loc[all_container_data['place.name'] == place]
        plc_ovw = plc_ovw.reset_index(drop=True)
        plc_ovw = plc_ovw.rename(columns={'container.name':'container name','place.name':'location', 'Date':'Stay time'})
        st.subheader(f'Overview per container and standing time per fill level status for location: {place}')
        st.dataframe(addFilterToDataframe.filter_dataframe(plc_ovw, False, 0), use_container_width=True)
    
    """ st.subheader('Overview of container arriving or leaving places')
    #pro container machen


    df1 = df.drop_duplicates(subset=['container.name', 'place.name', 'Date'], keep='last')
    stays = df1.groupby(['container.name', 'place.name'])['Date'].nunique()
    ###Debug
    st.dataframe(stays)
    # Sum up the counts for each place
    total_counts = stays.groupby('place.name').sum().reset_index(name='count')
    ###Debug
    st.dataframe(total_counts)

    # Shift the container ID and place name columns by one row, grouping by place name
    df = df.drop_duplicates(subset=['container.name', 'place.name'], keep='last')
    df_shifted = df.groupby('place.name')[['container.name']].shift(-1)
    # Merge the shifted data with the original data
    
    df_merged = pd.concat([df[['container.name', 'place.name']], df_shifted], axis=1)
    # Drop rows where the container ID or place name is missing
    df_merged = df_merged.dropna()
    # Count the number of times each container leaves each place
    leaves = df_merged.groupby('place.name').size().reset_index(name='count')
    merged_df = pd.merge(total_counts, leaves, on='place.name')
    merged_df.columns = ['Places', 'Amount containers traveled too', 'Amount containers left y'] 
    c1,c2 = st.columns(2)
    with c1:
        st.dataframe(merged_df, use_container_width=True)
    with c2:
        lottie_data = load_lottieurl('https://assets6.lottiefiles.com/packages/lf20_qp1q7mct.json')
        st_lottie(
            lottie_data,
            height=250,
            loop=False)
    st.markdown('---') """


def app(df):
    #places = df['place.name'].unique()
    #select_plc = st.multiselect('Select the places you want to observe', places)
    #placeContainerCount(df, select_plc)
    sub_menu = st.sidebar.selectbox(
            "Select the Dashboard you would like to see",
            ('Standzeiten', 'FiFo'), key='place_main'
        )
    if sub_menu == 'Standzeiten':
        try:
            containerStayDuration(df)
        except:
            st.warning('No data found for your selection!')
    if sub_menu == 'FiFo':
        try:
            containerStayDuration(df)
        except:
            st.warning('No data found for your selection!')