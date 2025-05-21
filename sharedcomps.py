import logging
import app
import os
import requests
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import openpyxl
import json
import ast
import sys
from io import BytesIO
import smtplib
from email.message import EmailMessage
from flask import Flask, render_template, request, redirect, send_file

def read_api():
    ''' Get data from API and store in the database '''
    ''' Should be run every few hours'''

    username = os.getenv('username')
    password = os.getenv('password')
    chargerdid = os.getenv('chargerid')
    installationid = os.getenv('InstallationId')
    apiurl = 'https://api.zaptec.com'
    access_token = get_accesstoken(username, password, apiurl)
    if not access_token:
        return
    
    charge_history = get_charge_history_installation(access_token=access_token, apiurl=apiurl, installationid=installationid)

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
        app.logger.info(f"From API retrieved {key['Id'][:14]}xxxx-xxxx - {key['UserUserName']} - Date: {key['StartDateTime']}")
        KeyIsUnique = False
        KeyIsUnique = sql_check_unique_key(key,cursor)
        if KeyIsUnique:
            app.logger.info(f"Write {key['Id'][:14]}xxxx-xxxx - {key['UserUserName']} - Date: {key['StartDateTime']} to database.")
            Result = sql_insert(key,cursor,conn)
            if not Result:
                app.logger.info(f"Error writing record {key['Id'][-9:]}xxxx-xxxx - {key['UserUserName']} to the database.")
            else:
                app.logger.info(f"Record {key['Id'][:14]}xxxx-xxxx - {key['UserUserName']} successfully written to the database.")  
        else:
            app.logger.info(f"Record {key['Id'][:14]}xxxx-xxxx - {key['UserUserName']} already exists in the database.")
    conn.close()

def get_accesstoken(username, password, apiurl):
    """
    Authenticate and obtain access token
    """

    auth_url = f"{apiurl}/oauth/token"
    payload = {
        "grant_type": "password",
        "username": username,
        "password": password
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        response = requests.post(auth_url, data=payload, headers=headers)
        response.raise_for_status()

        auth_data = response.json()
        access_token = auth_data.get('access_token')
        app.logger.info(f"Access token: OK")
        return access_token
    except requests.exceptions.RequestException as e:
        app.logger.info(f"Authentication failed: {e}")
        return False

def get_charge_history_installation(access_token, apiurl, installationid):
    """
    Retrieve charge history from Zaptec ZapCloud
    https://api.zaptec.com/help/index.html#/ChargeHistory/ChargeHistory_GetAll_GET
    :param start_date: Start date for charge history (default: 30 days ago)
    :param end_date: End date for charge history (default: today)
    :Max page size is 100, Default page size is 50
    :Max days is 365
    :param GroupBy 0 = 
                0 = Charger
                1 = Day
                2 = User
    :param DetailLevels
                0 = Summary
                1 = EnergyDetails
    :return: List of charge history entries
    """
    GroupBy=0
    DetailLevel=0
    PageSize=100
    PageIndex = 0


    # We go back 12 months to get a good amount of data
    start_date, end_date = get_report_dates()


    history_url = f"{apiurl}/api/chargehistory"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }


    while True:
        params = {
            "StartDate": start_date.isoformat(),
            "EndDate": end_date.isoformat(),
            "InstallationId": installationid,
            "GroupBy": GroupBy,
            "DetailLevel": DetailLevel,
            "PageSize": PageSize,
            "PageIndex": PageIndex
        }

        app.logger.info(f"Retrieving charge history from {start_date} to {end_date} - PageIndex {PageIndex}")
        try:
            response = requests.get(history_url, headers=headers, params=params)
            response.raise_for_status()
            charge_history = response.json()
            app.logger.info(f"Charge history retrieved succesful for page {PageIndex}")
            if len(charge_history['Data']) < PageSize:
                return charge_history
            else:
                PageIndex += 1
                app.logger.info(f"PageIndex {PageIndex} - continue to get more data")
        except requests.exceptions.RequestException as e:
            app.logger.info(f"Failed to retrieve charge history: {e}")
            return []

def get_report_dates():
    # Get current date in UTC
    current_date = datetime.now(ZoneInfo("UTC"))
    start_date = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month = start_date.month -12
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

def get_report(period):
     # Connect to the SQLite database
    conn, cursor = sql_connect()

    # Convert the period to the format "YYYY-MM"
    period_date = datetime.strptime(period, "%Y-%m")
    start_timestamp = int(period_date.timestamp())
    end_timestamp = int((period_date.replace(day=28) + timedelta(days=4)).replace(day=1).timestamp())
    start_date_str = datetime.fromtimestamp(start_timestamp).strftime('%Y-%m-%d %H:%M:%S')
    end_date_str = datetime.fromtimestamp(end_timestamp).strftime('%Y-%m-%d %H:%M:%S')
    app.logger.info(f"Generate report for Start: {start_date_str} - End: {end_date_str}")

    # Query to fetch the report data for the given period INCLUDING Guest Account
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

def generate_smtp_report():
    # Generate the report to send via email
    # Get the report data for the previous month
    previous_month = get_previous_month()
    smtp_report = get_report(period=previous_month)
    if not smtp_report:
        app.logger.info(f"No data available for the smtp report for period {(datetime.now() - timedelta(days=1)).strftime('%Y-%m')}")
        return 
    else:
        return generate_excel_for_smtp_report(smtp_report)
    
