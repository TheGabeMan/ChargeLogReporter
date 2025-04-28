# Dockerfile, Image, Container
FROM python:3.11-slim

ADD . /app.py .

RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 5000
CMD ["python", "app.py"]

# docker build -t zaptecreporting .
# docker run -d -p 5000:5000 --name zaptecreporting zaptecreporting