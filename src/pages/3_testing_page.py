from millify import millify
import streamlit as st

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="Temperature", value=millify(7000), delta="1.2 °F")

with col2:
    st.metric(label="Temperature", value=f"{millify(7000)} teste", delta="1.2 °F")

with col3:
    st.metric(label="Temperature", value="70 °F", delta="1.2 °F")

with col4:
    st.metric(label="Temperature", value="70 °F", delta="1.2 °F")