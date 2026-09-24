"""Sunsynk inverter scheduling utilities.

Original credit to author AsTheSeaRises, project SunSynk_API.
https://github.com/AsTheSeaRises/SunSynk_API

Password salting help from:
https://github.com/restrive/sunsynk/blob/c9f9ec806d3e0bb7113461e89d9915865f646562/custom_components/sunsynk_sync/api_client.py

Edmund Duesbury, 2024-06-05
"""

import datetime
import hashlib
import json
import time
import urllib
from base64 import b64encode
from math import ceil, floor, exp
from pathlib import Path

import pandas as pd
import requests
import typer
from Crypto.Cipher import PKCS1_v1_5  # pip install pycryptodome
from Crypto.PublicKey import RSA
from typing_extensions import Annotated

LOGIN_URL = "https://api.sunsynk.net/oauth/token/new"
LOGIN_BASE_URL = "https://api.sunsynk.net"
API_BASE_URL = "https://api.sunsynk.net/api/v1"
AGILE_PAGE_SIZE = 250
AGILE_URL = (
    "https://api.octopus.energy/v1/products/AGILE-24-04-03/"
    "electricity-tariffs/E-1R-AGILE-24-04-03-A/standard-unit-rates/"
    f"?page_size={AGILE_PAGE_SIZE}"
)
AGILE_OUTGOING_URL = (
    "https://api.octopus.energy/v1/products/AGILE-OUTGOING-19-05-13/"
    "electricity-tariffs/E-1R-AGILE-OUTGOING-19-05-13-L/standard-unit-rates/"
    f"?page_size={AGILE_PAGE_SIZE}"
)
VERIFY_SSL = False
DEFAULT_SOURCE = "sunsynk"
DEFAULT_DESIRED_SOC = 90
MIN_SOC = 14
CHARGING_RATE = 5500
DEFAULT_START_TIME = datetime.time(2, 0)
DEFAULT_START_TIME_SOC_THRESHOLD = 30.0
OCTOPUS_GO_NIGHT_CHARGING_COST = 9.5  # p/kWh


# convenience functions

