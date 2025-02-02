# Main Script for ZapTec API
# import os
# import requests
# from datetime import datetime, timedelta
# from zoneinfo import ZoneInfo
# import storage
import app
import logging
import os
from datetime import datetime


def main():
    logging.basicConfig(filename="zaptecschedule.log", encoding="utf-8",level=logging.DEBUG)
    app.writelog("Starting Zaptec Scheduler", True)

    app.read_api()

    reportday=os.getenv('reportday')
    app.writelog(f"Check if report day {reportday}", True)
    
    if int(datetime.now().strftime("%d")) == int(reportday):
        app.writelog("Generate report", True)
        if app.generate_smtp_report() == 0:
            app.writelog("SMTP Report not generated", True)

    else:
        app.writelog("Not report day", True)
    

    app.writelog("End Zaptec Scheduler", True)


if __name__ == "__main__":
    main()

