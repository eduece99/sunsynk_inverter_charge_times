# SunSynk inverter charge scheduling

This project contains a small Python utility for automatically scheduling a SunSynk inverter battery to charge at the cheapest or most favourable times based on electricity tariff data.

It connects to the SunSynk API, reads the inverter’s current battery state, estimates the charging rate, fetches Octopus tariff pricing, and then writes updated charge windows back to the inverter.

This is useful if you want to charge your battery during cheap off-peak periods or during very low-price windows on Octopus Agile / Octopus Go tariffs.

**Note** - This is not endorsed by SunSynk or Octopus.  *Use at your own risk*!

## What it does

The main script in [inverter_set.py](inverter_set.py) does the following:

- Authenticates to the SunSynk service using the account email and password
- Downloads a bearer token for future API requests
- Reads current inverter battery status such as current SoC and battery capacity
- Estimates how quickly the battery can charge from historical inverter data
- Fetches tariff prices from Octopus Energy
- Finds the cheapest charging window for the next day
- Optionally uses a special Octopus Go logic based on forecast sunlight and export prices
- Sends the chosen time windows back to the inverter as charge schedules

It is built around the `SunsynkInverter` class and the `SunsynkInverterOctopusGo` subclass.

## Main logic

### `SunsynkInverter`

This is the main class that handles:

- login and token generation
- building the inverter schedule payload
- fetching real-time inverter battery state
- calculating charge duration needed to reach a target SoC
- retrieving Agile data
- selecting cheapest periods
- writing the final charging windows back to the inverter

### `SunsynkInverterAgile`

This subclass overrides the main class, implementing the logic for setting optimal times for charging based on Octopus Agile Data.

### `SunsynkInverterOctopusGo`

This subclass overrides the price-fetching and scheduling logic for Octopus Go.

It looks at:

- the next day’s sunrise/sunset and sunshine forecast
- the day-time export price pattern
- the overnight charging rate and decides how much charge the battery should target

It then sets the inverter to charge during the most sensible Go window.

## Files in this project

- [inverter_set.py](inverter_set.py): main scheduling logic and CLI entry point
- [sunsynk_api_example.py](sunsynk_api_example.py): simple example showing how to request a token and fetch live generation data
- [example_usage.txt](example_usage.txt): example command lines
- [api-login.html](api-login.html), [api-login2.html](api-login2.html): simple HTML files related to auth or earlier testing

## Requirements

Install the Python dependencies before running the script:

```bash
pip install pandas requests typer pycryptodome typing_extensions
```

You will also need a valid SunSynk account and an inverter serial number.

## How to use it

The script is run as a command-line tool with Typer.

### Standard mode (Octopus Agile pricing)

```bash
python inverter_set.py -u your-email@example.com -p 'your-password' -i 1234567890
```

Arguments:

- `-u` or `--user-email`: your SunSynk account email
- `-p` or `--user-password`: your SunSynk password
- `-i` or `--inverter-code`: inverter serial number or ID
- `-t` or `--bearer-token-path`: optional path to a cached token file
- `-g` or `--octopus-go`: use Octopus Go logic instead of Agile logic

### With a saved bearer token

If you already have a token file saved, you can skip login credentials:

```bash
python inverter_set.py -t token.txt -i 1234567890
```

The code expects the token file to contain the bearer value, usually in the form:

```text
Bearer <your-token>
```

### Octopus Go mode

```bash
python inverter_set.py -u your-email@example.com -p 'your-password' -i 1234567890 -g
```

This uses the Octopus Go tariff and next-day daylight estimate to decide how much battery capacity to target.

## Example commands

The project includes example usage in [example_usage.txt](example_usage.txt):

```bash
python inverter_set.py -u eduece99@gmail.com -p 'Welcome123' -i 2407257268

# octopus go charging % optimisation based on next day's median price
python inverter_set.py -u eduece99@gmail.com -p 'Welcome123' -i 2407257268 -g
```

## How the schedule is chosen

The script uses tariffs and current battery state to decide a charging window.

For Agile mode:

- fetches the next day’s price bands
- looks at the cheapest rolling time window of the right duration
- if a strong negative-price period exists, it may override the plan
- writes an updated charge window to the inverter

For Go mode:

- looks at sunrise, sunset, and projected sunshine hours
- decides a charge target based on whether daytime export is likely to be better than cheaper night charging
- sets a charge goal and updates the inverter settings

## Important notes

- This code talks directly to the SunSynk and Octopus APIs; it is not an official integration library.
- Public APIs and endpoints can change over time, so some parts may need updating.
- The script makes real changes to your inverter settings. Use it carefully and test it with your own configuration.
- It can be run on a schedule via cron or a small automation process if you want it to update the battery schedule automatically.


## Typical workflow

1. Log in to SunSynk and get a bearer token
2. Read the inverter status and current battery charge
3. Fetch the latest tariff data
4. Choose the cheapest charge window
5. Push the new charge schedule to the inverter
6. Repeat as needed on a daily or regular schedule

## Safety and responsibility

This utility changes your inverter charging behaviour based on pricing and battery conditions. Before using it in a live setup, ensure:

- you understand the tariff rules in your region
- your battery and inverter manufacturer permits this kind of automation
- your system has safe charge limits and correct battery settings
- you have backup access if you need to revert to manual scheduling

## Summary

In short, this project is a home-energy automation helper that lets a SunSynk inverter charge its battery at the cheapest or most useful times by combining:

- SunSynk battery/inverter status
- Octopus Energy tariff data
- a lightweight decision algorithm
- automatic API updates to inverter charging windows

If you want to use this project, the essential entry point is [inverter_set.py](inverter_set.py), and the most important command is the CLI form shown above.

## References

Original credit to author AsTheSeaRises, project SunSynk_API.
https://github.com/AsTheSeaRises/SunSynk_API

Password salting help from:
https://github.com/restrive/sunsynk/blob/c9f9ec806d3e0bb7113461e89d9915865f646562/custom_components/sunsynk_sync/api_client.py
