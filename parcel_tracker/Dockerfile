FROM python:3.10-alpine

# Installiere Build-Abhängigkeiten
RUN apk add --no-cache build-base python3-dev libffi-dev openssl-dev linux-headers

WORKDIR /app

# Kopiere requirements.txt und installiere Abhängigkeiten
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiere den gesamten Code in das Image
COPY . .

# Mache run.sh ausführbar
RUN chmod +x run.sh

CMD ["./run.sh"]
