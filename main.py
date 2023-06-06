import streamlit as st
import pandas as pd
import numpy as np
from datetime import time
import altair as alt
import json
import requests
from streamlit_lottie import st_lottie
from streamlit_option_menu import option_menu


#### Sub-Pages Import
import productanalytics
import circles
import relevantColumns
import placeanalytics
import temperatureCheck
import product_analytics
import containerObservation
import checkPermission

st.set_page_config(
    page_title='Packwise Container Data Analytics',
    layout="wide"
)

product_menu = ["Consumption Analytics", "Storage range"]
logistic_menu = ["Container Downtimes", "FiFo"]
cycle_menu = ["Cycle Analytics"]
container_menu = ["Temperature", "Cycle Counter", "Container TÜV ADR"]
dosage_menu = ["Dosage Analytics"]
home_menu = ["Homepage", "FAQ"]


def read_data(file_path):
    relevant_cols = relevantColumns.relevant_columns
    # Read the data in chunks
    chunks = []
    for chunk in pd.read_csv(file_path, chunksize=100000, sep=",", encoding='utf-8', on_bad_lines='skip', usecols=relevant_cols):
        chunks.append(chunk)
    df = pd.concat(chunks)
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

st.write("""<figure><embed type="image/svg+xml" src="https://www.packwise.de/hubfs/packwise_klein-farbe.svg" /></figure>""", unsafe_allow_html=True)

st.markdown('---')
st.subheader('Main Menu')
main_menu= option_menu(None, ["Home Dashboard", "Product Dashboard", "Logistic Dashboard", "Cycle Dashboard", "Container Dashboard", "Dosage Dashboard"],
    icons=['house', 'cup-hot', "truck", 'recycle', 'box-seam', 'eyedropper'], 
    menu_icon="cast", default_index=0, orientation="horizontal",
)
cols1, cols2, cols3 = st.columns([2,1,2])
with cols2:
    st.subheader('Please select a date range for your Dashboard')
    b1, b2 = st.columns(2)
    with b1:
        user_start_date = st.date_input(label='Start date', key='start', value=export_start ,min_value=export_start, max_value=export_end)
    with b2:
        user_end_date = st.date_input(label='End date', key='end', value=export_end, min_value=export_start, max_value=export_end)
    
st.markdown('---')

if main_menu == "Product Dashboard":
    sub_menu_list = product_menu
elif main_menu == "Logistic Dashboard":
    sub_menu_list = logistic_menu
elif main_menu == "Cycle Dashboard":
    sub_menu_list = cycle_menu
elif main_menu == "Container Dashboard":
    sub_menu_list = container_menu
elif main_menu == "Dosage Dashboard":
    sub_menu_list = dosage_menu
elif main_menu == "Home Dashboard":
    sub_menu_list = home_menu

with st.sidebar:
    st.sidebar.title('Container Analytics')
    st.write('Provided by')
    st.write("""<figure><embed type="image/svg+xml" src="https://www.packwise.de/hubfs/packwise_klein-farbe.svg" /></figure>""", unsafe_allow_html=True)
    st.markdown('---')
        
    # Convert 'Date' column to datetime if it isn't already
    df['Date'] = pd.to_datetime(df['Date'])

    # Convert user input dates to datetime
    user_start_date = pd.to_datetime(user_start_date)
    user_end_date = pd.to_datetime(user_end_date)

    # Filter rows between user_start_date and user_end_date
    df = df[(df['Date'] >= user_start_date) & (df['Date'] <= user_end_date)]
    c = st.container()

    # 1. as sidebar menu
    sub_menu = option_menu(main_menu, 
                        sub_menu_list,
                        menu_icon="cast", default_index=0)

st.title(f'Welcome to your {main_menu}')
st.subheader(f'Current Selection: {sub_menu}')

#Home Section
if sub_menu == 'Home':
    st.title('Homepage')
    st.write('Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet. Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet.')

if sub_menu == 'FAQ':
    st.title('FAQ')
    st.write('Lorem ipsum ')

#Product Section
if sub_menu == 'Consumption Analytics':
    product_analytics.app(df)

if sub_menu == 'Storage range':
    st.write('Storage')
    
#Logistic Section
if sub_menu == 'Container Downtimes':
    placeanalytics.app(df)

if sub_menu == 'Storage range':
    st.write('Storage')

if sub_menu == 'FiFo':
    st.write('test')

#Cycle Dashboard
if sub_menu == 'Cycle Analytics':
    circles.app(df)

#Container Dashboard
if sub_menu == 'Temperature':
    temperatureCheck.app(df)

if sub_menu == 'Cycle Counter':
    st.write('Cycle')

if sub_menu == 'Container TÜV ADR':
    st.write('Hier Ihre neue TÜV Plakette!')

#Dosage Dashboard
if sub_menu == 'Dosage Analytics':
    st.write('Dosierkontrole')


