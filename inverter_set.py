"""
Original credit to author AsTheSeaRises, project SunSynk_API
https://github.com/AsTheSeaRises/SunSynk_API

password salting help from - https://github.com/restrive/sunsynk/blob/c9f9ec806d3e0bb7113461e89d9915865f646562/custom_components/sunsynk_sync/api_client.py
"""
# 96762 ticket id for IT support

import requests
import urllib
import json
import pandas as pd
import datetime
import time
from math import floor, ceil
import typer
from typing_extensions import Annotated
from pathlib import Path

import uuid
import hashlib
from base64 import b64decode, b64encode
import hmac

from Crypto.Cipher import PKCS1_v1_5  # pip install pycryptodome
from Crypto.PublicKey import RSA



# Enter your username and password that you created on the Sunsynk website.
#my_user_email=str(sys.argv[1]) if len(sys.argv) > 1 else None
#my_user_password=str(sys.argv[2]) if len(sys.argv) > 2 else None
#inverter_id=str(sys.argv[3]) if len(sys.argv) > 3 else None

#loginurl = ('https://pv.inteless.com/oauth/token')
#loginurl = "https://api.sunsynk.net/oauth/token"
loginurl = "https://api.sunsynk.net/oauth/token/new"


# API call to set inverter settings
#the_bearer_token_string = None
desired_soc = 90
#emergency_soc = 35
min_soc = 14
charging_rate = 5500
default_start_time = datetime.time(2,0)  # 2:00 am
default_start_time_soc_threshold = 30.0
today_date = datetime.datetime.now().date()
default_source = "sunsynk"

login_base_url = "https://api.sunsynk.net"
api_base_url = "https://api.sunsynk.net/api/v1"

agile_page_size = 250
agile_url = f"https://api.octopus.energy/v1/products/AGILE-24-04-03/electricity-tariffs/E-1R-AGILE-24-04-03-A/standard-unit-rates/?page_size={agile_page_size}"

VERIFY_SSL = False


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

"""def createUuid() :
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    var r = Math.random()*16|0, v = c == 'x' ? r : (r&0x3|0x8);
    return v.toString(16);
    })
"""

# not used
def urlToSign(headers, data) :
    params = {}
    contentType = headers["Content-Type"]
    
    if contentType and contentType.startswith('application/x-www-form-urlencoded') :
        formParams = data.split("&")
        for p in formParams :
            ss = p.split('=')
            params[ss[0]] =  ss[1]
        

    ss = "oauth/token".split('?')
    if ( len(ss) > 1 and ss[1]) :
        queryParams = ss[1].split('&')
        for p in queryParams :
            ss = p.split('=')
            params[ss[0]] = ss[1]
        

    sortedKeys = list( params.keys() )
    sortedKeys.sort()

    first = True
    qs = None
    for k in sortedKeys:
        s = k + "=" + params[k]
        qs = qs + "&" + s  if qs else s
        print("key=" + k + " value=" + params[k] )
    

    url = ss[0]
    return url + "?" + qs if qs else url 
    


def _fetch_public_key() -> str:
    nonce = str(int(time.time() * 1000))
    query = f"nonce={nonce}&source={default_source}"
    sign = hashlib.md5((query + "POWER_VIEW").encode("utf-8")).hexdigest()
    path = f"{login_base_url}/anonymous/publicKey?{query}&sign={sign}"
    #payload = self._request("GET", path, require_success=True)
    payload = requests.get(path).json()
    public_key = payload["data"] if isinstance(payload, str) else payload.get("data")
    if not public_key:
        raise Exception("Failed to obtain Sunsynk public key")
    return public_key

 
def _encrypt_password(password : str, base64_key: str) -> str:
        pem = f"-----BEGIN PUBLIC KEY-----\n{base64_key}\n-----END PUBLIC KEY-----"
        rsa_key = RSA.import_key(pem)
        cipher = PKCS1_v1_5.new(rsa_key)
        encrypted = cipher.encrypt( password.encode("utf-8"))
        return b64encode(encrypted).decode("ascii")


