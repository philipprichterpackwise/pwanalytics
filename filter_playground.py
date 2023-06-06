import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def createFilter(df: pd.DataFrame, column_name: str, filter_id: int) -> tuple:
    """
    Erstellt ein Filter-Widget, das es dem Benutzer ermöglicht, die Daten basierend auf einer bestimmten Spalte zu filtern.
    :param df: Ein Pandas DataFrame, auf das der Filter angewendet werden soll.
    :param column_name: Der Name der Spalte, auf die der Filter angewendet werden soll.
    :param filter_id: Die ID des aktuellen Filters.
    :return: Ein Tuple mit den ausgewählten Daten, der aktualisierten Filter-ID, dem Filtertyp und dem Filterbetrag.
    """
    selected_data = None
    filter_type_value = None
    amount = 0
    col1, col2 = st.columns(2)
    with col1:
        filter_type = st.radio(f'Select filter type for {column_name}', ['specific','conditional'], key=f'radio-{filter_id}')
    with col2:
        if filter_type == 'specific':
            selected_data = st.multiselect(
                f'Select the relevant for {column_name}',
                options=df[column_name].unique(),   
                key=f'data-{filter_id}',
            )
        if filter_type == 'conditional':
            filter_type_value = st.selectbox("Select filter type:", ['lower than', 'greater than', 'equal'], key=f'type-{filter_id}')
            amount = st.text_input("Enter amount:", value=0,key=f'amount-{filter_id}')
    filter_id += 1
    st.markdown('---')
    return selected_data, filter_id, filter_type_value, amount
    
def filter(df):
    column_names = df.columns.tolist()
    filter_id = 1
    relevant_columns = st.multiselect(f'Select a relevant columns', column_names)
    filter_query = ''
    for i in relevant_columns:
        selected_data, filter_id, filter_type_value, amount = createFilter(df, i, filter_id)
        if selected_data:
            filter_query += f"`{i}`.isin({selected_data}) & "
        if filter_type_value:
            if filter_type_value == 'lower than':
                filter_query += f"`{i}` < {amount} & "
            elif filter_type_value == 'greater than':
                filter_query += f"`{i}` > {amount} & "
            elif filter_type_value == 'equal':
                filter_query == f"`{i}` < {amount} & "
    if filter_query:
        if st.button('Filter - Zeig mir die Daten .... die Daten!', type='primary'):
            filter_query = filter_query[:-3]  # remove the last ' & '
            filtered_df = df.query(filter_query)
            st.dataframe(filtered_df)
            #if st.button('Zeig mir nen cooles Chart'):
            #chart=st.radio('Welche Art glaubst du ist passend?', ['Pie Chart',])
            filtered_chart = px.line(filtered_df)
            c1,c2 = st.columns(2)
            with c1:
                csv = convert_df_csv(filtered_df)
                st.download_button(
                    label="Download data as CSV",
                    data=csv,
                    file_name=f'{filtered_df}.csv',
                    mime='text/csv',
                )
            
            

def convert_df_csv(df):
    return df.to_csv().encode('utf-8')


def app(df):
    filter(df)