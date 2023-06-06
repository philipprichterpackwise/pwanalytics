import streamlit as st
import pandas as pd
import numpy as np
from datetime import time
import altair as alt
import json
import requests
from streamlit_lottie import st_lottie


#### Sub-Pages Import
import productanalytics
import circles
import relevantColumns
import placeanalytics
import temperatureCheck
import consumption_test
import containerObservation
import checkPermission

st.set_page_config(
    page_title='Packwise Container Data Analytics',
    layout="wide"
)

def read_data(file_path):
    relevant_cols = relevantColumns.relevant_columns
    # Read the data in chunks
    chunks = []
    for chunk in pd.read_csv(file_path, chunksize=100000, sep=",", encoding='utf-8', on_bad_lines='skip', usecols=relevant_cols):
        chunks.append(chunk)
    df = pd.concat(chunks)
    return df

def generate_meaningful_name():
    fake = Faker()
    return fake.name()

def anonymize_container_names(df):
    unique_names = df['container.name'].unique()
    anonymized_names = [generate_meaningful_name() for _ in range(len(unique_names))]
    mapping = dict(zip(unique_names, anonymized_names))
    df['container.name'] = df['container.name'].map(mapping)
    return df

#### relevant functions
# File Upload
def fileUpload():
    #read data into dataframe
    df = read_data('Anon_Clean_reportData.csv')
    #cleanup data
    df['fillingLevel.percent'] = df['fillingLevel.percent'].fillna(0).astype(float)
    # convert timestamp column to datetime type
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['place.name'] = np.where(df['place.name'].isnull(), 'on Transport', df['place.name'])
    df['containerData.productName'] = np.where(df['containerData.productName'].isnull(), 'No Product', df['containerData.productName'])
    df['Date'] = pd.to_datetime(df['timestamp'], dayfirst=True, errors='coerce').dt.date
    df = df.sort_values(by='Date')
    # Create a boolean mask for each condition
    full_mask = df['fillingLevel.percent'] >= 90
    in_use_mask = (df['fillingLevel.percent'] < 90) & (df['fillingLevel.percent'] > 10)
    empty_mask = df['fillingLevel.percent'] <= 10
    # Use NumPy's where function to assign values based on the conditions
    df['fillingLevel.state'] = np.where(full_mask, 'Full', np.where(in_use_mask, 'operative', 'empty'))
    return df


def load_lottieurl(url :str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

### Main -- Welcome Screen  
with open ('style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)


df = fileUpload()
export_start = df['Date'].head(1).reset_index(drop=True)[0]
export_end = df['Date'].tail(1).reset_index(drop=True)[0]

with st.sidebar:
    st.sidebar.title('Container Analytics')
    st.write('Provided by')
    st.write("""<figure><embed type="image/svg+xml" src="https://www.packwise.de/hubfs/packwise_klein-farbe.svg" /></figure>""", unsafe_allow_html=True)
    st.markdown('---')
    st.subheader('Please select a date range for your Dashboard')
    a1, a2 = st.columns(2)
    with a1:
        user_start_date = st.date_input(label='Start date', key='start', value=export_start ,min_value=export_start, max_value=export_end)
    with a2:
        user_end_date = st.date_input(label='End date', key='end', value=export_end, min_value=export_start, max_value=export_end)
        
    # Convert 'Date' column to datetime if it isn't already
    df['Date'] = pd.to_datetime(df['Date'])

    # Convert user input dates to datetime
    user_start_date = pd.to_datetime(user_start_date)
    user_end_date = pd.to_datetime(user_end_date)

    # Filter rows between user_start_date and user_end_date
    df = df[(df['Date'] >= user_start_date) & (df['Date'] <= user_end_date)]
    c = st.container()
    menu = st.sidebar.selectbox(
        "Select the Dashboard you would like to see",
        ('Cycle Analytics', 'Places Analytics', 'Temperature Analytics', 'Consumption Analytics', 'Container Observation')
    )
st.title('Welcome to your Analytics Dashboard')
st.subheader(f'Current Selection: {menu}')
st.markdown('---')

if menu == 'Places Analytics':
    placeanalytics.app(df)

if menu == 'Cycle Analytics':
    circles.app(df)

if menu == 'Temperature Analytics':
    temperatureCheck.app(df)

if menu == 'Consumption Analytics':
    consumption_test.app(df)

if menu == 'Container Observation':
    containerObservation.app(df)