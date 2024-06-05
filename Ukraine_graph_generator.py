import streamlit as st
import pandas as pd
import plotly.express as px
import os
import zipfile
import time
from kaggle.api.kaggle_api_extended import KaggleApi

# Set up environment variables for Kaggle credentials
os.environ['KAGGLE_USERNAME'] = st.secrets["kaggle"]["username"]
os.environ['KAGGLE_KEY'] = st.secrets["kaggle"]["key"]

st.set_page_config(page_title= "Ukraine Missiles Launched vs Intercepted Dashboard", page_icon=":bar_chart:")

def download_dataset():
    # Initialize Kaggle API client and authenticate
    api = KaggleApi()
    api.authenticate()
    
   # Define the dataset and the path where files will be downloaded
    dataset = 'piterfm/massive-missile-attacks-on-ukraine'
    path = '.'

    # Download the dataset zip file
    api.dataset_download_files(dataset, path=path, unzip=False)

    # Define the path of the zip file
    zip_path = os.path.join(path, dataset.split('/')[-1] + '.zip')

    # Extract only the needed file
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # Get list of all files in zip
        file_names = zip_ref.namelist()
        # Find the required file and extract it
        for file in file_names:
            if file.endswith('missile_attacks_daily.csv'):
                zip_ref.extract(file, path)
                # Optionally, rename and move the file to a more convenient location
                os.rename(os.path.join(path, file), os.path.join(path, 'missile_attacks_daily.csv'))
                break

    # Clean up the zip file after extraction
    os.remove(zip_path)

def remove_time(data):
    # Ensure that time is removed and only the date is kept
    data['time_start'] = data['time_start'].astype(str).apply(lambda x: x.split(' ')[0])
    return data

def process_dataset(data):
    # Drop unnecessary columns including the original 'time_end'
    data.drop(columns=['time_end', 'model', 'launch_place', 'target', 'destroyed_details', 'carrier', 'source'], inplace=True)

    # Rename 'time_start' to 'date'
    data.rename(columns={'time_start': 'date'}, inplace=True)

    # Convert 'date' to datetime object and extract the date part
    data['date'] = pd.to_datetime(data['date']).dt.date

    return data

def aggregate_data(data):
    # Group data by date and sum the values of 'launched' and 'destroyed'
    daily_data = data.groupby('date').agg({
        'launched': 'sum',
        'destroyed': 'sum'
    }).reset_index()
    # Calculate the daily interception rate
    daily_data['interception_rate'] = (daily_data['destroyed'] / daily_data['launched'] * 100).fillna(0).round(0).astype(int)
    daily_data['interception_rate'] = daily_data['interception_rate'].astype(str) + '%'
    return daily_data

def monthly_interception_rate(data):
    # Convert 'date' to datetime object for proper resampling
    data['date'] = pd.to_datetime(data['date'])
    # Group by month and sum the values of 'launched' and 'destroyed'
    monthly_data = data.resample('M', on='date').sum().reset_index()
    # Calculate the interception rate based on monthly sums, round, and convert to string with '%'
    monthly_data['interception_rate'] = (monthly_data['destroyed'] / monthly_data['launched'] * 100).fillna(0).round(0).astype(int)
    monthly_data['interception_rate'] = monthly_data['interception_rate'].astype(str) + '%'
    # Format date to show only year and month for readability in the chart
    monthly_data['date'] = monthly_data['date'].dt.strftime('%Y-%m')
    return monthly_data

def plot_data(data):
    fig = px.bar(data, x='date', y=['launched', 'destroyed'],
                 labels={'value': 'Count', 'variable': 'Category'},
                 color_discrete_map={'launched': 'darkblue', 'destroyed': 'darkgray'},
                 barmode='group')
    fig.update_traces(marker_line_width=0)
    fig.update_layout(
        title='Missiles Launched vs Destroyed Over Time',
        xaxis_title='Date',
        yaxis_title='Number of Missiles',
        xaxis=dict(
            title_font=dict(size=18, color='black'),
            tickfont=dict(size=16, color='black'),
            rangeslider=dict(visible=True),  # Enable the range slider
            type='date'  # Ensure the x-axis is treated as date
        ),
        yaxis=dict(
            title_font=dict(size=20, color='black'),
            tickfont=dict(size=18, color='black'),
            range=[0, 110]
        )
    )
    return fig