def generate_excel_for_smtp_report(report):
    # Convert the report from JSON
    # json_report = json.loads(report)
    filtered_report = []
    for entry in report:
        filtered_entry = {
            "From": datetime.fromtimestamp(entry["StartDateTime"]).strftime('%d-%m-%Y %H:%M'),
            "To": datetime.fromtimestamp(entry["EndDateTime"]).strftime('%d-%m-%Y %H:%M'),
            "Energy (KWh)": entry["Energy"]
        }
        filtered_report.append(filtered_entry)

    # Calculate the sum of the Energy column
    total_energy = sum(entry["Energy"] for entry in report)
    app.logger.info(f"Total energy for the report: {total_energy}")
    filtered_report.append({"To": "Total Energy (KWh)", "Energy (KWh)": total_energy})  

    # Read price per KWh from environment variable
    tarif = os.getenv('tarif')
    filtered_report.append({"To": "Price per KWh", "Energy (KWh)": float(tarif)})

    total_cost = total_energy * float(tarif)
    filtered_report.append({"To": "Total cost:", "Energy (KWh)": round(total_cost, 2)})
    app.logger.info(f"Total cost for the report: {total_cost}")

    # Convert the filtered report to a DataFrame
    df = pd.DataFrame(filtered_report)

    # Generate the Excel file in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)

    return output

def generate_excel_from_reportform(report, month_year):
    # Convert the report data to a DataFrame
    # First convert single quotes to double quotes
    report_data = report.replace("'", '"')

    # Convert the string to a dictionary
    jsreport = json.loads(report_data)

    # Filter columns in report
    filtered_report = []
    for entry in jsreport:
        if entry["UserFullName"] != "Guest Account":
            filtered_entry = {
                "From": datetime.fromtimestamp(entry["StartDateTime"]).strftime('%d-%m-%Y %H:%M'),
                "To": datetime.fromtimestamp(entry["EndDateTime"]).strftime('%d-%m-%Y %H:%M'),
                "Energy (KWh)": entry["Energy"]
            }
            filtered_report.append(filtered_entry)

    # Calculate the sum of the Energy column
    total_energy = sum(entry["Energy"] for entry in jsreport if entry["UserFullName"] != "Guest Account")
    app.logger.info(f"Total energy for the report: {total_energy}")
    filtered_report.append({"To": "Total Energy (KWh)", "Energy (KWh)": total_energy})

    # Read price per KWh from environment variable
    tarif = os.getenv('tarif')
    filtered_report.append({"To": "Price per KWh", "Energy (KWh)": float(tarif)})

    total_cost = total_energy * float(tarif)
    filtered_report.append({"To": "Total cost:", "Energy (KWh)": round(total_cost, 2)})
    app.logger.info(f"Total cost for the report: {total_cost}")

    jsreport = filtered_report
    if isinstance(jsreport, dict):
        jsreport = [jsreport]
    df = pd.DataFrame(jsreport)

    # Generate the Excel file in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)

    # Send the file to the user for download
    return send_file(output, as_attachment=True, download_name=f"report_{month_year}.xlsx", mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


def get_previous_month():
    # Get the previous month
    today = datetime.now()
    first = today.replace(day=1)
    last_month = first - timedelta(days=1)
    return last_month.strftime("%Y-%m")

def sql_connect():
    # Connect to a database (creates one if it doesn't exist)
    while True:
        conn = sqlite3.connect('./database/chargehistory.db')
        if conn is None:
            app.logger.info("Failed to connect to the database in sql_connect().")
            raise sqlite3.Error("Failed to connect to the database in sql_connect().")
            conn = None
            cursor = None
            return conn, cursor
        cursor = conn.cursor()

        ## Check if the table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
        if cursor.fetchone() is None:
            app.logger.info("Table sessions does not exist, try create it.")
            sql_createtable(conn=conn, cursor=cursor)
            ## As the table is created, we need to get data from the api
            read_api()
        else:
            return conn, cursor

def sql_insert(key, cursor, conn):
    # Create Tabel if not exists
    if not sql_createtable(conn=conn, cursor=cursor):
        app.logger.info("Error creating table")
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
        app.logger.info(f"Integrity error occurred: {err}")
        return False
    except sqlite3.Error as err:
        conn.rollback()
        app.logger.info(f"An error occurred: {err}")
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
        app.logger.info(f"An error occurred creating table sessions: {err}")
        return False

def sql_check_unique_key(key,cursor):
    # Check if the Id is unique
    cursor.execute('SELECT COUNT(1) FROM sessions WHERE "Id" = ?', (key['Id'],))
    if cursor.fetchone()[0] > 0:
        # Record already exists return False
        return False
    return True

def send_email(smtp_report_attachment, period):
    # Send the email with the SMTP report attachment
    filename = f"{period} {os.getenv('smtp_subject')}.xlsx"
    msg = EmailMessage()
    msg['Subject'] = period + " - " + os.getenv('smtp_subject')
    msg['From'] = os.getenv('smtp_from')
    msg['To'] = os.getenv('smtp_to')
    msg.set_content(os.getenv('smtp_body'))
    msg.add_attachment(smtp_report_attachment.getvalue(), maintype='application', subtype='octet-stream', filename=filename)

    try:
        # Send email
        with smtplib.SMTP_SSL(os.getenv('SMTP_SERVER'), os.getenv('SMTP_PORT')) as server:
            server.login(os.getenv('EMAIL_SENDER'), os.getenv('EMAIL_PASSWORD'))
            server.send_message(msg)
        app.logger.info("Email sent successfully")
        return True
    except smtplib.SMTPException as e:
        app.logger.info(f"Failed to send email: {e}")
        return False


