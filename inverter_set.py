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
from math import floor, ceil


# Enter your username and password that you created on the Sunsynk website.
my_user_email=str(sys.argv[1]) if len(sys.argv) > 1 else None
my_user_password=str(sys.argv[2]) if len(sys.argv) > 2 else None
inverter_id=str(sys.argv[3]) if len(sys.argv) > 3 else None

#loginurl = ('https://pv.inteless.com/oauth/token')
loginurl = ("https://api.sunsynk.net/oauth/token")


# API call to set inverter settings
the_bearer_token_string = None
desired_soc = 90
emergency_soc = 35
min_soc = 14
charging_rate = 5500
default_start_time = datetime.time(2,0)  # 2:00 am
default_start_time_soc_threshold = 30.0
today_date = datetime.datetime.now().date()

api_base_url = "https://api.sunsynk.net/api/v1"
set_url = f"{api_base_url}/common/setting/{inverter_id}/set"

inverter_status_url = f"{api_base_url}/inverter/battery/{inverter_id}/realtime?sn={inverter_id}&lan=en"

inverter_power_data_url = f'{api_base_url}/inverter/grid/{inverter_id}/day?lan=en&date={today_date.strftime("%Y-%m-%d")}&column=pac'
inverter_battery_power_data_url = f'{api_base_url}/inverter/battery/{inverter_id}/day?lan=en&date={today_date.strftime("%Y-%m-%d")}&column=p_bms'
agile_page_size = 250
agile_url = f"https://api.octopus.energy/v1/products/AGILE-24-04-03/electricity-tariffs/E-1R-AGILE-24-04-03-A/standard-unit-rates/?page_size={agile_page_size}"


