"""
Original credit to author AsTheSeaRises, project SunSynk_API
https://github.com/AsTheSeaRises/SunSynk_API
"""
# 96762 ticket id for IT support
import sys
import requests
import json
from io import StringIO 
import pandas as pd
import datetime
from math import floor, ceil
import typer
from typing_extensions import Annotated
from pathlib import Path


# Enter your username and password that you created on the Sunsynk website.
#my_user_email=str(sys.argv[1]) if len(sys.argv) > 1 else None
#my_user_password=str(sys.argv[2]) if len(sys.argv) > 2 else None
#inverter_id=str(sys.argv[3]) if len(sys.argv) > 3 else None

loginurl = ('https://pv.inteless.com/oauth/token')
#loginurl = ("https://api.sunsynk.net/oauth/token")
#loginurl = ("https://api.sunsynk.net/oauth/token/new")


# API call to set inverter settings
#the_bearer_token_string = None
desired_soc = 75
emergency_soc = 35
min_soc = 14
charging_rate = 5500
default_start_time = datetime.time(2,0)  # 2:00 am
default_start_time_soc_threshold = 30.0
today_date = datetime.datetime.now().date()

api_base_url = "https://api.sunsynk.net/api/v1"

agile_page_size = 250
agile_url = f"https://api.octopus.energy/v1/products/AGILE-24-04-03/electricity-tariffs/E-1R-AGILE-24-04-03-A/standard-unit-rates/?page_size={agile_page_size}"




def set_globals(inverter_id):
    
    global set_url
    set_url = f"{api_base_url}/common/setting/{inverter_id}/set"

    global inverter_status_url
    inverter_status_url = f"{api_base_url}/inverter/battery/{inverter_id}/realtime?sn={inverter_id}&lan=en"

    global inverter_power_data_url
    inverter_power_data_url = f'{api_base_url}/inverter/grid/{inverter_id}/day?lan=en&date={today_date.strftime("%Y-%m-%d")}&column=pac'
    
    global inverter_battery_power_data_url
    inverter_battery_power_data_url = f'{api_base_url}/inverter/battery/{inverter_id}/day?lan=en&date={today_date.strftime("%Y-%m-%d")}&column=p_bms'
 
    global inverter_data
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
def my_bearer_token( email, pw ):
    headers = {
    'Content-type':'application/json',
    'Accept':'application/json'
    }
    #pw="VWBKb3iaQUy76524t5JhGHvbehwdNYPylKwZKEGVIaDPU6LJBzq6u6H/p/5l3Bm+n5Gd3WUodAvnjWHqU0Obn9k7weeB2G0UFR3Xc/kzb/TnfhXpAMju09Bh856FWpgC/U8DxAh0IQK/oK1c4eTVF+WT0Wpm+7Z/g1H1E5o/hGMoq5/uf8ZRjLk6B2ZBX1FxXZk/97Ki0icfHW5TZ3z2sppN2C7gVTNQ5rcRYRtFP1oE2clwXojDyzth295gqaGjf1jpHI2IVDzyMe0Ocu00WbfABzt17CnyOcZd8NpaWxkbpn6S8/RNqBxV65Zh+D8BBIE6QYkunwCKpD/bgYEKEDfZFj4czX8Smc35/QhZKe+PvtCK5gMK0yuqLP2o4m0XMLn8R9r7He/lLJ+u0SfuMd7XYk2h9IWDGqq6HLEktvSTEdSXWf4hrgfsGgoTMd2dZccC5JB4tsRABH93ykvqGw3C+b1/y8KxQJW4+BfpBlkgqLFU898lu34c7OosnQJ9z8BljH2QXcxoWul5r1zQj4g8OdVIaNuTWuRCydgtFGUW0Uf68VHS2pr0IJNajNEpGzS7JXTOT2ZaJEdxGobRGtigIjM0zuH1urEETO20sX+D1nuTqFLu1K2tO1csguXeVn0HWG88E5N4dHjpdNY8WmoqRPtgy8M1tqruSVYnnpc="
    pw2="NIrk67POo0QxAOiewp2poFfL9o0/mWnEFqIoC/Z8wsUpCHEJzf3MULBGmdfeGrhik4LDk8sIGcsrOkURUDL+vyINQGXpOyT7DTXULjwHG3dIywVopHw+iNnCW4rIV+N0TLg8cj5csjvFrPK3fJ19VYsXhacQGIa2+jzkZuf31JczJoEaxW+Q1JF/ZNdKqkd+O2mly28rAxrlkBRqSuwPIen7BsSzOOL7yfJN2AXEHyr0roEJR/ZZ9/BXGndmeu47TRS3M8HHNLWnhQlby29URQW6Kl6ZyeK6nwm6kZl7RQPwHaVPFaEYdZb4pb3244P3Hq4i603SA74tq4muF2oCjGcH+KTiYJvfadiHbdi436Ymh8VGHHxJ4vRq77WkVjDJ5ilAS7ovw5qCGYGUPA45W2oIMHqxFvjceFJQ0H/tIaN03YW3GwcrWjzoE9SK66gELN237ECp5lVlBx0kbRgaSQsa2YNwvl6syEG7CqZzrhN6JajffIyhwmNH9adZDpIowdwDd5PWfLc4cdloU6eCDLpa+yzH/V465DL6wVIwK4BZuJ5s1eb7oOsQzgMh5X3QegBG+ZWDQjKEf+1XbSS8CwSKCsNDX2SC4WoiACmfgTcjZ5XfGXNiM9G6WK8ISURZYUBvcv43zw0aPLZfLfq8rm4uWT0fc6TdItqBuQYPX1Y="
    payload = {
        "username": email,
        "password": pw,
        "grant_type":"password",
        "client_id":"csp-web",
        "source":"sunsynk"
        }
    raw_data = requests.post(loginurl, json=payload, headers=headers).json()
    print(raw_data)
    # Your access token extracted from response
    my_access_token = raw_data["data"]["access_token"]


    bearer_token_string = ('Bearer '+ my_access_token)
    print('****************************************************')
    print('Your access token is: ' + my_access_token)
    return bearer_token_string

