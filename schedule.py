# Main Script for ZapTec API
# import os
# import requests
# from datetime import datetime, timedelta
# from zoneinfo import ZoneInfo
# import storage
import app
import sharedcomps
import logging
import os
from datetime import datetime


def main():
#    logging.basicConfig(filename="zaptecschedule.log", encoding="utf-8",level=logging.DEBUG)
#    app.writelog("Starting Zaptec Scheduler", True)

    sharedcomps.read_api()

    reportday=os.getenv('reportday')
    app.writelog(f"Check if report day {reportday}", True)
    
    if int(datetime.now().strftime("%d")) == int(reportday):
        app.writelog("It is report day, generate report", True)
        smtp_report_attachment = app.generate_smtp_report()
        if smtp_report_attachment == 0:
            app.writelog("SMTP Report not generated", True)
        else:
            app.writelog("SMTP Report generated", True)
            if app.send_email(smtp_report_attachment, app.get_previous_month()):
                app.writelog("SMTP Report sent", True)
            else:
                app.writelog("SMTP Report not sent", True)
    else:
        app.writelog("Not report day", True)
    
    app.writelog("End Zaptec Scheduler", True)


if __name__ == "__main__":
    logging.basicConfig(filename="zaptecschedule.log", encoding="utf-8",level=logging.DEBUG)
    app.writelog("Starting Zaptec Scheduler", True)
    main()

