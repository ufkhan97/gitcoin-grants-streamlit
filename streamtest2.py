import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime

st.title('Gitcoin Grants Stack')
chain_id = '1'


@st.cache_data(ttl=1800)
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
                        #'description': round['metadata']['description'] if 'description' in round['metadata'] else '',
                        #'matchingFundsAvailable': round['metadata']['matchingFunds']['matchingFundsAvailable'] if 'matchingFunds' in round['metadata'] else '',
                        #'matchingCap': round['metadata']['matchingFunds']['matchingCap'] if 'matchingFunds' in round['metadata'] else '',
                        'roundStartTime': datetime.datetime.utcfromtimestamp(int(round['roundStartTime'])), # create a datetime object from the timestamp in UTC time
                        'roundEndTime': datetime.datetime.utcfromtimestamp(int(round['roundEndTime']))
                    }
                    rounds.append(round_data)
            df = pd.DataFrame(rounds)
            return df 
    except: 
        return pd.DataFrame()

@st.cache_data(ttl=1800)
def load_round_data(round_id):
    # prepare the URLs
    votes_url = 'https://indexer-grants-stack.gitcoin.co/data/1/rounds/' + round_id + '/votes.json'
    projects_url = 'https://indexer-grants-stack.gitcoin.co/data/1/rounds/' + round_id + '/projects.json'
    
    try:
        # download the Votes JSON data from the URL
        response = requests.get(votes_url)
        if response.status_code == 200:
            votes_data = response.json()
        dfv = pd.DataFrame(votes_data)

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
        # Reorder the columns to match the desired order
        dfp = dfp[['id', 'title', 'description', 'status', 'amountUSD', 'votes', 'uniqueContributors']]
        
        # Merge the votes and projects DataFrames
        dfp = dfp.rename(columns={'id': 'project_id'})
        df_merged = pd.merge(dfv, dfp[['project_id', 'title']], how='left', left_on='projectId', right_on='project_id')

        return df_merged, dfp
    except:
        return pd.DataFrame()
    
    # Takes a dataframe as input and filters to only rows where the votes > 0 and the current time is between the roundStartTime and roundEndTime
    # Then drops all columns besides name, votes, and amountUSD and sorts by votes
def filter_chain_data(chain_data):
    df = chain_data[(chain_data['votes'] > 0) & (chain_data['roundStartTime'] < datetime.datetime.now()) & (chain_data['roundEndTime'] > datetime.datetime.now())]
    df = df[['name', 'votes', 'amountUSD', 'round_id']].sort_values(by=['votes'], ascending=False)
    return df

data_load_state = st.text('Loading data...')
chain_data = load_chain_data(chain_id)
chain_data = filter_chain_data(chain_data)
#round_data = load_round_data(round_id)
data_load_state.text("Done! (using st.cache_data)")




st.subheader('Live Rounds:')
st.write(chain_data)

# graph of the amountUSD grouped by name, and sorted descending
st.subheader('Amount USD by Round')
st.bar_chart(chain_data.groupby('name')['amountUSD'].sum().sort_values(ascending=False), use_container_width=True)
# get rid of the legend





# selectbox to select the round
option = st.selectbox(
    'Select Round',
    chain_data['name'])

data_load_state = st.text('Loading data...')
# load round data for the option selected by looking up the round id with that name in the chain_data df
round_id = chain_data[chain_data['name'] == option]['round_id'].values[0]
round_data, projects_data = load_round_data(round_id)
data_load_state.text("Done! (using st.cache_data)")

df = pd.DataFrame(round_data)
projects_data = projects_data[projects_data['status'] == 'APPROVED']

col1, col2, col3 = st.columns(3)
total_usd = df['amountUSD'].sum()
col1.metric('Total USD', '${:,.2f}'.format(total_usd))
total_donations = (df['amountUSD'] > 0).sum()
col2.metric('Total Donations',  '{:,.0f}'.format(total_donations))
total_by_donor = df.groupby('voter')['amountUSD'].sum()
nonZero_donors = (total_by_donor > 0).sum()
col3.metric('Total Donors',  '{:,.0f}'.format(nonZero_donors))

col4, col5, col6 = st.columns(3)
#column 4 metric is number of projects in projects_data
col4.metric('Total Projects',  '{:,.0f}'.format(len(projects_data)))

#write title and amountUSD from projects_data
st.subheader('Project Details')
st.write(projects_data[['title', 'amountUSD', 'votes', 'uniqueContributors']])

# graph of the amountUSD grouped by name, and sorted descending
st.subheader('Amount USD by Project')
st.bar_chart(projects_data.groupby('title')['amountUSD'].sum().sort_values(ascending=False), use_container_width=True)
