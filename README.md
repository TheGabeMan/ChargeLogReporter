![GitHub all releases](https://img.shields.io/github/downloads/thegabeman/ZapTecReporting/total?logo=Github&style=plastic)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/thegabeman/ZapTecReporting?style=plastic)
![GitHub](https://img.shields.io/github/license/thegabeman/ZapTecReporting?style=plastic)
![GitHub issues](https://img.shields.io/github/issues/thegabeman/ZapTecReporting?style=plastic)

Application to read your ZapTec Go charging sessions through API and create a report or have the report mail monthly.

# Installation
Create an environment file (.env) in the directory from which you start the docker container.
See env-example on how to format the .env file. The docker compose will mount this directory into the container and write the database (SQLite) and logfiles at this location.

- username & password are the email address and password you use to login to https://portal.zaptec.com/
- Your installation ID can be found through the portal website -> Installations -> Click the installation -> Click Settings tab. Here you'll see and option "Copy installation ID". Click it to get an id that looks like "12345678-1234-1234-1234-123456789123"
- Your charger ID can be found throught the portal website -> Chargers -> Click the charger.  Here you'll see and option "Copy charger ID". Click it to get an id that looks like "12345678-1234-1234-1234-123456789123"


For the report settings:
- tarif is the tarif at which you want the report created when exported to excel. For example 0.32 for 32 euro cent per KWh.
- reportday is the day of the month at which there is an automatic report generated for the previous month and then send by email.

Email & SMTP settings:
- These are pretty self explanatory

After start you should be able to find a basic webpage at port 5000. This is where the flask server is running.

# Database
The database is auto generated when not present and will try to read the last 365 days of data from the ZapTec API which is the max number of days ZapTec offers data. The database is written on the mounted volume and you can easily make a backup of it in this way. By running the schedule.py every day, the daily sessions will be read from the API and stored in the database. Be aware that a session is from start to disconnect of the car. When you pause charging in between, it will still be one session.

# Guest Account
When you create an account in the ZapTec portal with the exact name "Guest Account", sessions by this user will show when you ask for a monthly report, but will be filtered out in the Excel export.


# Todo:
- Create docker container
- Write docker compose
- Saved Excel sheet should not open full screen
- PDF export option