# perform an example set
def set_inverter_settings(times, soc_cap=100):
    headers_and_token = {
        'Content-type': 'application/json',
        'Accept': 'application/json',
        'Authorization': the_bearer_token_string
    }

    for index in range(0, len(times), 1 ):
        data_time_index = f"sellTime{index+1}" 
        data_cap_index = f"cap{index}"  # cap0 does not exist, this is just for convenience 
        timeon_index = f"time{index}on"  # note that time0on does not exist, this is just for convenience

        inverter_data[ data_time_index ] = times[index]
        inverter_data[ data_cap_index ] = soc_cap
        inverter_data[ timeon_index ] = True

    #inverter_data["sellTime1"] = start_time
    #inverter_data["sellTime2"] = end_time
    #inverter_data["cap1"] = soc_cap

    print(f"setting time bracket for charging to {times[0]}-{times[-1]} with cap of {soc_cap} % ")
    
    r = requests.post(set_url, headers=headers_and_token, json=inverter_data)

    print(r)  # status, 200 is good?
    print(f'time bracket set to {times}')


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
    """
    Returns the times [time1, time2, time3 etc] to set the Sunsynk API to for charging

    usually time1 would be start, and time2 would be end.

    Doesn't contain which day, just the times.  Care must be taken to adjust for correct day!
    """

    # calculate median price for the whole dataset 
    median_price = df["value_inc_vat"].median()
    #print(median_price)

    # filter to most recent day
    #max_date = df["valid_from"].max().date()
    #date_mask = (df["valid_from"].dt.date.values >= max_date )

    # filter to next 24 hours from current time
    dt_now = pd.to_datetime('today').tz_localize("Europe/London") 
    dt_now_p24 = dt_now + datetime.timedelta(days=1)
    date_mask = ( df["valid_from"] >= dt_now ) & ( df["valid_from"] < dt_now_p24 )


    df = df.loc[ date_mask ].sort_values( "valid_from", ascending=True ).set_index("valid_from")

    # if soc is very low, force to earlier charge
    if current_soc <= emergency_soc:
        df = df.between_time("0:00", "5:00")
    

    global desired_soc  # TODO ugly, should rewrite to object oriented

    # take advantage of cheaper prices
    min_interval_price = df["value_inc_vat"].min()  
    if min_interval_price < (median_price/2.0):
        print( f"adding extra charge time.  Upcoming min price is {min_interval_price} as opposed to recent median of {median_price}" )
        
        desired_soc = 85  # seeing as it's cheaper, why not?
        minutes += 20
    
    if min_interval_price < (median_price/3.0):
        print( f"adding yet more charge time.  Upcoming min price is {min_interval_price} as opposed to recent median of {median_price}, and setting max SOC to 100%" )
        
        desired_soc = 100  # seeing as it's dirt cheap, why not?
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

    charge_times = adjust_times_for_day_span( [ start_time, end_time ] )
    

    return(minutes, charge_times)
    

def adjust_times_for_day_span( times ):
    """
    if end_time is on the next day (smaller), then we need to make an
    adjustment as the sunsynk API just breaks and doesn't charge if this occurs
    """
    if times[0] > times[1]:
        return( [ times[0], datetime.time(hour=23, minute=59), times[1] ] )
    
    return(times)


def format_times( times ): 
    formatted_times = []

    for t_obj in times:
        formatted_times.append( t_obj.strftime("%H:%M") )
    
    return( formatted_times )

def best_negative_window(row=None, charge_minutes=None):
    """
    Intended to be used with pd.DataFrame.apply
    """
    timedelta_diff = row["valid_to"].max() - row["valid_from"].min()
    minutes = timedelta_diff.seconds / 60.0
    start_time = row["valid_from"].min()
    end_time = row["valid_to"].max()
    return(minutes, start_time, end_time)
    

def main(
        user_email: Annotated[str, typer.Option("-u", help="user email address")],
        user_password: Annotated[str, typer.Option("-p", help="user password")],
        inverter_code: Annotated[str, typer.Option("-i", help="ID for Inverter")],
        bearer_token_path: Annotated[str, typer.Option("-t", help="path to token file")] = None
):
    
    global the_bearer_token_string
    if bearer_token_path:
        bearer_token_path2 = Path(bearer_token_path)

        with bearer_token_path2.open("r") as bearer_token_handle:
            the_bearer_token_string = bearer_token_handle.read().strip()
    else:    
        the_bearer_token_string = my_bearer_token(user_email, user_password)

    set_globals(inverter_code)

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
    current_minutes, charge_times = get_times(costs_df, minutes=charge_minutes, current_soc=current_soc) 

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
                charge_times = adjust_times_for_day_span([start_time, end_time])
                print( f"Found large negative cost window, resetting times to {item[1][1]} and {item[1][2]}")
    
    
    formatted_charge_times = format_times(charge_times)
    print(f"charge times are {formatted_charge_times}")
    set_inverter_settings(formatted_charge_times, soc_cap=desired_soc)


if __name__ == "__main__":
    typer.run(main)