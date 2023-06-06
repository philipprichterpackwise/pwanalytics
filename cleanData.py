import streamlit as st
import fillingLevelCleanUpForecast

def convert_df_csv(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('utf-8')

def convert_df_xlsx(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_excel()

def app(df):
    df = fillingLevelCleanUpForecast.app(df)

    df[['lon', 'lat']] = df['location.coordinates'].str.split(', ', 1, expand=True)
    df[['lon', 'lat']] = df[['lon', 'lat']].astype(float)
    st.dataframe(df)
    csv = convert_df_csv(df)
    st.download_button(
        label='Download CSV File',
        data=csv,
        file_name='Packwiseflow_Cycle_export.csv',
        mime='text/csv',
        )
    csv = convert_df_csv(df)
    st.download_button(
        label='Download xlsx File',
        data=csv,
        file_name='Packwiseflow_Cycle_export.xlsx',
        mime='text/csv',
        )
    json = df.to_json()
    st.download_button(
        label='Download json File',
        data=json,
        file_name='Packwiseflow_Cycle_export.json',
        mime='application/json',
        )
