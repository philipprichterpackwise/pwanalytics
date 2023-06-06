import streamlit as st
import pandas as pd
import plotly.express as px


def get_filtered_data(df, selected_day):
    return df.loc[df['Date'] == selected_day]

def get_grouped_containers(filtered):
    return filtered.groupby('container.name')

def app(df):
    st.header('Status Overview')
    uniqueDate = df['Date'].unique()
    uniqueDate = sorted(uniqueDate,reverse=True)

    with st.sidebar:
        selected_day = st.selectbox('Select a date you want to see the state off', uniqueDate)
        slcFil = st.radio('Select your Filling Level Unit', ['weight', 'volume'])
        if slcFil == 'weight':
            fillingLvl = 'fillingLevel.weight'
        if slcFil == 'volume':
            fillingLvl = 'fillingLevel.volume'
        st.markdown('---')

    #Filter Df for date
    filtered = df.loc[df['Date'] == (selected_day)]

    #group data by container
    groupedContainers = filtered.groupby('container.name')

    #lastTimestampPerContainer = groupedContainers.tail(1).reset_index(drop=True)
    last_measurement = groupedContainers.apply(lambda x: x.iloc[-1]) 
    last_measurement = last_measurement[['timestamp','Date', 'place.name','place.placeType','containerData.productName', 'container.name', fillingLvl, 'fillingLevel.state', 'container.containerType.name']]
    #st.dataframe(last_measurement)
    st.subheader(f'Amount of products per Place at: {selected_day}')
    last_productValue = last_measurement.groupby(['place.name','containerData.productName'])[fillingLvl].sum().reset_index()
    last_productValue.columns = ['Place', 'Product', 'Filling Level']
    
    c1,c2 = st.columns(2)
    with c1:
        st.dataframe(last_productValue, use_container_width=True)
    with c2:
        fig = px.bar(last_productValue, x='Place', y='Filling Level', color='Product')
        st.plotly_chart(fig)
    st.markdown('---')
    #### How many container per place and product
    st.subheader(f'Amount of containers per Place at: {selected_day}')
    placeOverview = last_measurement.groupby(['place.name','containerData.productName','fillingLevel.state']).size().reset_index(name='Containers')
    placeOverview.columns = ['Place', 'Product', 'Filling Level State', 'Container Amount']
    c1,c2 = st.columns(2)
    with c1:
        st.dataframe(placeOverview, use_container_width=True)
    with c2:
        fig_place = px.bar(placeOverview, x='Place', y='Container Amount', color='Product')
        st.plotly_chart(fig_place)
    st.markdown('---')

     #### How many container per placetype and product
    st.subheader(f'Amount of containers per Placetype at: {selected_day}')
    placeOverview = last_measurement.groupby(['place.placeType','containerData.productName','fillingLevel.state']).size().reset_index(name='Containers')
    placeOverview.columns = ['Placetype', 'Product', 'Filling Level State', 'Container Amount']
    c1,c2 = st.columns(2)
    with c1:
        st.dataframe(placeOverview, use_container_width=True)
    with c2:
        fig_placetype = px.bar(placeOverview, x='Placetype', y='Container Amount', color='Product')
        st.plotly_chart(fig_placetype)
    st.markdown('---')

    #### How many containertypes types per place
    st.subheader(f'Amount of containertypes per Place at: {selected_day}')
    containertypeOvw = last_measurement.groupby(['place.name','container.containerType.name']).size().reset_index(name='Anzahl')
    containertypeOvw.columns = ['Place', 'Container Type', 'Container Amount']
    c1,c2 = st.columns(2)
    with c1:
        st.dataframe(containertypeOvw, use_container_width=True)
    with c2:
        fig_containertype = px.bar(containertypeOvw, x='Place', y='Container Amount', color='Container Type')
        st.plotly_chart(fig_containertype)
    st.markdown('---')