def plot_interception_rate(data):
    fig = px.line(data, x='date', y='interception_rate', color_discrete_sequence=['darkblue'])
    fig.update_traces(line=dict(width=4))
    fig.update_layout(
        title='Monthly Average Interception Rate Over Time',
        xaxis_title='Month',
        yaxis_title='Interception Rate (%)',
        xaxis=dict(
            title_font=dict(size=18, color='black'),
            tickfont=dict(size=16, color='black'),
            tickangle=-90,
            tickmode='linear',
            dtick='M1',
            rangeslider=dict(visible=True),  # Enable the range slider
            type='date'  # Ensure the x-axis is treated as date
        ),
        yaxis=dict(
            title_font=dict(size=20, color='black'),
            tickfont=dict(size=18, color='black'),
            range=[50, 100]
        )
    )
    return fig


# Streamlit app interface
st.title('Ukraine dashboard')
st.subheader('Missiles fired, intercepted, and interception rate')
placeholder = st.empty()

if 'data_loaded' not in st.session_state:
    st.session_state['data_loaded'] = False

if st.sidebar.button('Get Data', type="primary"):

    download_dataset()
    st.session_state['data_loaded'] = True

if not st.session_state['data_loaded']:
    st.markdown("To begin, click the 'GET DATA' button on the left panel")
if st.session_state['data_loaded']:
    # This button will allow users to download 'missile_attacks_daily.csv' once it's available
    success = st.success('Data downloaded and extracted successfully!')
    time.sleep(1) # Wait for 1 second
    success.empty() # Clear the alert

    st.markdown(
        "_The database is hosted on Kaggle and updated often. You can find more details [here](https://www.kaggle.com/datasets/piterfm/massive-missile-attacks-on-ukraine)._",
        unsafe_allow_html=True
    )    
    with open("missile_attacks_daily.csv", "rb") as file:
        btn = st.sidebar.download_button(
            label="Export Data",
            data=file,
            file_name="missile_attacks_daily.csv",
            mime="text/csv"
            )
    data = pd.read_csv("missile_attacks_daily.csv")

    # Process the dataset
    data_processed = remove_time(data.copy())  # Remove time part first
    data_processed = process_dataset(data_processed)  # Process the dataset
    data_aggregated = aggregate_data(data_processed)  # Aggregate the data by day

    latest_date = data_aggregated['date'].max()
    earliest_date = data_aggregated['date'].min()
    latest_missiles_fired = int(data_aggregated[data_aggregated['date'] == latest_date]['launched'].sum())

    # Displaying Date Selectors
    st.sidebar.title("Choose Date Range")
    start_date = st.sidebar.date_input("Start Date", min_value=earliest_date, max_value=latest_date, value=earliest_date)
    end_date = st.sidebar.date_input("End Date", min_value=earliest_date, max_value=latest_date, value=latest_date)
    date_range = start_date,end_date


    # Displaying Summary Information
    st.sidebar.title ("Summary")
    st.sidebar.markdown(f"* **Information up to:** {latest_date.strftime('%Y-%m-%d')}")
    st.sidebar.markdown(f"* **Latest number of missiles fired:** {latest_missiles_fired}")
    st.sidebar.markdown(f"* **Data since:** {earliest_date.strftime('%Y-%m-%d')}")

    # Calculate monthly interception rate
    data_monthly_rate = monthly_interception_rate(data_aggregated.copy())  # Aggregate interception rate by month

    # Filter daily data based on selected date range
    filtered_data = data_aggregated[(data_aggregated['date'] >= date_range[0]) & (data_aggregated['date'] <= date_range[1])]
    # Also filter the monthly data by the selected date range
    filtered_monthly_data = data_monthly_rate[(pd.to_datetime(data_monthly_rate['date']).dt.date >= date_range[0]) & 
                                              (pd.to_datetime(data_monthly_rate['date']).dt.date <= date_range[1])]

    # Display the bar chart for launched vs destroyed
    st.plotly_chart(plot_data(filtered_data), use_container_width=True)
    
    # Display the bar chart for monthly interception rate
    st.plotly_chart(plot_interception_rate(filtered_monthly_data), use_container_width=True)

    st.subheader("Data:")

    # Display processed data below the charts
    col1, col2 = st.columns([1, 1])  # Split the layout into two columns
    with col1:
        st.write("Missiles launched and intercepted:", filtered_data)
    with col2:
        st.write("Monthly Interception Rates:", filtered_monthly_data)
