# Imports
import sqlite3
import logging
from flask import Flask, render_template, request, redirect
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os
import requests
import pandas as pd
import json

app = Flask(__name__,template_folder="./templates")
IsDebug = True

# Configure logging
logging.basicConfig(filename="zaptecreport.log", encoding="utf-8",level=logging.DEBUG)

def writelog(log, IsDebug=False):
    log = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {log}"
    if IsDebug:
        print(log)
    logging.info(log)

writelog("Starting Zaptec Report application", IsDebug)

@app.template_filter('timestamp_to_date')
def timestamp_to_date(timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%d-%m-%Y %H:%M')


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/reports", methods=["GET","POST"])
def reports():
     get_portal_data()
     if request.method == "POST":
          period = request.form.get('month-year')
          if not period:
               # Handle the case where 'month-year' is not provided
               return render_template("reports.html", error="Please provide a period.")
          else:
               report = get_report(period=period)
               app.logger.info(f"Report result: {report}")
               if not report:
                    return render_template("reports.html", error="No data available for the selected period.")
               return render_template("reports.html", report=report)
     else:
          return render_template("reports.html")
     
@app.route("/generate_excel", methods=["POST"])
def generate_excel():
    report = request.form.get('report')
    month_year = request.form.get('month-year')

    if not report:
        return render_template("generate_excel.html", error="No report data available to generate Excel.")

    # Convert the report data to a DataFrame
    report_data = json.loads(report)
    if isinstance(report_data, dict):
        report_data = [report_data]
    df = pd.DataFrame(report_data)

    # Generate the Excel file
    excel_filename = f"report_{month_year}.xlsx"
    excel_filepath = os.path.join("static", excel_filename)
    df.to_excel(excel_filepath, index=False)

    # Provide the link to download the Excel file
    return render_template("generate_excel.html", excel_file=excel_filename)
    
    return render_template("generate_excel.html")

def get_portal_data():
    ''' Get data from API and store in the database '''

    username = os.getenv('username')
    password = os.getenv('password')
    chargerdid = os.getenv('chargerid')
    installationid = os.getenv('InstallationId')
    apiurl = 'https://api.zaptec.com'
    access_token = get_accesstoken(username, password, apiurl)
    if not access_token:
        return
    
    charge_history = get_charge_history_installation(access_token=access_token, apiurl=apiurl, installationid=installationid, GroupBy=0)

     #### API data
     # UserUserName
     # Id (SessionId)
     # DeviceID
     # StartDateTime
     # EndDateTime
     # Energy
     # UserFullName
     # ChargerId
     # DeviceName
     # UserEmail
     # UserId

    ## Open DB connection to insert data
    conn, cursor = sql_connect()
    for key in charge_history['Data']:
        writelog(f"From API retrieved {key['Id']} - {key['UserUserName']}", IsDebug)
        KeyIsUnique = False
        KeyIsUnique = check_unique_key(key,cursor)
        if KeyIsUnique:
            writelog(f"Write record {key['Id']}{key['UserUserName']} to database.", IsDebug)
            Result = sql_insert(key,cursor,conn)
            if not Result:
                writelog(f"Error writing record {key['Id']}{key['UserUserName']} to the database.", IsDebug)
            else:
                writelog(f"Record {key['Id']}{key['UserUserName']} successfully written to the database.", IsDebug)  
        else:
            writelog(f"Record {key['Id']}{key['UserUserName']} already exists in the database.", IsDebug)
    conn.close()

def get_report(period):
     # Connect to the SQLite database
    conn, cursor = sql_connect()

    # Convert the period to the format "YYYY-MM"
    period_date = datetime.strptime(period, "%Y-%m")
    start_timestamp = int(period_date.timestamp())
    end_timestamp = int((period_date.replace(day=28) + timedelta(days=4)).replace(day=1).timestamp())
    start_date_str = datetime.fromtimestamp(start_timestamp).strftime('%Y-%m-%d %H:%M:%S')
    end_date_str = datetime.fromtimestamp(end_timestamp).strftime('%Y-%m-%d %H:%M:%S')
    writelog(f"Generate report for Start: {start_date_str} - End: {end_date_str}", IsDebug)

    # Query to fetch the report data for the given period    
    query = """
    SELECT * FROM sessions
    WHERE startdatetime >= ? AND startdatetime < ?
    """
    cursor.execute(query, (start_timestamp, end_timestamp))

    # Fetch all rows and convert to dictionary
    rows = cursor.fetchall()
    report_data = [dict((cursor.description[i][0], value) for i, value in enumerate(row)) for row in rows]

    # Close the connection
    conn.close()

    return report_data

def get_accesstoken(username, password, apiurl):
    """
    Authenticate and obtain access token
    """

    auth_url = f"{apiurl}/oauth/token"
    payload = {
        "grant_type": "password",
        "username": username,
        "password": password
        # "client_id": "ZaptecPortal"
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        response = requests.post(auth_url, data=payload, headers=headers)
        response.raise_for_status()

        auth_data = response.json()
        access_token = auth_data.get('access_token')
        writelog(f"Access token: OK", IsDebug)
        return access_token
    except requests.exceptions.RequestException as e:
        writelog(f"Authentication failed: {e}", IsDebug)
        return False

def get_charge_history_installation(access_token, apiurl, installationid, GroupBy=0, DetailLevel=0, max_entries=500):
    """
    Retrieve charge history from Zaptec ZapCloud
    :param start_date: Start date for charge history (default: 30 days ago)
    :param end_date: End date for charge history (default: today)
    :param max_entries: Maximum number of entries to retrieve
    :param GroupBy 0 = 
    :return: List of charge history entries
    """

    # Default to last 30 days if no dates specified
    # We go back 3 months to get a good amount of data
    start_date, end_date = get_report_dates()

    history_url = f"{apiurl}/api/chargehistory"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    params = {
        "StartDate": start_date.isoformat(),
        "EndDate": end_date.isoformat(),
        "MaxEntires": max_entries,
        "InstallationId": installationid,
        "GroupBy": GroupBy,
        "DetailLevel": DetailLevel
    }

    writelog(f"Retrieving charge history from {start_date} to {end_date}", IsDebug)
    try:
        response = requests.get(history_url, headers=headers, params=params)
        response.raise_for_status()
        charge_history = response.json()
        writelog(f"Charge history retrieved succesful", IsDebug)
        return charge_history
    except requests.exceptions.RequestException as e:
        writelog(f"Failed to retrieve charge history: {e}", IsDebug)
        return []

def get_report_dates():
    # Get current date in UTC
    current_date = datetime.now(ZoneInfo("UTC"))
    start_date = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month = start_date.month -3
    year = start_date.year

    if month <= 0:
         month += 12
         year -= 1
    start_date = start_date.replace(year=year, month=month)

    if current_date.month == 12:
        end_date = current_date.replace(year=current_date.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_date = current_date.replace(month=current_date.month + 1, day=1) - timedelta(days=1)
    end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
    return start_date, end_date

def sql_connect():
    # Connect to a database (creates one if it doesn't exist)
    conn = sqlite3.connect('chargehistory.db')
    if conn is None:
        writelog("Failed to connect to the database.", IsDebug)
        raise sqlite3.Error("Failed to connect to the database.")
    cursor = conn.cursor()

    ## Check if the table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
    if cursor.fetchone() is None:
        writelog("Table sessions does not exist, try create it.", IsDebug)
        sql_createtable(conn=conn, cursor=cursor)
    return conn, cursor

def check_unique_key(key,cursor):
    # Check if the Id is unique
    cursor.execute('SELECT COUNT(1) FROM sessions WHERE "Id" = ?', (key['Id'],))
    if cursor.fetchone()[0] > 0:
        writelog(f"Id {key['Id']} already exists in the database.")
        return False
    return True

def sql_insert(key, cursor, conn):
    # Create Tabel if not exists
    if not sql_createtable(conn=conn, cursor=cursor):
        writelog("Error creating table", IsDebug)
        return False
    # Single insertion
    try:
        # StartDate, EndDate TEXT as ISO8601 strings (“YYYY-MM-DD HH:MM:SS.SSS”).
        # UnixStartDateTime = datetime.fromisoformat(key['StartDateTime']).timestamp()
        UnixStartDateTime = datetime.strptime(key['StartDateTime'], '%Y-%m-%dT%H:%M:%S.%f').timestamp()
        UnixEndDateTime = datetime.strptime(key['EndDateTime'], '%Y-%m-%dT%H:%M:%S.%f').timestamp()
    
        cursor.execute('''
        INSERT INTO sessions (
        "UserUserName",
        "Id",
        "DeviceID",
        "StartDateTime",
        "EndDateTime",
        "Energy",
        "UserFullName",
        "ChargerId",
        "DeviceName",
        "UserEmail",
        "UserId"        ) 
        VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? )''',
            (
                key['UserUserName'],
                key['Id'],
                key['DeviceId'],
                UnixStartDateTime,
                UnixEndDateTime,
                key['Energy'],
                key['UserFullName'],
                key['ChargerId'],
                key['DeviceName'],
                key['UserEmail'],
                key['UserId']
            ))
        conn.commit()
        return True
    except sqlite3.IntegrityError as err:
        conn.rollback()
        writelog(f"Integrity error occurred: {err}", IsDebug)
        return False
    except sqlite3.Error as err:
        conn.rollback()
        writelog(f"An error occurred: {err}", IsDebug)
        return False
    return True

def sql_createtable(conn, cursor):
    # Create a table
    # TEXT as ISO8601 strings (“YYYY-MM-DD HH:MM:SS.SSS”).
    try:
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            "UserUserName"	TEXT NOT NULL,
            "Id"	TEXT NOT NULL UNIQUE,
            "DeviceID"	TEXT,
            "StartDateTime"	INT NOT NULL,
            "EndDateTime"	INT NOT NULL,
            "Energy"	INTEGER NOT NULL,
            "UserFullName"	TEXT,
            "ChargerId"	TEXT,
            "DeviceName"	TEXT,
            "UserEmail"	TEXT,
            "UserId"	TEXT,
            PRIMARY KEY("StartDateTime")
        )''')
        conn.commit()
        return True
    except sqlite3.Error as err:
        conn.rollback()
        writelog(f"An error occurred creating table sessions: {err}", IsDebug)
        return False


if __name__ == "__main__":
    app.run(debug=True)