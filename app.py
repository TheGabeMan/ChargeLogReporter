# Imports
import sharedcomps
import logging
from flask import Flask, render_template, request, redirect, send_file
from datetime import datetime
# from zoneinfo import ZoneInfo


# Create the Flask app
def create_app():
    app = Flask(__name__,template_folder="./templates")
    logging.basicConfig(filename="app.log", encoding="utf-8",level=logging.DEBUG)
    sharedcomps.writelog("Starting Zaptec Report application from App()", IsDebug)
    return app


IsDebug = True
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
               app.logger.info(f"Report result: {report}")
               if not report:
                    return render_template("reports.html", error="No data available for the selected period.")
               return render_template("reports.html", report=report, period=period)
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

if __name__ == "__main__":
    # logging.basicConfig(filename="app.log", encoding="utf-8",level=logging.DEBUG)
    IsDebug = True
    sharedcomps.writelog("Starting Zaptec Report application from Main", IsDebug)
    index()
