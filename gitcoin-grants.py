import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime
import plotly.graph_objs as go
import plotly.express as px
import locale
import time
import networkx as nx

st.set_page_config(
    page_title="Gitcoin Grants Round 18",
    page_icon="📊",
    layout="wide",

)
# DEPLOYED ON STREAMLIT 
# https://gitcoin-grants.streamlit.app/

st.title('Gitcoin Grants 18')
st.title('👉 Visit [gitcoin.co/grants-data](https://gitcoin-grants-51f2c0c12a8e.herokuapp.com/) to view the dashboard.')
