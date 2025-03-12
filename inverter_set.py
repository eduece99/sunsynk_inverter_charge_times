"""
Original credit to author AsTheSeaRises, project SunSynk_API
https://github.com/AsTheSeaRises/SunSynk_API
"""

import sys
import requests
import json
from io import StringIO 
import pandas as pd
import datetime
from math import floor


# Enter your username and password that you created on the Sunsynk website.
my_user_email=str(sys.argv[1])
my_user_password=str(sys.argv[2])
inverter_id=str(sys.argv[3])

#loginurl = ('https://pv.inteless.com/oauth/token')
loginurl = ("https://api.sunsynk.net/oauth/token")


# API call to set inverter settings
the_bearer_token_string = None
desired_soc = 100
min_soc = 14
charging_rate = 5500
default_start_time = datetime.time(2,0)  # 2:00 am
default_start_time_soc_threshold = 30.0

api_base_url = "https://api.sunsynk.net/api/v1"
set_url = f"{api_base_url}/common/setting/{inverter_id}/set"

inverter_status_url = f"{api_base_url}/inverter/battery/{inverter_id}/realtime?sn={inverter_id}&lan=en"

agile_url = "https://api.octopus.energy/v1/products/AGILE-24-04-03/electricity-tariffs/E-1R-AGILE-24-04-03-A/standard-unit-rates/?page_size=50"


inverter_data = {
  "sn": inverter_id,
  "safetyType": "0",
  "battMode": "-1",
  "solarSell": "1",
  "pvMaxLimit": "5000",
  "energyMode": "0",
  "peakAndVallery": "1",
  "sysWorkMode": "2",
  "sellTime1": "11:30",
  "sellTime2": "13:20",
  "sellTime3": "09:00",
  "sellTime4": "11:30",
  "sellTime5": "16:00",
  "sellTime6": "21:00",
  "sellTime1Pac": charging_rate,
  "sellTime2Pac": "4000",
  "sellTime3Pac": "4000",
  "sellTime4Pac": "4000",
  "sellTime5Pac": "4000",
  "sellTime6Pac": "4000",
  "cap1": desired_soc,
  "cap2": min_soc,
  "cap3": min_soc,
  "cap4": min_soc,
  "cap5": min_soc,
  "cap6": min_soc,
  "sellTime1Volt": "49",
  "sellTime2Volt": "49",
  "sellTime3Volt": "49",
  "sellTime4Volt": "49",
  "sellTime5Volt": "49",
  "sellTime6Volt": "49",
  "zeroExportPower": "0",
  "solarMaxSellPower": "6500",
  "mondayOn": "false",
  "tuesdayOn": "false",
  "wednesdayOn": "false",
  "thursdayOn": "false",
  "fridayOn": "false",
  "saturdayOn": "false",
  "sundayOn": "false",
  "time1on": True,
  "time2on": "false",
  "time3on": "false",
  "time4on": "false",
  "time5on": "false",
  "time6on": "false",
  "genTime1on": "false",
  "genTime2on": "false",
  "genTime3on": "false",
  "genTime4on": "false",
  "genTime5on": "false",
  "genTime6on": "false"
}

# This function will print your bearer/access token
def my_bearer_token():
    headers = {
    'Content-type':'application/json',
    'Accept':'application/json'
    }

    payload = {
        "username": my_user_email,
        "password": my_user_password,
        "grant_type":"password",
        "client_id":"csp-web"
        }
    raw_data = requests.post(loginurl, json=payload, headers=headers).json()
    # Your access token extracted from response
    my_access_token = raw_data["data"]["access_token"]

    the_bearer_token_string = ('Bearer '+ my_access_token)
    print('****************************************************')
    print('Your access token is: ' + my_access_token)
    return my_access_token

# perform an example set
def set_inverter_settings(start_time, end_time):
    headers_and_token = {
        'Content-type': 'application/json',
        'Accept': 'application/json',
        'Authorization': the_bearer_token_string
    }
    inverter_data["sellTime1"] = start_time
    inverter_data["sellTime2"] = end_time
    
    r = requests.post(set_url, headers=headers_and_token, json=inverter_data)

    print(r)  # status, 200 is good?
    print(f'time bracket set to {inverter_data["sellTime1"]} and {inverter_data["sellTime2"]}')


def calc_charge_time():
    headers_and_token = {
        'Content-type': 'application/json',
        'Accept': 'application/json',
        'Authorization': the_bearer_token_string
    }
    
    r = requests.get(inverter_status_url, headers=headers_and_token)
    data = r.json()
    #print(data["data"])
    capacity_watts = data["data"]["correctCap"] * data["data"]["bmsVolt"]
    current_soc = data["data"]["bmsSoc"]

    watts_to_charge = (1.0 - (current_soc / 100.0)) * capacity_watts
    charge_minutes = floor( 60 * watts_to_charge / charging_rate ) 


    print(charge_minutes)
    return( charge_minutes, current_soc )


def get_agile_data(minutes=90, current_soc=100):
    r = requests.get(agile_url)
    data = r.json()
    #df = pd.read_json( StringIO(data) )
    #dtypes = { "valid_from" : "datetime", "valid_to" : "datetime", "value_inc_vat" : "float", "value_exc_vat" : "float", "payment_method": "string" }
    
    # convert dict (from JSON) to dataframe
    df = pd.DataFrame.from_dict(data["results"])

    # type conversion
    df["valid_from"] = pd.to_datetime( df["valid_from"] )
    df["valid_to"] = pd.to_datetime( df["valid_to"] )
    #df["valid_from"] = df["valid_from"].to_timestamp( )
    #df["valid_to"] = df["valid_to"].to_timestamp( )


    # filter to most recent day
    max_date = df["valid_from"].max().date()
    date_mask = (df["valid_from"].dt.date.values >= max_date )
    df = df.loc[ date_mask ].sort_values( "valid_from", ascending=True ).set_index("valid_from")

    # rolling average (assumed that each interval is 30 minutes)
    window_size = floor(minutes/30)
    indexer = pd.api.indexers.FixedForwardWindowIndexer(window_size=window_size)  # look forward
    rolling_df = df.rolling(indexer).mean(numeric_only=True)
    min_day_price = rolling_df["value_inc_vat"].min()  


    # choose best row and calculate start and end times
    cheapest_row = rolling_df.loc[ rolling_df["value_inc_vat"] == min_day_price ]

    if current_soc < default_start_time_soc_threshold:
        start_time = cheapest_row.index.replace( hour=default_start_time.hour, minute=default_start_time.minute  )
        end_time = (cheapest_row.index + datetime.timedelta(minutes=minutes)).time[0]
    else:
        start_time = cheapest_row.index.time[0]
        end_time = (cheapest_row.index + datetime.timedelta(minutes=minutes)).time[0]

    end_time = (cheapest_row.index + datetime.timedelta(minutes=minutes)).time[0]
    print(end_time)

    return(start_time.strftime("%H:%M"), end_time.strftime("%H:%M"))
    
    
    
    

if __name__ == "__main__":
    my_bearer_token()

    current_minutes, current_soc = calc_charge_time()
    charge_minutes = current_minutes + 15

    start_time, end_time = get_agile_data(charge_minutes, current_soc) 
    
    set_inverter_settings(start_time, end_time)
