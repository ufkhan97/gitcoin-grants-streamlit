import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime
import plotly.graph_objs as go
import plotly.express as px
import locale

st.set_page_config(
    page_title="Gitcoin Beta Rounds",
    page_icon="📊",
    layout="wide",
)

st.title('Gitcoin Beta Rounds')
st.write('The Gitcoin Grants Program is a quarterly initiative that empowers everyday believers to drive funding toward what they believe matters, with the impact of individual donations being magnified by the use of the [Quadratic Funding (QF)](https://wtfisqf.com) distribution mechanism.')
st.write('You can donate to projects in the Beta Round from April 25th 2023 12:00 UTC to May 9th 2023 23:59 UTC.')
st.write('👉 Visit [grants.gitcoin.co](https://grants.gitcoin.co) to donate.')


chain_id = '1'


@st.cache_data(ttl=300)
def load_chain_data(chain_id):
    chain_url = 'https://indexer-grants-stack.gitcoin.co/data/' + chain_id + '/rounds.json'
    try:
        response = requests.get(chain_url)
        if response.status_code == 200:
            chain_data = response.json()
            rounds = []
            for round in chain_data:
                if round['metadata'] is not None:
                    round_data = {
                        'round_id': round['id'],
                        'name': round['metadata']['name'],
                        'amountUSD': round['amountUSD'],
                        'votes': round['votes'],
                        'description': round['metadata']['description'] if 'description' in round['metadata'] else '',
                        'matchingFundsAvailable': round['metadata']['matchingFunds']['matchingFundsAvailable'] if 'matchingFunds' in round['metadata'] else '',
                        'matchingCap': round['metadata']['matchingFunds']['matchingCap'] if 'matchingFunds' in round['metadata'] else '',
                        'roundStartTime': datetime.datetime.utcfromtimestamp(int(round['roundStartTime'])), # create a datetime object from the timestamp in UTC time
                        'roundEndTime': datetime.datetime.utcfromtimestamp(int(round['roundEndTime']))
                    }
                    rounds.append(round_data)
            df = pd.DataFrame(rounds)
            # Filter to live now and active rounds with votes > 0
            df = df[(df['votes'] > 0) & (df['roundStartTime'] < datetime.datetime.now()) & (df['roundEndTime'] > datetime.datetime.now())]
            return df 
    except: 
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_round_projects_data(round_id):
    # prepare the URLs
    projects_url = 'https://indexer-grants-stack.gitcoin.co/data/1/rounds/' + round_id + '/projects.json'
    
    try:
        # download the Projects JSON data from the URL
        response = requests.get(projects_url)
        if response.status_code == 200:
            projects_data = response.json()

        # Extract the relevant data from each project
        projects = []
        for project in projects_data:
            project_data = {
                'id': project['id'],
                'title': project['metadata']['application']['project']['title'],
                'description': project['metadata']['application']['project']['description'],
                'status': project['status'],
                'amountUSD': project['amountUSD'],
                'votes': project['votes'],
                'uniqueContributors': project['uniqueContributors']
            }
            projects.append(project_data)
        # Create a DataFrame from the extracted data
        dfp = pd.DataFrame(projects)
        # Reorder the columns to match the desired order and rename column id to project_id
        dfp = dfp[['id', 'title', 'description', 'status', 'amountUSD', 'votes', 'uniqueContributors']]
        dfp = dfp.rename(columns={'id': 'project_id'})
        # Filter to only approved projects
        dfp = dfp[dfp['status'] == 'APPROVED']
        return dfp
    except:
        return pd.DataFrame()
    
@st.cache_data(ttl=300)
def load_round_votes_data(round_id):
    votes_url = 'https://indexer-grants-stack.gitcoin.co/data/1/rounds/' + round_id + '/votes.json'
    try:
        # download the Votes JSON data from the URL
        response = requests.get(votes_url)
        if response.status_code == 200:
            votes_data = response.json()
        df = pd.DataFrame(votes_data)
        return df
    except:
        return pd.DataFrame()


data_load_state = st.text('Loading data...')
chain_data = load_chain_data(chain_id)
data_load_state.text("")

st.subheader('Beta Rounds Summary')
# create two-column metrics. One with the sum of votes and the other with the amountUSD
col1, col2, col3 = st.columns(3)
col1.metric("Total Votes", '{:,.0f}'.format(chain_data['votes'].sum()))
col2.metric('Total Contributed', '${:,.2f}'.format(chain_data['amountUSD'].sum()))
col3.metric('Total Rounds', '{:,.0f}'.format(chain_data['round_id'].count()))


# filter chain_data to name, votes, amountUSD


def get_USD_by_round_chart(chain_data, color_map):
    grouped_data = chain_data.groupby('name')['amountUSD'].sum().reset_index().sort_values('amountUSD', ascending=True)
    data = [go.Bar(
        x=grouped_data['amountUSD'], 
        y=grouped_data['name'],
        marker_color=grouped_data['name'].map(color_map), # map each round to a specific color
        orientation='h'
    )]
    layout = go.Layout(
        title='Crowdfunded (in $) by Round',
        xaxis=dict(title='Dollars'),
        yaxis=dict(title='Round')
    )
    fig = go.Figure(data=data, layout=layout)
    return fig

