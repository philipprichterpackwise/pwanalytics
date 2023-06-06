import streamlit as st

def app(df):
    containers = df['container.name'].unique()
    places = df['place.name'].unique()
    products = df['containerData.productName'].unique()
    orders = df['containerData.orderNumber'].unique()
    st.subheader('Quick Data Overview')
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        col1.metric("Amount of observed container", len(containers))
        with st.expander('Container List'):
            st.dataframe(containers, use_container_width=True)
    with col2:
        col2.metric("Amount of places", len(places))
        with st.expander('Places List'):
            st.dataframe(places, use_container_width=True)
    with col3:
        col3.metric("Amount of products", len(products))
        with st.expander('Products List'):
            st.dataframe(products, use_container_width=True)
    with col4:
        col4.metric("Amount of Orders in export", len(orders))
        with st.expander('List of orders'):
            st.dataframe(orders, use_container_width=True)
    st.markdown('---')