# Sunsynk support gave me this
# not used
def sunsynk_sign(method, url, headers, body, content_type, app_secret, forced_header_list):
    string_to_sign, signature_headers = build_string_to_sign(
        method, headers, url, body, content_type, forced_header_list
    )
    signature = base64.b64encode(
        hmac.new(app_secret.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256).digest()
    ).decode("ascii")
    return signature, signature_headers


# This function will print your bearer/access token
def my_bearer_token( email, pw ):



    #nonce = str( uuid.uuid4() )
    nonce = int(time.time() * 1000)
    public_key = _fetch_public_key()
    encrypted_password = _encrypt_password(pw, public_key)
    sign_str = f"nonce={nonce}&source={default_source}{public_key[:10]}"
    sign = hashlib.md5(sign_str.encode("utf-8")).hexdigest()

    payload = {
        "username": email,
        "password": encrypted_password,
        "nonce": nonce,
        "sign" : sign,
        "grant_type":"password",
        "client_id":"csp-web",
        "source":"sunsynk"
    }

    headers = {
        'Content-Type':'application/json',
        'Accept':'application/json'
    }


    body_json = json.dumps(payload, separators=(",",":"))
    raw_data = requests.post(loginurl, data=body_json, headers=headers, verify=VERIFY_SSL).json()
    print(raw_data)
    # Your access token extracted from response
    my_access_token = raw_data["data"]["access_token"]


    bearer_token_string = ('Bearer '+ my_access_token)
    print('****************************************************')
    print('Your access token is: ' + my_access_token)
    return bearer_token_string

"""
    appKey="204013305"
    appSecret=""
    signature=""
    signatureHeaders=""
    md5= b64encode( hashlib.md5( json.dumps(payload).encode() ).digest() ).decode() 
    headers2 = {
        'Content-Type':'application/json;charset=UTF-8',
        'Accept':'application/json',
        "Content-MD5":md5,
        "X-Ca-Nonce":str(nonce),
        "X-Ca-Key":appKey,
        "X-Ca-Signature":signature,
        "X-Ca-Signature-Headers":signatureHeaders
    }
    
    textToSign = "POST";
    textToSign += headers["Accept"] + "\n";
    textToSign += md5 + "\n";
    textToSign += headers["Content-Type"] + "\n";
    textToSign += "\n";

    
    signatureHeaders = None;
    sortedKeys = list(headers.keys())
    sortedKeys.sort()
    for headerName in sortedKeys:
        textToSign += headerName + ":" + headers[headerName] + "\n";
    signatureHeaders = ",".join(sortedKeys)
    
    textToSign += urlToSign(headers, payload)    

    print( f"textToSign is {textToSign}")

    hash = hmac.new(appSecret.encode("utf-8"), msg=textToSign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    #print("hash:" + hash)
    signature = b64encode(hash).decode("ascii")
    print("signature:" + signature)

    #headers['X-Ca-Signature'] = signature
    #headers['X-Ca-Signature-Headers'] = signatureHeaders
    

    print(loginurl)
    print(payload)
"""

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
    print(the_bearer_token_string)
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


    data = {}
    try:
        r = requests.get(agile_url, timeout=30)
        data = r.json()
    except Exception as ex:
        print("requests failed, trying urllib urlopen instead")
        r = urllib.request.urlopen(agile_url, timeout=30)
        data_raw = r.read()
        data = json.loads(data_raw)
        r.close()



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
    if current_soc <= default_start_time_soc_threshold:
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

    start_time = cheapest_row.index.time[0]
    end_time = (cheapest_row.index + datetime.timedelta(minutes=minutes)).time[0]

    """
    if current_soc < default_start_time_soc_threshold:
        #start_time = cheapest_row.index.replace( hour=default_start_time.hour, minute=default_start_time.minute  )
        start_time = default_start_time
        end_time = (cheapest_row.index + datetime.timedelta(minutes=minutes)).time[0]
    else:
        start_time = cheapest_row.index.time[0]
        end_time = (cheapest_row.index + datetime.timedelta(minutes=minutes)).time[0]"""

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