inverter_data = {
  "sn": inverter_id,
  "safetyType": "0",
  "battMode": "-1",
  "solarSell": "1",
  "pvMaxLimit": "5400",
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
  "sellTime2Pac": charging_rate,
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
def my_bearer_token( email, pw):
    headers = {
    'Content-type':'application/json',
    'Accept':'application/json'
    }

    payload = {
        "username": email,
        "password": pw,
        "grant_type":"password",
        "client_id":"csp-web"
        }
    raw_data = requests.post(loginurl, json=payload, headers=headers).json()
    # Your access token extracted from response
    my_access_token = raw_data["data"]["access_token"]

    bearer_token_string = ('Bearer '+ my_access_token)
    print('****************************************************')
    print('Your access token is: ' + my_access_token)
    return bearer_token_string

# perform an example set
def set_inverter_settings(start_time, end_time, soc_cap=100):
    headers_and_token = {
        'Content-type': 'application/json',
        'Accept': 'application/json',
        'Authorization': the_bearer_token_string
    }
    inverter_data["sellTime1"] = start_time
    inverter_data["sellTime2"] = end_time
    inverter_data["cap1"] = soc_cap
    
    r = requests.post(set_url, headers=headers_and_token, json=inverter_data)

    print(r)  # status, 200 is good?
    print(f'time bracket set to {inverter_data["sellTime1"]} and {inverter_data["sellTime2"]}')


def calc_inverter_charge_wattage():
    """
    Not currently used, below function supercedes this
    """
    headers_and_token = {
        'Content-type': 'application/json',
        'Accept': 'application/json',
        'Authorization': the_bearer_token_string
    }
    
    r = requests.get(inverter_power_data_url, headers=headers_and_token)
    data = r.json()

    #print(data["data"]["infos"][0]["records"])

    dts = []
    powers = []
    for row in data["data"]["infos"][0]["records"]:
        dts.append(row["time"])
        powers.append(float(row["value"]))

    df = pd.DataFrame.from_dict( {"datetime":dts, "power": powers} ).set_index("datetime")
    print(df)
    return( df.loc[ df["power"] > 0.0 , "power"].median() )


def calc_battery_charge_wattage():
    """
    Calculates the charge rate of the battery
    """
    headers_and_token = {
        'Content-type': 'application/json',
        'Accept': 'application/json',
        'Authorization': the_bearer_token_string
    }
    
    r = requests.get(inverter_battery_power_data_url, headers=headers_and_token)
    data = r.json()

    #print(data["data"]["infos"][0]["records"])

    dts = []
    powers = []
    for row in data["data"]["infos"][0]["records"]:
        dts.append(row["time"])
        powers.append(float(row["value"]))

    df = pd.DataFrame.from_dict( {"datetime":dts, "power": powers} ).set_index("datetime")
    print(df)
    return( df.loc[ df["power"] < 0.0 , "power"].min() )


def calc_charge_time(desired_charge_rate, soc_cap=100.0):
    headers_and_token = {
        'Content-type': 'application/json',
        'Accept': 'application/json',
        'Authorization': the_bearer_token_string
    }
    
    r = requests.get(inverter_status_url, headers=headers_and_token)
    data = r.json()
    print(data)
    capacity_watts = data["data"]["correctCap"] * data["data"]["bmsVolt"]
    current_soc = data["data"]["bmsSoc"]

    watts_to_charge = (1.0 - (current_soc / soc_cap)) * capacity_watts
    charge_minutes = floor( 60 * watts_to_charge / desired_charge_rate ) 


    print(charge_minutes)
    return( max( charge_minutes, 0 ), current_soc )


def get_agile_data():
    r = requests.get(agile_url)
    data = r.json()
    #df = pd.read_json( StringIO(data) )
    #dtypes = { "valid_from" : "datetime", "valid_to" : "datetime", "value_inc_vat" : "float", "value_exc_vat" : "float", "payment_method": "string" }
    
    # convert dict (from JSON) to dataframe
    df = pd.DataFrame.from_dict(data["results"])

    # type conversion
    df["valid_from"] = pd.to_datetime( df["valid_from"] )
    df["valid_to"] = pd.to_datetime( df["valid_to"] )

    # account for daylight savings
    df["valid_from"] = df["valid_from"].apply(lambda r: r.tz_convert("Europe/London") )
    df["valid_to"] = df["valid_to"].apply(lambda r: r.tz_convert("Europe/London") )

    #df["valid_from"] = df["valid_from"].to_timestamp( )
    #df["valid_to"] = df["valid_to"].to_timestamp( )

    return df


def calc_negative_windows(df):

    df_windowing = df
    df_windowing["positive"] = df_windowing["value_inc_vat"] >= 0
    df_windowing["group"] = df_windowing["positive"].cumsum()

    df_neg = df_windowing.loc[ df_windowing["positive"] == False ]

    boundaries_df = df_neg.groupby(by="group") 
    # boundaries_df.min()  
    return(boundaries_df)

    # aggregage (groupby) based on the cumsum, filter where occurrence > 1, and use these to choose boundaries

    # different indexers may be useful here
    # https://pandas.pydata.org/docs/user_guide/window.html#custom-window-rolling


def get_times(df, minutes=90, current_soc=100):

    # calculate median price for the whole dataset 
    median_price = df["value_inc_vat"].median()
    #print(median_price)

    # filter to most recent day
    max_date = df["valid_from"].max().date()
    date_mask = (df["valid_from"].dt.date.values >= max_date )




    df = df.loc[ date_mask ].sort_values( "valid_from", ascending=True ).set_index("valid_from")

    # if soc is very low, force to earlier charge
    if current_soc <= emergency_soc:
        df = df.between_time("0:00", "5:00")
    

    # take advantage of cheaper prices
    min_interval_price = df["value_inc_vat"].min()  
    if min_interval_price < (median_price/1.75):
        print( f"adding extra charge time.  Upcoming min price is {min_interval_price} as opposed to recent median of {median_price}" )
        minutes += 20
    
    if min_interval_price < (median_price/4.0):
        minutes += 20

    # rolling average (assumed that each interval is 30 minutes)
    window_size = ceil(minutes/30)
    indexer = pd.api.indexers.FixedForwardWindowIndexer(window_size=window_size)  # look forward
    rolling_df = df.rolling(indexer).mean(numeric_only=True)
    min_day_price = rolling_df["value_inc_vat"].min()  

    


    # choose best row and calculate start and end times
    cheapest_row = rolling_df.loc[ rolling_df["value_inc_vat"] == min_day_price ]
    print(f"cheapest row of rolling data with price of {min_day_price}:")
    print(cheapest_row)

    if current_soc < default_start_time_soc_threshold:
        start_time = cheapest_row.index.replace( hour=default_start_time.hour, minute=default_start_time.minute  )
        end_time = (cheapest_row.index + datetime.timedelta(minutes=minutes)).time[0]
    else:
        start_time = cheapest_row.index.time[0]
        end_time = (cheapest_row.index + datetime.timedelta(minutes=minutes)).time[0]

    end_time = (cheapest_row.index + datetime.timedelta(minutes=minutes)).time[0]
    print(end_time)

    return(minutes, start_time.strftime("%H:%M"), end_time.strftime("%H:%M"))
    
    

def best_negative_window(row=None, charge_minutes=None):
    """
    Intended to be used with pd.DataFrame.apply
    """
    timedelta_diff = row["valid_to"].max() - row["valid_from"].min()
    minutes = timedelta_diff.seconds / 60.0
    start_time = row["valid_from"].min().strftime("%H:%M")
    end_time = row["valid_to"].max().strftime("%H:%M")
    return(minutes, start_time, end_time)
    

if __name__ == "__main__":
    the_bearer_token_string = my_bearer_token(my_user_email, my_user_password)

    actual_charge_rate = abs( calc_battery_charge_wattage() )
    print(f"best battery charge rate of {actual_charge_rate}")
    desired_charge_rate = actual_charge_rate
    
    # arbitrary - if more than half of the default, we set this
    if actual_charge_rate > (charging_rate/2):
        print( f"Setting charge rate for time calculations to {actual_charge_rate} instead of defined {charging_rate} due to historic trends")
        actual_charge_rate = actual_charge_rate
    else:
        desired_charge_rate = charging_rate


    current_minutes, current_soc = calc_charge_time(desired_charge_rate, soc_cap = desired_soc)
    charge_minutes = current_minutes + 10
    print( f"Setting charging minutes to {charge_minutes} to reach desired battery charge % of {desired_soc}")
    
    # agile data 
    costs_df = get_agile_data()
    

    print(costs_df)
    current_minutes, start_time, end_time = get_times(costs_df, minutes=charge_minutes, current_soc=current_soc) 

    # handle negative windows
    # filter on recent dates (now)
    # calc time window - if better than charge_minutes then set to these
    dtn = pd.Timestamp(datetime.datetime.now()).tz_localize("Europe/London")
    costs_df_recent = costs_df.loc[ costs_df["valid_from"] >= dtn ]

    b_df = calc_negative_windows(costs_df_recent)
    nw_df = b_df.apply(best_negative_window)
    print(nw_df)
    if len(nw_df) > 0:
        for item in nw_df.items():
            if item[1][0] > current_minutes:
                current_minutes = item[1][0]
                start_time=item[1][1]
                end_time=item[1][2]
                print( f"Found large negative cost window, resetting times to {item[1][1]} and {item[1][2]}")
        
    
    set_inverter_settings(start_time, end_time, soc_cap=desired_soc)
