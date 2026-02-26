FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Gesamten Code und run.sh kopieren
COPY . .

# Skript ausführbar machen
RUN chmod a+x /app/run.sh

EXPOSE 6000

CMD [ "/app/run.sh" ]