def round_to_nearest_half_hour(value: datetime.datetime) -> datetime.datetime:
    """Round a datetime to the nearest 30 minutes."""
    minutes = (value.minute // 30) * 30
    if value.minute % 30 >= 15:
        minutes += 30

    rounded = value.replace(minute=0, second=0, microsecond=0)
    return rounded + datetime.timedelta(minutes=minutes)


class SunsynkInverter:
    """Encapsulate the Sunsynk auth, API, and scheduling logic.

    Do not use on its own, please use one of the subclasses for specific tariff strategies.

    Attributes:
        inverter_id (str): Unique inverter serial number.
        desired_soc (int): Target state of charge for charging windows.
        charging_rate (int): Default charge rate in watts.
        bearer_token (str | None): Current bearer token used for authenticated API calls.
    """

    def __init__(
        self,
        inverter_id: str,
        bearer_token: str | None = None,
        desired_soc: int = DEFAULT_DESIRED_SOC,
        charging_rate: int = CHARGING_RATE,
    ) -> None:
        self.inverter_id = inverter_id
        self.desired_soc = desired_soc
        self.charging_rate = charging_rate
        self.bearer_token = bearer_token
        self.today_date = datetime.datetime.now().date()
        self.default_start_time = DEFAULT_START_TIME
        self.default_start_time_soc_threshold = DEFAULT_START_TIME_SOC_THRESHOLD
        self.min_soc = MIN_SOC
        self.set_url = f"{API_BASE_URL}/common/setting/{self.inverter_id}/set"
        self.inverter_status_url = (
            f"{API_BASE_URL}/inverter/battery/{self.inverter_id}/realtime?"
            f"sn={self.inverter_id}&lan=en"
        )
        self.inverter_power_data_url = (
            f"{API_BASE_URL}/inverter/grid/{self.inverter_id}/day?lan=en&"
            f"date={self.today_date.strftime('%Y-%m-%d')}&column=pac"
        )
        self.inverter_battery_power_data_url = (
            f"{API_BASE_URL}/inverter/battery/{self.inverter_id}/day?lan=en&"
            f"date={self.today_date.strftime('%Y-%m-%d')}&column=p_bms"
        )
        self.inverter_data = self._build_default_inverter_data()

    def _build_default_inverter_data(self) -> dict:
        """Create the payload used when configuring charging windows.

        Returns:
            dict: Default settings payload for the inverter.
        """
        return {
            "sn": self.inverter_id,
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
            "sellTime1Pac": self.charging_rate,
            "sellTime2Pac": self.charging_rate,
            "sellTime3Pac": "4000",
            "sellTime4Pac": "4000",
            "sellTime5Pac": "4000",
            "sellTime6Pac": "4000",
            "cap1": self.desired_soc,
            "cap2": self.min_soc,
            "cap3": self.min_soc,
            "cap4": self.min_soc,
            "cap5": self.min_soc,
            "cap6": self.min_soc,
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
            "genTime6on": "false",
        }

    def _auth_headers(self) -> dict:
        """Build the JSON auth headers for API requests.

        Returns:
            dict: Request headers including bearer token when available.
        """
        headers = {"Content-type": "application/json", "Accept": "application/json"}
        if self.bearer_token:
            headers["Authorization"] = self.bearer_token
        return headers

    def _fetch_public_key(self) -> str:
        """Fetch the public key used to encrypt the user password.

        Returns:
            str: Base64-encoded public key.

        Raises:
            RuntimeError: If the public key is missing.
        """
        nonce = str(int(time.time() * 1000))
        query = f"nonce={nonce}&source={DEFAULT_SOURCE}"
        sign = hashlib.md5((query + "POWER_VIEW").encode("utf-8")).hexdigest()
        path = f"{LOGIN_BASE_URL}/anonymous/publicKey?{query}&sign={sign}"
        payload = requests.get(path).json()
        public_key = payload["data"] if isinstance(payload, str) else payload.get("data")
        if not public_key:
            raise RuntimeError("Failed to obtain Sunsynk public key")
        return public_key

    def _encrypt_password(self, password: str, base64_key: str) -> str:
        """Encrypt the user password with the server public key.

        Args:
            password (str): Plaintext user password.
            base64_key (str): Base64-encoded RSA public key.

        Returns:
            str: Encrypted password payload.
        """
        pem = f"-----BEGIN PUBLIC KEY-----\n{base64_key}\n-----END PUBLIC KEY-----"
        rsa_key = RSA.import_key(pem)
        cipher = PKCS1_v1_5.new(rsa_key)
        encrypted = cipher.encrypt(password.encode("utf-8"))
        return b64encode(encrypted).decode("ascii")

    def get_bearer_token(self, email: str, password: str) -> str:
        """Authenticate and store the bearer token.

        Args:
            email (str): Sunsynk username.
            password (str): Sunsynk password.

        Returns:
            str: The bearer token with the "Bearer " prefix.
        """
        nonce = int(time.time() * 1000)
        public_key = self._fetch_public_key()
        encrypted_password = self._encrypt_password(password, public_key)
        sign_str = f"nonce={nonce}&source={DEFAULT_SOURCE}{public_key[:10]}"
        sign = hashlib.md5(sign_str.encode("utf-8")).hexdigest()

        payload = {
            "username": email,
            "password": encrypted_password,
            "nonce": nonce,
            "sign": sign,
            "grant_type": "password",
            "client_id": "csp-web",
            "source": DEFAULT_SOURCE,
        }

        response = requests.post(
            LOGIN_URL,
            data=json.dumps(payload, separators=(",", ":")),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            verify=VERIFY_SSL,
        ).json()
        access_token = response["data"]["access_token"]
        self.bearer_token = f"Bearer {access_token}"
        print(f"Your access token is: {access_token}")
        return self.bearer_token

    def load_bearer_token(self, bearer_token_path: str | Path) -> str:
        """Load a bearer token from disk.

        Args:
            bearer_token_path (str | Path): Path to a token file.

        Returns:
            str: The loaded bearer token.
        """
        token_path = Path(bearer_token_path)
        self.bearer_token = token_path.read_text().strip()
        return self.bearer_token

    def set_inverter_charge_times(self, times: list[str | datetime.time], soc_cap: int = 100) -> None:
        """Set the inverter charging windows.

        Args:
            times (list[str | datetime.time]): Charging times to apply.
            soc_cap (int): Desired state of charge ceiling for the windows.
        """
        if not times:
            raise ValueError("At least one charging time must be supplied.")

        formatted_times = [
            time_value.strftime("%H:%M") if isinstance(time_value, datetime.time) else str(time_value)
            for time_value in times
        ]

        for index, time_value in enumerate(formatted_times, start=1):
            self.inverter_data[f"sellTime{index}"] = time_value
            self.inverter_data[f"cap{index}"] = soc_cap
            self.inverter_data[f"time{index}on"] = True

        print(f"setting time bracket for charging to {formatted_times[0]}-{formatted_times[-1]} with cap of {soc_cap} %")
        response = requests.post(self.set_url, headers=self._auth_headers(), json=self.inverter_data)
        print(response)
        print(f"time bracket set to {formatted_times}")

    def calc_inverter_charge_wattage(self) -> float:
        """Estimate the inverter charge power from the historical grid data.

        Returns:
            float: Median positive charge wattage.
        """
        response = requests.get(self.inverter_power_data_url, headers=self._auth_headers())
        data = response.json()

        dts = []
        powers = []
        for row in data["data"]["infos"][0]["records"]:
            dts.append(row["time"])
            powers.append(float(row["value"]))

        df = pd.DataFrame.from_dict({"datetime": dts, "power": powers}).set_index("datetime")
        print(df)
        return float(df.loc[df["power"] > 0.0, "power"].median())

    def calc_battery_charge_wattage(self) -> float:
        """Calculate the battery charging rate.

        Returns:
            float: Minimum negative charge wattage observed.
        """
        response = requests.get(self.inverter_battery_power_data_url, headers=self._auth_headers())
        data = response.json()

        dts = []
        powers = []
        for row in data["data"]["infos"][0]["records"]:
            dts.append(row["time"])
            powers.append(float(row["value"]))

        df = pd.DataFrame.from_dict({"datetime": dts, "power": powers}).set_index("datetime")
        print(df)
        return float(df.loc[df["power"] < 0.0, "power"].min())

    def calc_charge_time(self, desired_charge_rate: float, soc_cap: float = 100.0) -> tuple[int, float]:
        """Work out how many minutes until the battery reaches the target SoC.

        Args:
            desired_charge_rate (float): Target charge rate in watts.
            soc_cap (float): Maximum permissible state of charge.

        Returns:
            tuple[int, float]: Charge minutes and current SoC.
        """
        response = requests.get(self.inverter_status_url, headers=self._auth_headers())
        data = response.json()
        print(data)

        capacity_watts = data["data"]["correctCap"] * data["data"]["bmsVolt"]
        current_soc = data["data"]["bmsSoc"]
        watts_to_charge = (1.0 - (current_soc / soc_cap)) * capacity_watts
        charge_minutes = floor(60 * watts_to_charge / desired_charge_rate)
        print(charge_minutes)
        return max(charge_minutes, 0), current_soc

    def get_agile_data(self) -> pd.DataFrame:
        """Fetch the Octopus Agile pricing data.

        Octopus Agile pricing data is retrieved from the Octopus Energy API and returned as a pandas DataFrame with timezone-normalised timestamps.

        Override as needed for different pricing APIs or data sources.

        Returns:
            pd.DataFrame: Agile pricing dataset with timezone-normalised timestamps.
        """
        data = {}
        try:
            response = requests.get(AGILE_URL, timeout=30)
            data = response.json()
        except Exception:
            print("requests failed, trying urllib urlopen instead")
            with urllib.request.urlopen(AGILE_URL, timeout=30) as response:
                data = json.loads(response.read())

        df = pd.DataFrame.from_dict(data["results"])
        df["valid_from"] = pd.to_datetime(df["valid_from"]).apply(lambda value: value.tz_convert("Europe/London"))
        df["valid_to"] = pd.to_datetime(df["valid_to"]).apply(lambda value: value.tz_convert("Europe/London"))
        return df

    @staticmethod
    def calc_negative_windows(df: pd.DataFrame):
        """Group consecutive negative-price windows together.

        Args:
            df (pd.DataFrame): Price table.

        Returns:
            pd.core.groupby.generic.DataFrameGroupBy: Grouped negative windows.
        """
        df_windowing = df.copy()
        df_windowing["positive"] = df_windowing["value_inc_vat"] >= 0
        df_windowing["group"] = df_windowing["positive"].cumsum()
        return df_windowing.loc[df_windowing["positive"] == False].groupby(by="group")

    def get_times(self, df: pd.DataFrame, minutes: int = 90, current_soc: int = 100) -> tuple[int, list[datetime.time]]:
        """Return the optimal charging start and end times.

        Args:
            df (pd.DataFrame): Agile tariff frame.
            minutes (int): Desired charging duration in minutes.
            current_soc (int): Battery state of charge at the moment of evaluation.

        Returns:
            tuple[int, list[datetime.time]]: Duration and scheduled times.
        """
        median_price = df["value_inc_vat"].median()
        dt_now = pd.to_datetime("today").tz_localize("Europe/London")
        dt_now_p24 = dt_now + datetime.timedelta(days=1)
        date_mask = (df["valid_from"] >= dt_now) & (df["valid_from"] < dt_now_p24)

        filtered_df = df.loc[date_mask].sort_values("valid_from", ascending=True).set_index("valid_from")

        if current_soc <= self.default_start_time_soc_threshold:
            filtered_df = filtered_df.between_time("0:00", "7:00")

        min_interval_price = filtered_df["value_inc_vat"].min()
        if min_interval_price < (median_price / 1.8):
            print(
                f"adding extra charge time. Upcoming min price is {min_interval_price} "
                f"as opposed to recent median of {median_price}"
            )
            self.desired_soc = 95
            minutes += 20

        if min_interval_price < (median_price / 3.0):
            print(
                f"adding yet more charge time. Upcoming min price is {min_interval_price} "
                f"as opposed to recent median of {median_price}, and setting max SOC to 100%"
            )
            self.desired_soc = 100
            minutes += 20

        window_size = ceil(minutes / 30)
        indexer = pd.api.indexers.FixedForwardWindowIndexer(window_size=window_size)
        rolling_df = filtered_df.rolling(indexer).mean(numeric_only=True)
        min_day_price = rolling_df["value_inc_vat"].min()

        cheapest_row = rolling_df.loc[rolling_df["value_inc_vat"] == min_day_price]
        print(f"cheapest row of rolling data with price of {min_day_price}:")
        print(cheapest_row)

        start_time = cheapest_row.index.time[0]
        end_time = (cheapest_row.index + datetime.timedelta(minutes=minutes)).time[0]
        charge_times = self.adjust_times_for_day_span([start_time, end_time])
        return minutes, charge_times

    @staticmethod
    def adjust_times_for_day_span(times: list[datetime.time]) -> list[datetime.time]:
        """Split windows that cross midnight into a valid two-part charge schedule.

        Args:
            times (list[datetime.time]): Start and end times.

        Returns:
            list[datetime.time]: Adjusted times compatible with the inverter API.
        """
        if times[0] > times[1]:
            return [times[0], datetime.time(hour=23, minute=59), datetime.time(hour=0, minute=0), times[1]]
        return times

    @staticmethod
    def format_times(times: list[datetime.time]) -> list[str]:
        """Convert datetime.time objects into HH:MM strings.

        Args:
            times (list[datetime.time]): Times to convert.

        Returns:
            list[str]: Formatted charge times.
        """
        return [time_value.strftime("%H:%M") for time_value in times]

    @staticmethod
    def best_negative_window(row: pd.Series) -> tuple[float, datetime.datetime, datetime.datetime]:
        """Find the best negative-price window in a grouped row.

        Args:
            row (pd.Series): Row from a groupby apply.

        Returns:
            tuple[float, datetime.datetime, datetime.datetime]: Duration, start, and end times.
        """
        timedelta_diff = row["valid_to"].max() - row["valid_from"].min()
        minutes = timedelta_diff.seconds / 60.0
        return minutes, row["valid_from"].min(), row["valid_to"].max()

    def resolve_bearer_token(
        self,
        user_email: str | None = None,
        user_password: str | None = None,
        bearer_token_path: str | Path | None = None,
    ) -> str:
        """Resolve a bearer token from disk or by authenticating against the API.

        Args:
            user_email (str | None): Sunsynk username.
            user_password (str | None): Sunsynk password.
            bearer_token_path (str | Path | None): Cache file path.

        Returns:
            str: Active bearer token.
        """
        if bearer_token_path:
            return self.load_bearer_token(bearer_token_path)
        if user_email is None or user_password is None:
            raise ValueError("Either a cached token or both user credentials are required.")
        return self.get_bearer_token(user_email, user_password)

    def estimate_charge_rate(self) -> tuple[float, float]:
        """Calculate the charge rate to use for scheduling.

        Returns:
            tuple[float, float]: Selected charge rate and actual observed charge rate.
        """
        actual_charge_rate = abs(self.calc_battery_charge_wattage())
        print(f"best battery charge rate of {actual_charge_rate}")

        if actual_charge_rate > (CHARGING_RATE / 2):
            print(
                f"Setting charge rate for time calculations to {actual_charge_rate} instead of defined "
                f"{CHARGING_RATE} due to historic trends"
            )
            return actual_charge_rate, actual_charge_rate

        return CHARGING_RATE, actual_charge_rate

    def calculate_schedule(self) -> list[str]:
        """Compute and apply the optimal inverter charging schedule.

        Override this for different functionality, e.g., to use a different pricing API or to implement a different scheduling algorithm.

        Returns:
            list[str]: Formatted charging times applied to the inverter.
        """
        return []


class SunsynkInverterAgile(SunsynkInverter):
    """Explicit subclass for standard Agile tariff scheduling.

    This keeps the existing scheduling behaviour in a named subclass so code can
    choose between the default tariff strategy and the Octopus Go override in a
    clearer way without changing the underlying logic.
    """

    def calculate_schedule(self) -> list[str]:
        """Compute and apply the standard inverter charging schedule.

        Returns:
            list[str]: Formatted charging times applied to the inverter.
        """
        desired_charge_rate, _ = self.estimate_charge_rate()
        current_minutes, current_soc = self.calc_charge_time(desired_charge_rate, soc_cap=self.desired_soc)
        charge_minutes = current_minutes + 10
        print(f"Setting charging minutes to {charge_minutes} to reach desired battery charge % of {self.desired_soc}")

        costs_df = self.get_agile_data()
        print(costs_df)
        current_minutes, charge_times = self.get_times(costs_df, minutes=charge_minutes, current_soc=current_soc)

        dtn = pd.Timestamp(datetime.datetime.now()).tz_localize("Europe/London")
        costs_df_recent = costs_df.loc[costs_df["valid_from"] >= dtn]
        negative_windows = self.calc_negative_windows(costs_df_recent)
        negative_windows_df = negative_windows.apply(self.best_negative_window)
        print(negative_windows_df)

        if len(negative_windows_df) > 0:
            for item in negative_windows_df.items():
                if item[1][0] > current_minutes:
                    current_minutes = item[1][0]
                    start_time = item[1][1]
                    end_time = item[1][2]
                    charge_times = self.adjust_times_for_day_span([start_time, end_time])
                    print(f"Found large negative cost window, resetting times to {item[1][1]} and {item[1][2]}")

        formatted_charge_times = self.format_times(charge_times)
        print(f"charge times are {formatted_charge_times}")
        self.set_inverter_charge_times(formatted_charge_times, soc_cap=self.desired_soc)
        return formatted_charge_times


class SunsynkInverterOctopusGo(SunsynkInverter):
    """Subclass of SunsynkInverter that uses Octopus Go pricing data.

    This class overrides the `get_agile_data` method to fetch Octopus Go pricing data instead of Agile pricing data.
    """

    def get_next_day_sunlight(self) -> dict[str, datetime.datetime | float]:
        """Retrieve tomorrow's sunlight data for Cambridge, UK.

        Returns:
            dict: Sunrise, sunset, daylight hours, and forecast sunshine hours.

        Raises:
            requests.HTTPError: If the weather service returns an HTTP error.
        """
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)

        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": 52.2053,
                "longitude": 0.1218,
                "daily": "sunrise,sunset,sunshine_duration",
                "start_date": tomorrow.isoformat(),
                "end_date": tomorrow.isoformat(),
                "timezone": "Europe/London",
            },
            timeout=30,
        )
        response.raise_for_status()

        daily = response.json()["daily"]
        sunrise = datetime.datetime.fromisoformat(daily["sunrise"][0])
        sunset = datetime.datetime.fromisoformat(daily["sunset"][0])

        daylight_hours = (sunset - sunrise).total_seconds() / 3600
        sunshine_hours = daily["sunshine_duration"][0] / 3600

        return {
            "date": tomorrow,
            "sunrise": sunrise,
            "sunset": sunset,
            "daylight_hours": daylight_hours,
            "sunshine_hours": sunshine_hours,
        }

    def get_agile_data(self) -> pd.DataFrame:
        """Fetch the Octopus Go pricing data.

        Returns:
            pd.DataFrame: Octopus Go pricing dataset with timezone-normalised timestamps.
        """
        data = {}
        try:
            response = requests.get(AGILE_OUTGOING_URL, timeout=30)
            data = response.json()
        except Exception:
            print("requests failed, trying urllib urlopen instead")
            with urllib.request.urlopen(AGILE_OUTGOING_URL, timeout=30) as response:
                data = json.loads(response.read())

        df = pd.DataFrame.from_dict(data["results"])
        df["valid_from"] = pd.to_datetime(df["valid_from"]).apply(lambda value: value.tz_convert("Europe/London"))
        df["valid_to"] = pd.to_datetime(df["valid_to"]).apply(lambda value: value.tz_convert("Europe/London"))
        return df

    def calculate_schedule(self) -> list[str]:
            """Compute and apply the optimal inverter charging schedule using Octopus Go pricing data.

            For now, simply modifies the soc_cap/desired_soc based on the following logic:
            - If min day export price > night charging cost, then set desired_soc to 100% 
            - If min day export price < night charging cost, then set desired_soc to % based on estimated hours of sunlight
                in winter months should be higher % and in summer months, lower %
            
            - need daylight hours to estimate how much solar will be generated, and then set the desired_soc accordingly.

            Returns:
                list[str]: Formatted charging times applied to the inverter.
            """

            sunlight_data = self.get_next_day_sunlight()
            sunrise_time_rounded = round_to_nearest_half_hour(sunlight_data["sunrise"])
            sunset_time_rounded = round_to_nearest_half_hour(sunlight_data["sunset"])

            sunrise_time_rounded_pd = pd.to_datetime(sunrise_time_rounded).tz_localize("Europe/London")
            sunset_time_rounded_pd = pd.to_datetime(sunset_time_rounded).tz_localize("Europe/London")

            print(f"Sunlight data for {sunlight_data['date']}: sunrise at {sunlight_data['sunrise']}, sunset at {sunlight_data['sunset']}, daylight hours: {sunlight_data['daylight_hours']:.2f}, sunshine hours: {sunlight_data['sunshine_hours']:.2f}")
            print(f"Estimated sunrise rounded time: {sunrise_time_rounded}")

            df = self.get_agile_data()
            

            #median_price = df["value_inc_vat"].median()
            dt_now = pd.to_datetime("today").tz_localize("Europe/London")
            dt_now_p24 = dt_now + datetime.timedelta(days=1)
            date_mask = (df["valid_from"] >= sunrise_time_rounded_pd) & (df["valid_from"] < sunset_time_rounded_pd)
    
            filtered_df = df.loc[date_mask].sort_values("valid_from", ascending=True).set_index("valid_from")
            median_price = filtered_df["value_inc_vat"].median()

            if median_price > OCTOPUS_GO_NIGHT_CHARGING_COST * 1.2:
                print(f"Min day export price {median_price} is greater than night charging cost {OCTOPUS_GO_NIGHT_CHARGING_COST}, setting desired_soc to 100%")
                soc_cap = 100
            else:
                growth_rate = 1.0  # adjust this value to control the steepness of the curve.  Lower - less steep (more linear), higher - more steep (more exponential)
                # rate of 1.0 should suffice.  Increase if you have greater solar charging rate vs battery capacity
                # 1.0 was used for max solar generation of 2.0kW and battery capacity of 15.12kWh.  2.0 would work for 4.0kW solar generation and 15.12kWh battery capacity, etc.
                solar_quotient = sunlight_data["sunshine_hours"] / 24.0  # proportion of sunshine hours in day
                sigmoid = 2/(1+exp(solar_quotient * growth_rate))  # modified logistic function to map solar_quotient to a value between 0 and 1
                soc_cap = min(100, max(50, int(sigmoid * 100)))
                print(f"Min day export price {median_price} is worse than night charging cost {OCTOPUS_GO_NIGHT_CHARGING_COST}, setting desired_soc to {soc_cap}% based on estimated solar generation")

            idx = 1
            self.inverter_data[f"cap{idx}"] = soc_cap
            self.inverter_data[f"time{idx}on"] = True
            self.inverter_data["sellTime1"] = "00:30"
            self.inverter_data["sellTime2"] = "05:20"
            

            print(f"setting charge %")
            response = requests.post(self.set_url, headers=self._auth_headers(), json=self.inverter_data)
            print(response)


def main(
    user_email: Annotated[str, typer.Option("-u", help="user email address")],
    user_password: Annotated[str, typer.Option("-p", help="user password")],
    inverter_code: Annotated[str, typer.Option("-i", help="ID for Inverter")],
    bearer_token_path: Annotated[str, typer.Option("-t", help="path to token file")] = None,
    octopus_go: Annotated[bool, typer.Option("-g", help="Use Octopus Go pricing data")] = False,
):
    """Run the end-to-end inverter schedule calculation and update.

    Args:
        user_email (str): Sunsynk account email.
        user_password (str): Sunsynk account password.
        inverter_code (str): Inverter serial number.
        bearer_token_path (str | None): Optional path to a cached bearer token.
        octopus_go (bool): Whether to use Octopus Go pricing data.
    """

    if octopus_go:
        inverter = SunsynkInverterOctopusGo(inverter_id=inverter_code)
    else:
        inverter = SunsynkInverterAgile(inverter_id=inverter_code)

    inverter.resolve_bearer_token(user_email, user_password, bearer_token_path)
    inverter.calculate_schedule()


if __name__ == "__main__":
    typer.run(main)
