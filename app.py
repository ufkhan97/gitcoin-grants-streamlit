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
st.title("THIS THE APP")
st.title('Gitcoin Grants 18')
st.write('The Gitcoin Grants Program is a quarterly initiative that empowers everyday believers to drive funding toward what they believe matters, with the impact of individual donations being magnified by the use of the [Quadratic Funding (QF)](https://wtfisqf.com) distribution mechanism.')
st.write('You can donate to projects in the Round from August 15th 2023 12:00 UTC to August 29th 2023 12:00 UTC.')
st.write('👉 Visit [grants.gitcoin.co](https://grants.gitcoin.co) to donate.')

# Helper function to load data from URLs
def safe_get(data, *keys):
    """Safely retrieve nested dictionary keys."""
    temp = data
    for key in keys:
        if isinstance(temp, dict) and key in temp:
            temp = temp[key]
        else:
            return None
    return temp

def load_data_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        return response.json()
    except requests.RequestException as e:
        st.warning(f"Failed to fetch data from {url}. Error: {e}")
        return []

@st.cache_data(ttl=900)
def load_round_projects_data(round_id, chain_id):
    url = f'https://indexer-grants-stack.gitcoin.co/data/{chain_id}/rounds/{round_id}/applications.json'
    data = load_data_from_url(url)
    
    projects = []
    for project in data:
        title = safe_get(project, 'metadata', 'application', 'project', 'title')
        grantAddress = safe_get(project, 'metadata', 'application', 'recipient')
        description = safe_get(project, 'metadata', 'application', 'project', 'description')
        
        if title and grantAddress:  # Ensure required fields are available
            project_data = {
                'projectId': project['projectId'],
                'title': title,
                'grantAddress': grantAddress,
                'status': project['status'],
                'amountUSD': project['amountUSD'],
                'votes': project['votes'],
                'uniqueContributors': project['uniqueContributors'],
                'description': description
            }
            projects.append(project_data)
    return projects

    
@st.cache_data(ttl=900)
def load_round_votes_data(round_id, chain_id):
    url = f'https://indexer-grants-stack.gitcoin.co/data/{chain_id}/rounds/{round_id}/votes.json'
    data = load_data_from_url(url)
    return pd.DataFrame(data)

@st.cache_data(ttl=900)
def load_passport_data():
    url = 'https://indexer-grants-stack.gitcoin.co/data/passport_scores.json'
    data = load_data_from_url(url)
    passports = [{
        'address': passport['address'],
        'last_score_timestamp': passport['last_score_timestamp'],
        'status': passport['status'],
        'rawScore': passport['evidence']['rawScore'] if 'evidence' in passport and passport['evidence'] is not None and 'rawScore' in passport['evidence'] else 0,
    } for passport in data]
    df = pd.DataFrame(passports)
    df['last_score_timestamp'] = pd.to_datetime(df['last_score_timestamp'])
    return df


def compute_timestamp(row, starting_time, chain_starting_blocks):
    # Get the starting block for the chain_id
    starting_block = chain_starting_blocks[row['chain_id']]
    # Determine the increment based on the chain_id
    increment = 12.0 if row['chain_id'] == 1 else 2
    # Calculate the timestamp based on the blockNumber and starting block
    timestamp = starting_time + pd.to_timedelta((row['blockNumber'] - starting_block) * increment, unit='s')
    return timestamp

data_load_state = st.text('Loading data...')
round_data = pd.read_csv('gg18_rounds.csv')
#program = st.selectbox("Select a program", round_data['program'].unique())
round_data = round_data[round_data['program'] == 'GG18']

dfv_list = []
dfp_list = []
for _,row in round_data.iterrows():
    #dfp = load_round_projects_data(str(row['round_id']), str(row['chain_id']))
    projects_list = load_round_projects_data(str(row['round_id']), str(row['chain_id']))
    dfp = pd.DataFrame(projects_list)
    dfv = load_round_votes_data(str(row['round_id']), str(row['chain_id']))

    dfp['round_id'] = row['round_id']
    dfp['chain_id'] = row['chain_id']
    dfp['round_name'] = row['round_name']
    
    dfv['round_id'] = row['round_id']
    dfv['chain_id'] = row['chain_id']
    dfv['round_name'] = row['round_name']
    

    #st.write("Round " + row[1]['round_name'] + " loaded with " + str(len(dfv)) + " votes.")
    dfv_list.append(dfv)
    dfp_list.append(dfp)

dfv = pd.concat(dfv_list)
dfp = pd.concat(dfp_list)

token_map = {
    "0x0000000000000000000000000000000000000000": "ETH",
    "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1": "DAI",
}
dfv["token_symbol"] = dfv["token"].map(token_map)


chain_starting_blocks = dfv.groupby('chain_id')['blockNumber'].min().to_dict()
starting_time = pd.to_datetime(round_data['starting_time'].min())
dfv['timestamp'] = dfv.apply(compute_timestamp, args=(starting_time, chain_starting_blocks), axis=1)

data_load_state.text("")

