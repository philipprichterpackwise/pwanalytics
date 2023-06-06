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
import pydeck as pdk
import addFilterToDataframe
import placecleanup 
import fillingLevelCleanUp_Circle
import json


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

def split_in_3(data):
    result = []
    for i in range(0, len(data), 3):
        group = data[i:i+3]
        result.append(group)
    return result

@st.cache_data
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
            if idx+3 >= len(df_container) or ((pd.to_datetime(df_container.loc[idx + 1, 'Date'], dayfirst=True) - pd.to_datetime(df_container.loc[idx, 'Date'], dayfirst=True)).days > 10) :
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

            if (row['place.name'] == start_place and df_container.loc[idx, 'fillingLevel.state'] == 'Full' and not cycle_started):
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
        #st.dataframe(df_container, use_container_width=True)

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
                #st.dataframe(time_Ovw)
                # merge the two dataframes on the 'circle' column
                merged_df = pd.merge(time_Ovw, singleCircleOverview, on='circle')
                merged_df['Stay Time'] = merged_df['Stay Time'].astype('int')
                # create a new column with a unique identifier for each combination of 'place.name' and 'fillingLevel.state'
                merged_df['place_filling'] = 'Days at' + ' ' + merged_df['place.name'] + ' ' + merged_df['fillingLevel.state']
                merged_df = merged_df.reindex(sorted(merged_df.columns), axis=1)
                
                ## Debug
                #st.dataframe(merged_df)
                # create a pivot table with 'circle', 'startdate', and 'enddate' as index columns, and 'place_filling' as a column
                pivot_df = pd.pivot_table(merged_df, values='Stay Time', index=['startdate', 'enddate', 'container.name', 'circle', 'Total Duration'], columns=['place_filling'])
                # reset the index and rename the columns to remove the multi-level column index
                df3 = pivot_df.reset_index()
                df3.columns.name = None
                # display the resulting dataframe
                all_circle_fillstate = pd.concat([all_circle_fillstate, df3])
                
                ## Debug 
                #st.dataframe(all_circle_fillstate)

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
    additional_place = None
    container_types = None
    start_place = None
    circleAnalytics = None

    unique_places = df['place.name'].unique()
    containers = df['container.name'].unique()
    with st.sidebar:
        start_place = st.selectbox('Select Start Place for calculating cycle', unique_places)
        start_place_alone = start_place
        additional_place = st.multiselect('Select addtional places which are in the cycle', unique_places)
        output_place = additional_place
        selected_places = additional_place
        selected_places.append(start_place)
        container_types = df['container.containerType.name'].unique()
        slc_container_types = st.multiselect('Select the containertypes', container_types)
        df = pd.DataFrame(df, columns=['timestamp', 'container.name', 'containerData.productName', 'place.name', 'fillingLevel.percent','fillingLevel.state', 'Date', 'container.containerType.name', 'location.coordinates'])
        places_in_observation = [] 
        specific_container = st.checkbox('I want to select specific containers (Default: All container)')
        if specific_container:
            containers = st.multiselect('Please select all containers you want in the calculation', containers)
        st.markdown('---')
    if start_place is not None and (len(additional_place) > 1) and (len(slc_container_types) != 0):
        try:              
            circleAnalytics = circlecalculation(df, containers, start_place, selected_places, slc_container_types, places_in_observation)
        except:
            st.warning(f'No fully completed cycle found between {start_place_alone} and {output_place}')
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

        export_start = df['Date'].iloc[0]
        export_start = pd.to_datetime(export_start)
        export_start_str = export_start.strftime("%d-%m-%Y")
        export_end = df['Date'].iloc[-1]
        export_end = pd.to_datetime(export_end)
        export_end_str = export_end.strftime("%d-%m-%Y")

        ### Overview
        
        if 'on Transport' in places_in_observation:
            places_in_observation.remove('on Transport')
        
        places_in_observation.remove(start_place)
        
        # First KPI Row
        a1, a2 = st.columns(2)
        a1.metric('Export Start Time', export_start_str)
        a2.metric('Export End Time', export_end_str)

        # Second KPI Row
        col1, col2, col3 = st.columns(3)
        with col1:
            col1.metric('Amount of containers in obversation', len(containers_in_observation))
            with st.expander('Container in observation'):
                st.dataframe(containers_in_observation, use_container_width=True)

        with col2:
            col2.metric('Amount of supplied places/customers', len(places_in_observation))
            with st.expander('Places/Customers list'):
                st.dataframe(places_in_observation, use_container_width=True)

        with col3:
            col3.metric('Amount of containertypes in obversation', len(slc_container_types))  
            with st.expander('Containertypes in observation'):
                st.dataframe(slc_container_types, use_container_width=True)

        # Third KPI row
        c1, c2, c3, c4 = st.columns(4)
        c1.metric('Amount of completed cycles', len(circleAnalytics))
        c2.metric('Average duration of cycle', meanCycle)
        c3.metric('Duration of longest Cycle', longestCycle, delta=int((meanCycle - longestCycle)))
        c4.metric('Duration of shortest Cycle', shortesCycle, delta=int((meanCycle - shortesCycle)))

        st.subheader('Average Duration')
        st.write('Overview of the average stay time as Days per state and per place')
        columns = circleAnalytics.columns.tolist()[5:]
        cities = round(circleAnalytics[columns].mean(), 1).to_frame().rename(columns={0: 'Avg Days'})

        # extract the city names from the index
        cities = cities.reset_index()
        # extract state information from 'index' column
        cities['state'] = cities['index'].str.split(' ').str[-1]
        # extract city information from 'index' column
        cities['city'] = cities['index'].str.split(' ').str[2:-1].apply(lambda x: ' '.join(x))
        cities.drop(['index'], axis=1, inplace=True)

        fig = px.bar(cities, x="city", y="Avg Days", color="state", text="Avg Days")
        fig.update_traces(texttemplate='%{text}', textposition='outside')
        # Plot!
        st.plotly_chart(fig, use_container_width=True)

        """ # Third KPI Chart
        d3, d4 = st.columns(2)
        with d3:
            # Example data for 1 year
            date_range = pd.date_range('2022-01-01', '2022-12-31')
            data = pd.DataFrame({
                'Full': np.random.randint(100, 200, len(date_range)),
                'empty': np.random.randint(150, 250, len(date_range)),
                'operative': np.random.randint(50, 100, len(date_range))
            }, index=date_range)

            # Create the Plotly line chart
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=data.index, y=data['Full'], name='Full'))
            fig.add_trace(go.Scatter(x=data.index, y=data['empty'], name='empty'))
            fig.add_trace(go.Scatter(x=data.index, y=data['operative'], name='operative'))

            # Update the layout of the chart
            fig.update_layout(
                title='Example Time Series Data for 1 Year',
                xaxis_title='Date',
                yaxis_title='Values',
                legend_title='Status'
            )
            # Plot!
            st.plotly_chart(fig, use_container_width=True)
        with d4:
            df = px.data.gapminder().query("year==2007")
            fig = px.scatter_geo(df, locations="iso_alpha", color="continent",
                                hover_name="country", size="pop",
                                projection="winkel3")
            st.plotly_chart(fig, use_container_width=True) """

        st.subheader('Filter Dataframe')
        st.write('You also have the option to filter the dataframe as you like')
        st.dataframe(addFilterToDataframe.filter_dataframe(circleAnalytics, True, 4), height=700)
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
        min_json = min_cycle
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
        cols = df_circleAnalytics.columns[3:]
        avg_vals = df_circleAnalytics[cols].mean()
        avg_df = pd.DataFrame(avg_vals).transpose()
        avg_df = avg_df.drop(columns=['circle', 'Total Duration']).reset_index(drop=True)
        sum_val_avg = avg_df.sum(axis=1)
        avg_df.insert(0, 'Total Duration', sum_val_avg)


        ###Chart noch darstellen, um potential aufzuzeigen
        compare_df = pd.DataFrame()
        min_cycle = min_cycle.drop(columns=['startdate', 'enddate', 'container.name', 'circle'])
        max_cycle = max_cycle.drop(columns=['startdate', 'enddate', 'container.name', 'circle'])
        compare_df = pd.concat([paradies_df,min_cycle,avg_df,max_cycle.head(1),hell_df])
        # repeating the list to match DataFrame's length
        cycle_scenarios = ['best possible cycle', 'min cycle', 'avg. Cycle', 'max cycle', 'worst possible cycle'] * len(compare_df)

        # truncating the list to match DataFrame's length
        cycle_scenarios = cycle_scenarios[:len(compare_df)]

        # inserting the column
        compare_df.insert(0, 'Cycle Scenario', cycle_scenarios)
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
