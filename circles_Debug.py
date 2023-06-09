from pandas.api.types import (
    is_categorical_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)

import streamlit as st
import pandas as pd
import plotly.express as px
import networkx as nx
import matplotlib.pyplot as plt
import datetime as dt
import numpy as np
import plotly.graph_objs as go
import plotly.io as pio
from io import BytesIO
import base64


import placecleanup 
import fillingLevelCleanUp_Circle

def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a UI on top of a dataframe to let viewers filter columns

    Args:
        df (pd.DataFrame): Original dataframe

    Returns:
        pd.DataFrame: Filtered dataframe
    """
    modify = st.checkbox("Add filters")

    if not modify:
        return styling(df)

    df = df.copy()

    # Try to convert datetimes into a standard format (datetime, no timezone)
    for col in df.columns:
        if is_object_dtype(df[col]):
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass

        if is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)

    modification_container = st.container()

    with modification_container:
        to_filter_columns = st.multiselect("Filter dataframe on", df.columns)
        for column in to_filter_columns:
            left, right = st.columns((1, 20))
            # Treat columns with < 10 unique values as categorical
            if is_categorical_dtype(df[column]) or df[column].nunique() < 10:
                user_cat_input = right.multiselect(
                    f"Values for {column}",
                    df[column].unique(),
                    default=list(df[column].unique()),
                )
                df = df[df[column].isin(user_cat_input)]
            elif is_numeric_dtype(df[column]):
                _min = float(df[column].min())
                _max = float(df[column].max())
                step = (_max - _min) / 100
                user_num_input = right.slider(
                    f"Values for {column}",
                    min_value=_min,
                    max_value=_max,
                    value=(_min, _max),
                    step=step,
                )
                df = df[df[column].between(*user_num_input)]
            elif is_datetime64_any_dtype(df[column]):
                user_date_input = right.date_input(
                    f"Values for {column}",
                    value=(
                        df[column].min(),
                        df[column].max(),
                    ),
                )
                if len(user_date_input) == 2:
                    user_date_input = tuple(map(pd.to_datetime, user_date_input))
                    start_date, end_date = user_date_input
                    df = df.loc[df[column].between(start_date, end_date)]
            else:
                user_text_input = right.text_input(
                    f"Substring or regex in {column}",
                )
                if user_text_input:
                    df = df[df[column].astype(str).str.contains(user_text_input)]

    return styling(df)

def dataframeCleanup(df):
    
    df['startdate'] = df['startdate'].dt.date
    df['enddate'] = df['enddate'].dt.date
    return df

def convert_df_csv(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('utf-8')

def convert_df_xlsx(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_excel()


def styling(df):

    #### Styling
    cols_to_highlight = df.columns[4:]
    styledData = df.style.background_gradient(subset=cols_to_highlight)
    return styledData

def removeIndex(df):
    hide_table_row_index = """
            <style>
            thead tr th:first-child {display:none}
            tbody th {display:none}
            </style>
            """

    # Inject CSS with Markdown
    st.markdown(hide_table_row_index, unsafe_allow_html=True)

    # Display a static table
    #st.table(df)
    return df


def circlecalculation(df, containers, start_place, selected_places, slc_container_types, places_in_observation):
    allContainer_circle_fillstate = pd.DataFrame()
    for container in containers:
        df_container = df.loc[df['container.name'] == container]

        places_of_container = df_container['place.name'].unique()
        containertypes_of_container = df_container['container.containerType.name'].unique()
        ###Place Check
        place_check = all(item in list(places_of_container) for item in list(selected_places))
        if place_check == False:
            continue
        #### Filter nochmal je cycle for places
        container_type_check = all(item in list(containertypes_of_container) for item in list(slc_container_types))
        if container_type_check == False:
            continue
        df_container = df_container.sort_values(by='timestamp').drop_duplicates(subset=['Date'],keep='last')
        df_container.reset_index(inplace=True, drop=True)
        df_container = placecleanup.app(df_container)
        df_container = fillingLevelCleanUp_Circle.app(df_container, start_place)

        full_mask = df_container['fillingLevel.percent'] >= 90
        in_use_mask = (df_container['fillingLevel.percent']) < 90 & (df_container['fillingLevel.percent'] > 10)
        empty_mask = df_container['fillingLevel.percent'] <= 10
        # Use NumPy's where function to assign values based on the conditions
        df_container['fillingLevel.state'] = np.where(full_mask, 'Full', np.where(empty_mask, 'empty', 'operative'))

        ####Definition of Routes 
        # Iterate through each container's measurements and keep track of location
        df_container['Cycle_State'] = ''
        df_container['circle'] = ''
        df_container['Cycle_started'] = ''
        df_container['Cycle_ended'] = ''
        cycle_started = False
        cycle_ended = False
        cycle_counter = 1
        singleCircleTimeCalc = {'circle':[], 'startdate':[], 'enddate':[]}



        for idx, row in df_container.iterrows():
            if idx+3 >= len(df_container):
                break
            
            if ((df_container.loc[idx, 'place.name'] == 'on Transport' and df_container.loc[idx, 'fillingLevel.state'] == 'empty') and
                (df_container.loc[idx+1, 'place.name'] == 'on Transport' and df_container.loc[idx, 'fillingLevel.state'] == 'Full') and
                (df_container.loc[idx+2, 'place.name'] == start_place and df_container.loc[idx+2, 'fillingLevel.state'] == 'Full')):

                df_container.loc[idx+1, 'fillingLevel.state'] = 'empty'
                df_container.loc[idx+2, 'fillingLevel.state'] = 'empty'

            if (df_container.loc[idx+1, 'place.name'] == start_place and
                (df_container.loc[idx+2, 'place.name'] == 'on Transport' or df_container.loc[idx+2, 'place.name'] in selected_places) and
                df_container.loc[idx+1, 'fillingLevel.state'] == 'empty' and
                df_container.loc[idx+2, 'fillingLevel.state'] == 'Full'):

                df_container.loc[idx+1, 'fillingLevel.state'] = 'Full'

            if (row['place.name'] == start_place and (df_container.loc[idx, 'fillingLevel.state'] == 'Full' or df_container.loc[idx, 'fillingLevel.state'] == 'operative') and not cycle_started):
                df_container.loc[idx, 'Cycle_State'] = 'Cycle Start'
                cycle_started = True
                cycle_ended = False
                df_container.loc[idx, 'circle'] = f'{cycle_counter}'
                df_container.loc[idx, 'Cycle_started'] = cycle_started
                df_container.loc[idx, 'Cycle_ended'] = cycle_ended
                singleCircleTimeCalc['circle'].append(str(cycle_counter))
                singleCircleTimeCalc['startdate'].append(df_container.loc[idx, 'Date'])
                singleCircleTimeCalc['enddate'].append(None)
                

            elif ((df_container.loc[idx+1, 'place.name'] == start_place and\
                    (df_container.loc[idx, 'fillingLevel.state'] == 'empty' or df_container.loc[idx, 'fillingLevel.state'] == 'operative') and\
                    (df_container.loc[idx+1, 'fillingLevel.state'] == 'Full' or df_container.loc[idx+1, 'fillingLevel.state'] == 'operative')) and
                    cycle_started):
                df_container.loc[idx, 'Cycle_State'] = 'Cycle End'
                df_container.loc[idx, 'circle'] = f'{cycle_counter}'             
                if len(singleCircleTimeCalc['enddate']) > 0:
                    singleCircleTimeCalc['enddate'][-1] = df_container.loc[idx, 'Date']
                cycle_ended = True
                cycle_started = False
                df_container.loc[idx, 'Cycle_started'] = cycle_started
                df_container.loc[idx, 'Cycle_ended'] = cycle_ended
                cycle_counter += 1

            elif (row['place.name'] != start_place and not cycle_ended and not cycle_started) or (row['place.name'] == start_place and not cycle_ended and not cycle_started):
                df_container.loc[idx, 'Cycle_State'] = 'Unknown Cycle'
                df_container.loc[idx, 'Cycle_started'] = cycle_started
                df_container.loc[idx, 'Cycle_ended'] = cycle_ended
                cycle_started = False
                cycle_ended = False
            else:
                df_container.loc[idx, 'Cycle_State'] = 'In Cycle'
                df_container.loc[idx, 'circle'] = f'{cycle_counter}'

        df_container['Date'] = pd.to_datetime(df_container['Date'])
        
        ####Debug
        st.dataframe(df_container, use_container_width=True)

        #Circle Overview
        singleCircleOverview = pd.DataFrame(singleCircleTimeCalc)
        singleCircleOverview['startdate'] = pd.to_datetime(singleCircleOverview['startdate'], dayfirst=True)
        singleCircleOverview['enddate'] = pd.to_datetime(singleCircleOverview['enddate'],  dayfirst=True)
        singleCircleOverview['Total Duration'] = singleCircleOverview['enddate'] - singleCircleOverview['startdate']
        singleCircleOverview['Total Duration'] = singleCircleOverview['Total Duration'].dt.days
        singleCircleOverview['Total Duration'] = singleCircleOverview['Total Duration']+1
        
        #st.dataframe(singleCircleOverview)
        
        if singleCircleOverview.isnull().values.any():
            singleCircleOverview = singleCircleOverview.dropna()

        # iterate through the rows of complete_circles, before check if there are any NaN values
        all_circle_fillstate = pd.DataFrame()

        for idy, row1 in singleCircleOverview.iterrows():
            try:
                df_subset = df_container[(df_container['Date'] >= row1['startdate']) & (df_container['Date'] <= row1['enddate'])]
                unique_places_in_subset = df_subset['place.name'].unique()
                places_in_observation.extend(unique_places_in_subset)
                ## Debug
                #st.dataframe(df_subset)
                time_Ovw = df_subset.groupby(['container.name', 'place.name','fillingLevel.state', 'circle']).size().reset_index(name='Stay Time')
                ## Debug
                st.dataframe(time_Ovw)
                # merge the two dataframes on the 'circle' column
                merged_df = pd.merge(time_Ovw, singleCircleOverview, on='circle')
                merged_df['Stay Time'] = merged_df['Stay Time'].astype('int')
                # create a new column with a unique identifier for each combination of 'place.name' and 'fillingLevel.state'
                merged_df['place_filling'] = 'Days at' + ' ' + merged_df['place.name'] + ' ' + merged_df['fillingLevel.state']
                merged_df = merged_df.reindex(sorted(merged_df.columns), axis=1)
                
                ## Debug
                st.dataframe(merged_df)
                # create a pivot table with 'circle', 'startdate', and 'enddate' as index columns, and 'place_filling' as a column
                pivot_df = pd.pivot_table(merged_df, values='Stay Time', index=['startdate', 'enddate', 'container.name', 'circle', 'Total Duration'], columns=['place_filling'])
                # reset the index and rename the columns to remove the multi-level column index
                df3 = pivot_df.reset_index()
                df3.columns.name = None
                # display the resulting dataframe
                all_circle_fillstate = pd.concat([all_circle_fillstate, df3])
                
                ## Debug 
                st.dataframe(all_circle_fillstate)

            except IndexError:
                pass
        #Pass each place , fillingState as column to singleCircleOverview
        #st.write('Overview Circles')
        for i in all_circle_fillstate.columns:
            try:
                all_circle_fillstate[[i]] = all_circle_fillstate[[i]].astype(np.float64).apply(np.int64)
            except:
                pass
        #st.write(f'completed cycles ')
        #st.dataframe(all_circle_fillstate)
        
        #st.markdown('---')
        allContainer_circle_fillstate = pd.concat([allContainer_circle_fillstate, all_circle_fillstate], ignore_index=True)
        
    for i in allContainer_circle_fillstate.columns:
            try:
                allContainer_circle_fillstate[[i]] = allContainer_circle_fillstate[[i]].astype(np.float64).apply(np.int16)
                #allContainer_circle_fillstate[[i]] = allContainer_circle_fillstate[[i]].astype('int')
            except:
                pass  
    
    # Dataframe reindexing
    df_start = allContainer_circle_fillstate.columns[:5]
    df_start= allContainer_circle_fillstate[df_start]
    
    #### Sorting
    df_ohne_5 = allContainer_circle_fillstate.columns[5:]
    marcsdf = allContainer_circle_fillstate[df_ohne_5]
    marcsdf = marcsdf.reindex(sorted(marcsdf.columns), axis=1)

    allContainer_circle_fillstate = pd.concat([df_start, marcsdf],axis=1)
    allContainer_circle_fillstate = dataframeCleanup(allContainer_circle_fillstate)
    containers_in_observation = allContainer_circle_fillstate['container.name'].unique()

    # Split Dataframe into two 
    df_ohne_5 = allContainer_circle_fillstate.columns[5:]
    df_bis_5 = allContainer_circle_fillstate.columns[:5]
    # Create new Dataframes and relevant cols
    cols = allContainer_circle_fillstate.columns[5:].tolist()
    index_dataframe = allContainer_circle_fillstate[df_bis_5]
    observation_dataframe = allContainer_circle_fillstate[df_ohne_5]
    # select only the columns that contain the strings in selected_list
    new_list = [column for column in cols if any(substring in column for substring in selected_places)]
    # Merge two Dataframes back together
    marcsdf = allContainer_circle_fillstate[new_list]
    marcsdf = marcsdf.reindex(sorted(marcsdf.columns), axis=1)
    index_dataframe = allContainer_circle_fillstate[df_bis_5]
    allContainer_circle_fillstate = pd.concat([index_dataframe, marcsdf],axis=1)

    return allContainer_circle_fillstate, places_in_observation, df_subset, time_Ovw, all_circle_fillstate, containers_in_observation, start_place
        

def app(df):
    st.subheader('Circles')
    menu = st.radio('Menu:',['Show Circle Analytics','Show Network Graph'], horizontal=True)
    if menu == 'Show Circle Analytics':

        additional_place = None
        container_types = None
        start_place = None
        circleAnalytics = None

        unique_places = df['place.name'].unique()
        containers = df['container.name'].unique()
        c1, c2, c3 = st.columns(3)
        with c1:
            start_place = st.selectbox('Select Start Place for calculating cycle', unique_places)
        with c2:
            additional_place = st.multiselect('Select addtional places which are in the cycle', unique_places)
            selected_places = additional_place
            selected_places.append(start_place)
        with c3:
            container_types = df['container.containerType.name'].unique()
            slc_container_types = st.multiselect('Select the containertypes', container_types)                     
        df = pd.DataFrame(df, columns=['timestamp', 'container.name', 'containerData.productName', 'place.name', 'fillingLevel.percent','fillingLevel.state', 'Date', 'container.containerType.name'])
        places_in_observation = [] 

        #if st.button('Start Analytics', key='Start-Analytics'):
        specific_container = st.checkbox('I want to select specific containers (Default: All container)')
        if specific_container:
            containers = st.multiselect('Please select all containers you want in the calculation', containers)
        st.markdown('---')
        if start_place is not None and (len(additional_place) > 1) and (len(slc_container_types) != 0):
                if st.button('Start Analytics', key='Start-Analytics'):                     
                    circleAnalytics = circlecalculation(df, containers, start_place, selected_places, slc_container_types, places_in_observation)
        if circleAnalytics is not None:
            df_circleAnalytics = circleAnalytics[0]
            places_in_observation = circleAnalytics[1]
            places_in_observation = list(set(places_in_observation))
            containers_in_observation = circleAnalytics[5]
            start_place = circleAnalytics[6]
            longestCycle = df_circleAnalytics['Total Duration'].max()
            shortesCycle = df_circleAnalytics['Total Duration'].min()
            meanCycle = df_circleAnalytics['Total Duration'].mean()
            meanCycle = meanCycle.astype('int')
            circleAnalytics = pd.DataFrame(df_circleAnalytics)

            ### Overview
            c1, c2 = st.columns(2)
            with c1:
                export_start = df['Date'].iloc[0]
                export_start = pd.to_datetime(export_start)
                export_start_str = export_start.strftime("%d-%m-%Y")
                c1.metric('Export Start Time', export_start_str)
            with c2:
                export_end = df['Date'].iloc[-1]
                export_end = pd.to_datetime(export_end)
                export_end_str = export_end.strftime("%d-%m-%Y")
                c2.metric('Export End Time', export_end_str)
            st.markdown('---')
            col0, col1, col2, col3, col4 = st.columns(5)
            with col0:
                col0.metric('Amount of containers in obversation', len(containers_in_observation))
                with st.expander('container in observation'):
                    st.dataframe(containers_in_observation, use_container_width=True)

                places_in_observation.remove('on Transport')
                places_in_observation.remove(start_place)
                col0.metric('Amount of supplied places/customers', len(places_in_observation))
                with st.expander('Places/Customers list'):
                    st.dataframe(places_in_observation, use_container_width=True)
                st.markdown('---')
            with col1:
                col1.metric('Amount of completed cycles', len(circleAnalytics))
                #Show amount of most cycles

                st.markdown('---')
            with col2:
                col2.metric('Average duration of cycle', meanCycle)
                st.markdown('---')
            with col3:
                col3.metric('Duration of longest Cycle', longestCycle)
                st.markdown('---')
            with col4:
                col4.metric('Duration of shortest Cycle', shortesCycle)
                st.markdown('---')



            st.title('Overview')
            st.subheader('Filter Dataframe')
            st.write('You also have the option to filter the dataframe as you like')
            st.dataframe(filter_dataframe(circleAnalytics), height=700)
            # create a streamlit button to download the csv file
            csv = convert_df_csv(circleAnalytics)
            st.download_button(
                label='Download CSV File',
                data=csv,
                file_name='Packwiseflow_Cycle_export.csv',
                mime='text/csv',
                )
            st.markdown('---')

            ####Summary
            st.header('Summary & Explaination')
            t1,t2 = st.columns(2)
            with t1:
                st.subheader('Best possible cycle')
                st.text('Best theoretical possible cycle based on the minimum of all columns')
            with t2:
                st.subheader('Worst possible cycle')
                st.text('Worst theoretical possible cycle based on the maximum of all columns')
            st.markdown('---')
            ##Min Cycle
            min_cycle = df_circleAnalytics[df_circleAnalytics['Total Duration']==df_circleAnalytics['Total Duration'].min()]

            ##Max Cycle
            max_cycle = df_circleAnalytics[df_circleAnalytics['Total Duration']==df_circleAnalytics['Total Duration'].max()]

            ##Paradies DF
            min_vals = df_circleAnalytics.min()
            paradies_df = pd.DataFrame(min_vals).transpose()
            paradies_df = paradies_df.drop(columns=['startdate', 'enddate', 'container.name', 'circle', 'Total Duration']).reset_index(drop=True)
            sum_val_para = paradies_df.sum(axis=1)
            paradies_df.insert(0, 'Total Duration', sum_val_para)
            paradies_df['Total Duration'] = paradies_df['Total Duration'].astype('int')
            ###Hell Df
            max_vals = df_circleAnalytics.max()
            hell_df = pd.DataFrame(max_vals).transpose()
            hell_df = hell_df.drop(columns=['startdate', 'enddate', 'container.name', 'circle', 'Total Duration']).reset_index(drop=True)
            sum_val_hell = hell_df.sum(axis=1)
            hell_df.insert(0, 'Total Duration', sum_val_hell)
            hell_df['Total Duration'] = hell_df['Total Duration'].astype('int')

            ###Average Cycle
            avg_vals = df_circleAnalytics.mean()
            avg_df = pd.DataFrame(avg_vals).transpose()
            avg_df = avg_df.drop(columns=['circle', 'Total Duration']).reset_index(drop=True)
            sum_val_avg = avg_df.sum(axis=1)
            avg_df.insert(0, 'Total Duration', sum_val_avg)

            st.subheader('Minimal Cycle')
            st.dataframe(min_cycle)
            min_cycle = min_cycle.head(1)
            

            st.subheader('Maximum Cycle')
            st.dataframe(max_cycle)
            
            st.subheader('Best possible cycle')            
            st.dataframe(paradies_df)

            st.subheader('Worst possible cycle')
            st.dataframe(hell_df)

            st.subheader('Average Cycle')
            st.dataframe(avg_df)

            ###Chart noch darstellen, um potential aufzuzeigen
            compare_df = pd.DataFrame()
            min_cycle = min_cycle.drop(columns=['startdate', 'enddate', 'container.name', 'circle'])
            max_cycle = max_cycle.drop(columns=['startdate', 'enddate', 'container.name', 'circle'])
            compare_df = pd.concat([paradies_df,min_cycle,avg_df,max_cycle,hell_df])
            compare_df.insert(0, 'Cycle Scenario', ['best possible cycle', 'min cycle', 'avg. Cycle', 'max cycle', 'worst possible cycle'])
            compare_df.reset_index(inplace=True, drop=True)
            
            for c in compare_df.columns:
                try:
                    compare_df[[c]] = compare_df[[c]].astype(np.float64).apply(np.int16)
                    #allContainer_circle_fillstate[[i]] = allContainer_circle_fillstate[[i]].astype('int')
                except:
                    pass
            st.subheader('Overview Summary')
            st.dataframe(compare_df)
            compare_df_ohne_total = compare_df.drop(columns=['Total Duration'])

            # Create the plot
            fig_Circles = px.bar(compare_df_ohne_total, y='Cycle Scenario', x=compare_df_ohne_total.columns) 
            fig_Circles.update_layout(xaxis_title='Duration at place')
            st.plotly_chart(fig_Circles, use_container_width=True)   


    if menu == 'Show Network Graph':
        # Create a network graph
        G = nx.DiGraph()

        # Add nodes for each place
        places = df['place.name'].unique()
        for place in places:
            G.add_node(place)

        # Add edges for each container route
        routes = df.groupby('container.name')['place.name'].apply(list)
        for route in routes:
            for i in range(len(route)-1):
                G.add_edge(route[i], route[i+1])

        # Plot the graph
        fig, ax = plt.subplots()
        nx.draw(G, with_labels=True, ax=ax)
        st.pyplot(fig)