def create_token_comparison_pie_chart(dfv):
    # Group by token_symbol and sum the amountUSD
    grouped_data = dfv.groupby('token_symbol')['amountUSD'].sum().reset_index()
    fig = px.pie(grouped_data, names='token_symbol', values='amountUSD', title='ETH vs DAI Contributions (in $)', hole=0.3)
    for trace in fig.data:
        trace.hoverinfo = 'none'
    return fig

def get_USD_by_round_chart(dfp, color_map):
    grouped_data = dfp.groupby('round_name')['amountUSD'].sum().reset_index().sort_values('amountUSD', ascending=False)
    fig = px.bar(grouped_data, x='round_name', y='amountUSD', title='Crowdfunded (in $) by Round', 
                 color='round_name', labels={'amountUSD': 'Crowdfunded Amount ($)', 'round_name': 'Round Name'}, 
                 color_discrete_map=color_map)
    fig.update_layout(showlegend=False)
    return fig

def get_contributions_by_round_chart(dfp, color_map):
    grouped_data = dfp.groupby('round_name')['votes'].sum().reset_index().sort_values('votes', ascending=False)
    fig = px.bar(grouped_data, x='round_name', y='votes', title='Total Contributions (#) by Round', 
                 color='round_name', labels={'votes': 'Number of Contributions', 'round_name': 'Round Name'}, 
                 color_discrete_map=color_map)
    fig.update_layout(showlegend=False)
    return fig

def get_contribution_time_series_chart(dfv):
    dfv_count = dfv.groupby([dfv['timestamp'].dt.strftime('%m-%d-%Y %H')])['id'].nunique()
    dfv_count.index = pd.to_datetime(dfv_count.index)
    dfv_count = dfv_count.reindex(pd.date_range(start=dfv_count.index.min(), end=dfv_count.index.max(), freq='H'), fill_value=0)
    fig = px.bar(dfv_count, x=dfv_count.index, y='id', labels={'id': 'Number of Contributions', 'index': 'Time'}, title='Number of Contributions over Time')
    fig.update_layout()
    return fig 


st.subheader('Rounds Summary')

col1, col2 = st.columns(2)
col1.metric('Matching Pool', '${:,.2f}'.format(round_data['matching_pool'].sum()))
col1.metric('Total Donated', '${:,.2f}'.format(dfp['amountUSD'].sum()))
col1.metric("Total Donations", '{:,.0f}'.format(dfp['votes'].sum()))
col1.metric('Unique Donors', '{:,.0f}'.format(dfv['voter'].nunique()))
col1.metric('Total Rounds', '{:,.0f}'.format(dfp['round_id'].nunique()))
col2.plotly_chart(create_token_comparison_pie_chart(dfv))

color_map = dict(zip(dfp['round_name'].unique(), px.colors.qualitative.Pastel))
col1, col2 = st.columns(2)
col1.plotly_chart(get_USD_by_round_chart(dfp, color_map))
col2.plotly_chart(get_contributions_by_round_chart(dfp, color_map))
st.plotly_chart(get_contribution_time_series_chart(dfv), use_container_width=True) 


st.title("Round Details")
# selectbox to select the round
option = st.selectbox(
    'Select Round',
    dfv['round_name'].unique())

dfv = dfv[dfv['round_name'] == option]
dfp = dfp[dfp['round_name'] == option]
round_data = round_data[round_data['round_name'] == option]

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric('Matching Pool', '${:,.2f}'.format(round_data['matching_pool'].sum()))
col2.metric('Total Donated', '${:,.2f}'.format(dfp['amountUSD'].sum()))
col3.metric('Total Donations',  '{:,.0f}'.format(dfp['votes'].sum()))
col4.metric('Total Projects',  '{:,.0f}'.format(len(dfp)))
col5.metric('Unique Donors',  '{:,.0f}'.format(dfv['voter'].nunique()))



def create_treemap(dfp):
    #dfp['title'] = dfp['title'].str[:30]
    # truncate everything after the first - or :
    #dfp['title'] = dfp['title'].str.split(':').str[0]
    #dfp['title'] = dfp['title'].str.split('\'').str[0]

    fig = px.treemap(dfp, path=['title'], values='amountUSD', hover_data=['title'])
    fig.update_traces(texttemplate='%{label}<br>$%{value:.3s}', textposition='middle center', textfont_size=20)
    fig.update_layout(font=dict(size=20))
    # set window height
    fig.update_layout(height=540)
    return fig

st.plotly_chart(create_treemap(dfp.copy()), use_container_width=True)

df = pd.merge(dfv, dfp[['projectId', 'title']], how='left', left_on='projectId', right_on='projectId')

st.write('## Projects')
# write projects title, votes, amount USD, unique contributors
df_display = dfp[['title', 'votes',  'amountUSD',]].sort_values('votes', ascending=False)
df_display.columns = ['Title', 'Votes',  'Amount (USD)',]
df_display['Amount (USD)'] = df_display['Amount (USD)'].apply(lambda x: '${:,.2f}'.format(x))
df_display['Votes'] = df_display['Votes'].apply(lambda x: '{:,.0f}'.format(x))
df_display = df_display.reset_index(drop=True)
st.dataframe(df_display, use_container_width=True, height=500)