def get_contributions_by_round_bar_chart(chain_data, color_map):
    grouped_data = chain_data.groupby('name')['votes'].sum().reset_index().sort_values('votes', ascending=True)
    data = [go.Bar(
        x=grouped_data['votes'], 
        y=grouped_data['name'],
        marker_color=grouped_data['name'].map(color_map), # map each round to a specific color
        orientation='h'
    )]
    layout = go.Layout(
        title='Total Contributions (#) by Round',
        xaxis=dict(title='Number'),
        yaxis=dict(title='Round')
    )
    fig = go.Figure(data=data, layout=layout)
    return fig

def create_color_map(chain_data):
    unique_rounds = chain_data['name'].unique()
    color_list = ['#4C72B0', '#DD8452', '#55A868', '#C44E52', '#8172B2', '#937860', '#DA8BC3', '#8C8C8C', '#CCB974', '#64B5CD', '#4E3D3D', '#AEBD38', '#AD6B5E', '#1F78B4', '#B2DF8A'] # manually specified list of colors
    color_map = dict(zip(unique_rounds, color_list[:len(unique_rounds)])) # map each round to a specific color
    return color_map

# create color map
color_map = create_color_map(chain_data)

# create two-column charts. One with the sum of votes and the other with the amountUSD
col1, col2 = st.columns(2)
fig = get_USD_by_round_chart(chain_data, color_map)
col1.plotly_chart(fig, use_container_width=True)
fig = get_contributions_by_round_bar_chart(chain_data, color_map)
col2.plotly_chart(fig, use_container_width=True)
chain_data_display = chain_data[['name', 'votes', 'amountUSD']]

# selectbox to select the round
option = st.selectbox(
    'Select Round',
    chain_data['name'])

data_load_state = st.text('Loading data...')
# load round data for the option selected by looking up the round id with that name in the chain_data df
round_id = chain_data[chain_data['name'] == option]['round_id'].values[0]
dfp = load_round_projects_data(round_id)
dfv = load_round_votes_data(round_id)
data_load_state.text("")

dfv = pd.merge(dfv, dfp[['project_id', 'title', 'status']], how='left', left_on='projectId', right_on='project_id')

col1, col2 = st.columns(2)
total_usd = dfv['amountUSD'].sum()
col1.metric('Total USD', '${:,.2f}'.format(total_usd))
total_donations = (dfv['amountUSD'] > 0).sum()
col1.metric('Total Donations',  '{:,.0f}'.format(total_donations))
total_by_donor = dfv.groupby('voter')['amountUSD'].sum()
nonZero_donors = (total_by_donor > 0).sum()
col1.metric('Total Donors',  '{:,.0f}'.format(nonZero_donors))

col1.metric('Total Projects',  '{:,.0f}'.format(len(dfp)))

col2.write('## Projects')
# write projects title, votes, amount USD, unique contributors
col2.write(dfp[['title', 'votes', 'amountUSD', 'uniqueContributors']])


def get_grants_bar_chart(votes_data):
    grouped_data = votes_data.groupby('title')['amountUSD'].sum().reset_index().sort_values('amountUSD', ascending=True)

    data = [go.Bar(
        x=grouped_data['amountUSD'], 
        y=grouped_data['title'],
        marker_color='blue',
        orientation='h'
    )]
    layout = go.Layout(
        title='Total Contributions (in $) by Grant',
        xaxis= { 'title':'Total Contributions ($)'},
        yaxis={'title':'Grant'},
        height=800

    )
    fig = go.Figure(data=data, layout=layout)
    return fig


# display the chart
# fig_grants = get_grants_bar_chart(dfv)
# st.plotly_chart(fig_grants, use_container_width=False)


starting_blockNumber = 17123133
ending_blockNumber = dfv['blockNumber'].max()
starting_blockTime = datetime.datetime(2023, 4, 25, 12, 13, 35)

def create_block_times(starting_blockNumber, ending_blockNumber, starting_blockTime):
    # Create an array of 107,000 blockNumbers starting from the starting_blockNumber and incrementing by 1 each time
    blocks = np.arange(starting_blockNumber, ending_blockNumber, 1)
    # create a new dataframe with the blocks array
    df = pd.DataFrame(blocks)
    df.columns = ['blockNumber']
    # create a new column called utc_time and use the starting_blockTime as the value for the first starting_blockNumber
    df['utc_time'] = starting_blockTime
    # as the blockNumber increases by 1, add 12.133 seconds to the utc_time
    df['utc_time'] = pd.to_datetime(df['utc_time']) + pd.to_timedelta(12.133*(df['blockNumber'] - starting_blockNumber), unit='s')
    return df

dfb = create_block_times(starting_blockNumber, ending_blockNumber, starting_blockTime)
# merge the block times with the votes data
dfv = pd.merge(dfv, dfb, how='left', on='blockNumber')
# graph of the amountUSD grouped by utc_time hour
#st.subheader('Amount USD by Hour and day of utc_time')
dfv_count = dfv.groupby([dfv['utc_time'].dt.strftime('%d-%m-%Y %H')])['id'].nunique()
# set the index to be the utc_time column
dfv_count.index = pd.to_datetime(dfv_count.index)
# fill in missing hours with 0
dfv_count = dfv_count.reindex(pd.date_range(start=dfv_count.index.min(), end=dfv_count.index.max(), freq='H'), fill_value=0)
fig = px.bar(dfv_count, x=dfv_count.index, y='id', labels={'id': 'Number of Votes'}, title='Number of Contributions over Time')
st.plotly_chart(fig, use_container_width=True)
