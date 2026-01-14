# Use an official Python runtime as a parent image
FROM python:3.11-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Copy the application code into the container
COPY . /app

# Install any dependencies, including cron
RUN pip install --no-cache-dir -r requirements.txt && \
    apt-get update && \
    apt-get install -y cron

# Copy your cron job definition file into the container
COPY crontab /etc/cron.d/reporting-cron

# Make the cron file executable
RUN chmod 0644 /etc/cron.d/reporting-cron

# Load the cron table
RUN crontab /etc/cron.d/reporting-cron

# Make port 5000 available to the outside world
EXPOSE 5000

# Define the command to run the Flask application AND the cron service
CMD ["sh", "-c", "cron && python app.py"]

# Make docker image
# docker build -t chargelogreporter:v0.55 .

# Save docker image to a tar.gz file
# docker save chargelogreporter:v0.55 | gzip > chargelogreporter_v0.55.tar.gz

# On another machine, load the docker image from the tar.gz file
# docker load -i chargelogreporter_v0.55.tar.gz

