# Imports
import sharedcomps
import logging
logger = logging.getLogger(__name__)
from flask import Flask, render_template, request, send_file
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create the Flask app
def create_app():
    app = Flask(__name__, template_folder="./templates")
    logging.basicConfig(
        filename="./database/app.log", 
        level=logging.INFO, 
        encoding="utf-8",
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    # Add StreamHandler for Docker logs
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    logger.info("Welcome, Starting Zaptec Report application (Docker logs)")

    # For testing purposes:
    envtarif = os.getenv('tarif')
    logger.info(f"Env tarif: {envtarif}")

    logger.info("Again Welcome, Starting Zaptec Report application (Docker logs)")
    return app


app = create_app()

@app.template_filter('timestamp_to_date')
def timestamp_to_date(timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%d-%m-%Y %H:%M')

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/reports", methods=["GET","POST"])
def reports():
     if request.method == "POST":
          period = request.form.get('month-year')
          if not period:
               # Handle the case where 'month-year' is not provided
               return render_template("reports.html", error="Please provide a period.")
          else:
               report = sharedcomps.get_report(period=period)
               if not report:
                    logger.info(f"Report returned no data for period: {period}")
                    return render_template("reports.html", error="No data available for the selected period.")
               else:
                    logger.info(f"Report returned {len(report)} rows for period: {period}")
                    logger.info(f"First row of report: {report[0]['Id'][:14]}xxxx-xxxx - {report[0]['UserUserName']} - Date: {report[0]['StartDateTime']}")
                    logger.info(f"Last row of report: {report[-1]['Id'][:14]}xxxx-xxxx - {report[-1]['UserUserName']} - Date: {report[-1]['StartDateTime']}")
                    envtarif = os.getenv('tarif')
                    logger.info(f"Env tarif: {envtarif}")
                    tarif = float(envtarif) if envtarif else 0.0
                    logger.info(f"Tarif: {tarif}")
                    if tarif == 0.0:
                         logger.info("Tarif not set, using default value")
                    else:
                         logger.info(f"Tarif set to {tarif}")
                    return render_template("reports.html", report=report, period=period, tarif=tarif)
     else:
          return render_template("reports.html")
     
@app.route("/generate_excel", methods=["POST"])
def generate_excel():
    report = request.form.get('report')
    month_year = request.form.get('month-year')

    if not report:
        return render_template("generate_excel.html", error="No report data available to generate Excel.")

    return sharedcomps.generate_excel_from_reportform(report, month_year)

    # return redirect("/reports")

@app.route("/getdata", methods=["GET","POST"])
def getdata():
    if request.method == "POST":
        number_of_records = sharedcomps.read_api()
        return render_template("getdata.html", output=f"Report data has been updated. Total records found: {number_of_records}")
    else:
        return render_template("getdata.html")

@app.route("/totals", methods=["GET","POST"])
def totals():
    ''' Get monthly totals from the database over the past years '''
    if request.method == "GET":
        # monthly_totals = sharedcomps.get_monthly_totals()
        return render_template("totals.html")
    elif request.method == "POST":
        if not request.form.get('period_start') or not request.form.get('period_end'):
            return render_template("totals.html", error="Please provide both start and end periods.")
        
        period_start = request.form.get('period_start')
        period_end = request.form.get('period_end')
        logger.info(f"Get a report from Start period: {period_start}, End period: {period_end}")
        monthly_totals = sharedcomps.get_monthly_totals(period_start=period_start, period_end=period_end)
        return render_template("totals.html", monthly_totals=monthly_totals)

if __name__ == "__main__":
    logger.info("Starting Zaptec Report application from Main")
    app.run(host='0.0.0.0', port=5000, debug=True)
