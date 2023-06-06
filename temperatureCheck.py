import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from datetime import timedelta

import addFilterToDataframe

# Funktion zum Filtern des DataFrames schreiben
def filter_data(df, tmpTresh, daysTresh, temp_option):
    filtered_data = []
    complete_list = []
    for container in df["container.name"].unique():
        container_data = df[df["container.name"] == container].reset_index(drop=True)
        container_data['temperature.current'] = pd.to_numeric(container_data['temperature.current'], errors='coerce')

        container_data['timestamp'] = pd.to_datetime(container_data['timestamp'], format="%Y%m%d:%H:%M:%S")
        container_data = container_data.sort_values('timestamp')

        # Get every row where temperature.current is below treshold from user input
        if temp_option == 'Undercut':
            below_thresh_rows = container_data[container_data['temperature.current'] <= tmpTresh]
            criteria_string = 'below'
        else:  # temp_option == 'Overcut'
            below_thresh_rows = container_data[container_data['temperature.current'] >= tmpTresh]
            criteria_string = 'above'

        below_thresh_rows['grp_date'] = below_thresh_rows.timestamp.diff().dt.days.ne(1).cumsum()

        # Group rows by consecutive date groups
        groups = below_thresh_rows.groupby('grp_date')

        # Filter groups with count greater than daysTresh
        filtered_groups = groups.filter(lambda x: len(x) > daysTresh)

        # Get the list of group numbers that meet the criteria
        group_nums = filtered_groups['grp_date'].unique().tolist()

        # Filter below_tresh_rows to only include the selected groups
        final_result = below_thresh_rows[below_thresh_rows['grp_date'].isin(group_nums)]
        if len(final_result) > 0:
            # Reset the index
            final_result = final_result.reset_index()
            start_date = final_result["timestamp"].iloc[0].date()
            start_product = final_result["containerData.productName"].iloc[0]
            end_date = final_result["timestamp"].iloc[-1].date()
            end_product = final_result["containerData.productName"].iloc[-1]
            filtered_data.append((container, len(final_result), start_date, start_product, end_date, end_product))
            complete_list.append(final_result)
    return filtered_data, complete_list, criteria_string


def app(df):
    with st.sidebar:
        temp_option = st.selectbox('Choose a Temperature Criteria', ('Undercut', 'Overcut'))
        if temp_option == 'Undercut':
            temp = 'maximal'
        else:
            temp = 'minimal'
        tmpTresh = st.slider(f'Choose the {temp} temperature', min_value=-20.0, max_value=40.0, value=5.0, step=0.5, format="%.1f °C")
        daysTresh = st.slider('Choose the minimum ammount of days', min_value=1, max_value=30, value=7, step=1)

    results, complete_results, criteria_string = filter_data(df, tmpTresh, daysTresh, temp_option)
    results_df = pd.DataFrame(results, columns=['Container', 'Anzahl Tage', 'Start Datum', 'Produkt zum Start', 'End Datum', 'Produkt zum Ende'])
    # Geben Sie die Ergebnisse aus.
    if results:
        complete_results_df = pd.concat(complete_results)
        st.subheader('Temperature undercut found')
        st.write(f'for atleast {daysTresh} consecutive days a temperature {criteria_string} the threshold of {tmpTresh} °C recorded:')
        for result in results:
            st.write("- container", result[0], "with", result[1], "days from", result[2], "to", result[4],)
        st.markdown('---')
        st.subheader('Complete List to Filter')
        st.dataframe(addFilterToDataframe.filter_dataframe(results_df, False, 1), use_container_width=True)
        st.markdown('---')
        st.subheader('The complete Data to analyse as you wish')
        st.dataframe(addFilterToDataframe.filter_dataframe(complete_results_df, False, 1), use_container_width=True)
    else:
        st.write('No containers found that match the criteria.')
   