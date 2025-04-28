# Main Script for ZapTec API
import sharedcomps
import logging
logger = logging.getLogger(__name__)
import os
from datetime import datetime

def main():
    logging.basicConfig(
        filename='schedule.log', 
        level=logging.INFO, 
        encoding="utf-8", 
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger.info("Welcome, Starting ZapTec Report application from Schedule.py")
    sharedcomps.read_api()
    reportday=os.getenv('reportday')
    logger.info(f"Check if report day {reportday}")
    
    if int(datetime.now().strftime("%d")) == int(reportday):
        logger.info("It is report day, generate report")
        smtp_report_attachment = sharedcomps.generate_smtp_report()
        if smtp_report_attachment == 0:
            logger.info("SMTP Report not generated")
        else:
            logger.info("SMTP Report generated")
            if sharedcomps.send_email(smtp_report_attachment, sharedcomps.get_previous_month()):
                logger.info("SMTP Report sent")
            else:
                logger.info("SMTP Report not sent")
    else:
        logger.info("Not report day")
    
    logger.info("End Zaptec Scheduler")


if __name__ == '__main__':
    main()
