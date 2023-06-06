import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import fillingLevelCleanUp

maxVolume = 'container.containerType.maxVolume'

def convert_df_csv(df):
    return df.to_csv().encode('utf-8')


def fillingLevel(df):
    with st.sidebar:
        slcFil = st.radio('Select your Filling Level Unit', ['weight', 'volume'])
        if slcFil == 'weight':
            fillingLvl = 'fillingLevel.weight'
        if slcFil == 'volume':
            fillingLvl = 'fillingLevel.volume'
        places = df['place.name'].unique()
        slc_places = st.multiselect('Select the places you want to observe', places)
        st.markdown('---')
    #containers = df['container.name']
    #slc_container = st.multiselect('Select the container', containers)
    """ container_type_check = all(item in list(containertypes_of_container) for item in list(slc_container_types))
    if container_type_check == False:
        continue """
    all_container_data = pd.DataFrame()
    grouped_containers = df.groupby('container.name')

    ##Max Filling Level je Container mit aufnehmen 
    for container, container_df in grouped_containers:
        filtered_df = df[df['container.name'] == container]
        filtered_df = filtered_df.sort_values(by='timestamp').drop_duplicates(subset=['Date'],keep='last')
        filtered_df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        filtered_df.reset_index(inplace=True, drop=True)
        cleaned_ContainerData = fillingLevelCleanUp.app(filtered_df, slc_places)
        all_container_data = pd.concat([all_container_data, cleaned_ContainerData])
    
    all_container_data = all_container_data.sort_values(by='Date')
    all_container_data = all_container_data.reset_index(drop=True)
    ####Debug
    
    #Hier muss noch das per Place und product und datum der füllstand aggregiert werden.
    # group by place, product, and timestamp and aggregate filling level per container
    agg_data = all_container_data.groupby(['Date','place.name', 'containerData.productName'])[[maxVolume, fillingLvl]].sum().reset_index()
    agg_data = agg_data.sort_values(by='Date')
    agg_data = agg_data.reset_index(drop=True)
    agg_data[fillingLvl] = agg_data[fillingLvl].astype('int')
    agg_data['Anteil von max Volume'] = (agg_data[fillingLvl]/agg_data[maxVolume])*100
    
    # Create new Df to store dataframes
    df_list = []
    #create a plot for each place and show consumption for each place
    ## consumption = added + negative
    keycounter = 0
    for place in slc_places:
        st.subheader(place)
        #allcontainer data has already the last timestamp per container
        data = agg_data.loc[agg_data['place.name'] == place]
        data = data.reset_index(drop=True)
        
        #add week 
        data['week'] = data['Date'].dt.isocalendar().week
        #Add Diff Column
        data['diff %'] = data['Anteil von max Volume'].diff()
        data['diff'] = data[fillingLvl].diff()
        data['consumption'] = data['diff'].apply(lambda x: x if x < 0 else 0)
        data['additions'] = data['diff'].apply(lambda x: x if x > 10 else 0)
        data['additions %'] = data['diff %'].apply(lambda x: x if x > 5 else 0)
        data['additions Anteil'] = (data['additions %']/100)*data[fillingLvl]
        data['additions'] = data['additions'].astype('int')
        data = data.reset_index(drop=True)
        data['filling_count'] = ''
        fillingcounter = 1
        for idx, row in data.iterrows():
            if row['additions'] > 700:
                data.loc[idx, 'filling_count'] = fillingcounter
                fillingcounter += 1
        st.dataframe(data, use_container_width=True)
        data['consumption_cumulative'] = data['consumption'].cumsum()
        data['additions_cumulative'] = data['additions'].cumsum()
        #Chart Filling Level
        fig_fllingLevel = px.line(data, x='Date', y=fillingLvl, color='containerData.productName',markers=True, title=f'Filling Level for {place}')
        csv = convert_df_csv(data)
        st.download_button(
            label="Download data as CSV",
            data=csv,
            file_name='PackwiseProductAnalyticsAllData.csv',
            mime='text/csv',
            key='data' + str(keycounter)
        )
        st.plotly_chart(fig_fllingLevel, use_container_width=True)
        
        ### Consumption per week
        fig_consumption = px.bar(data, x='Date', y='consumption', color='containerData.productName', title=f'Consumption Level for {place}')
        
        st.cache()
        #Avg consumption per produkt per week
        avg_consumption_week = data.groupby(['week','containerData.productName'])['consumption'].mean().reset_index()
        avg_consumption_week.columns = ['Week','Product', 'Consumption per Week']
        st.dataframe(avg_consumption_week)
        fig_avg_consumption_week = px.bar(avg_consumption_week, x='Week', y='Consumption per Week', color='Product', title=f'Consumption per Calendar Week for {place}') 
        st.cache()
        #Avg consumption per product per day
        avg_consumption_day = data.groupby(['Date','containerData.productName'])['consumption'].mean().reset_index()
        avg_consumption_day.columns = ['Day','Product', 'Avg.Consumption per Day']
        fig_avg_consumption_day = px.bar(avg_consumption_day, x='Day', y='Avg.Consumption per Day', color='Product', title=f'Average Consumption per Calendar Day for {place}') 
        
        #Addition per week
        fig_addition_week = px.bar(data, x='Date', y='additions', color='containerData.productName', title=f'Additions Level for {place}')
        # Avg Addition per produkt per week
        avg_addition_week = data.groupby(['week','containerData.productName'])['additions'].sum().reset_index()
        fig_avg_additions = px.bar(avg_addition_week, x='week', y='additions', color='containerData.productName', title=f'Average Additions per Calendar Week for {place}') 
        #Avg Addition per day
        avg_addition_day = data.groupby(['Date','containerData.productName'])['additions'].mean().reset_index()
        fig_avg_addition_day = px.bar(avg_addition_day, x='Date', y='additions', color='containerData.productName', title=f'Average Additions per Day for {place}') 
        
        #Optimal Filling level
        #consumption per week per product
        optimal_levels_consumption = avg_consumption_week.pivot(index='Product', columns='Week', values='Consumption per Week')
        optimalFig = go.Figure(data=go.Heatmap(
        z=optimal_levels_consumption.values,
        x=optimal_levels_consumption.columns,
        y=optimal_levels_consumption.index,
        type = 'heatmap',
        colorscale='Hot',
        hoverongaps = False
        ))
        optimalFig.update_layout(
            title='Optimal Filling Levels by Product and Week',
            xaxis_title='Week',
            yaxis_title='Product'
        )
        

        optimal_levels_additions = avg_addition_week.pivot(index='containerData.productName', columns='week', values='additions')

        st.subheader('Overview Consumption')
        st.plotly_chart(fig_consumption, use_container_width=True)
        csv = convert_df_csv(data)
        st.download_button(
            label="Download data as CSV",
            data=csv,
            file_name='PackwiseProductAnalyticss.csv',
            mime='text/csv',
            key='overview' + str(keycounter)
        )
        
        st.plotly_chart(fig_avg_consumption_week, use_container_width=True)
        csv = convert_df_csv(avg_consumption_week)
        st.download_button(
            label="Download data as CSV",
            data=csv,
            file_name='PackwiseProductAnalyticss1.csv',
            mime='text/csv',
            key='average' + str(keycounter)
        )
        st.dataframe(avg_consumption_week, use_container_width=True)

        st.subheader('Overview Addition')
        st.plotly_chart(fig_avg_additions, use_container_width=True, theme=None)
        st.plotly_chart(fig_addition_week, use_container_width=True, theme=None)
        st.dataframe(avg_addition_week)

        st.subheader('Optimal Filling Level Overview')
        st.plotly_chart(optimalFig, use_container_width=True)

        st.markdown('---')
        # Add each dataframe to the dictonary
        keycounter +=1
        df_list.append(data)

    # End Loop
    if len(df_list) > 1:
        df_res = pd.DataFrame
        df_res = pd.concat(df_list)
        st.title('Filling Level Overview')
        # loop through each dataframe and add a trace to the plot
        fig = px.line(df_res, x='Date', y=fillingLvl, color='place.name', markers=True)
        # update the layout with axis titles, a custom font and background color

        st.plotly_chart(fig, use_container_width=True)
        st.markdown('---')

    

def app(df):
    fillingLevel(df)

