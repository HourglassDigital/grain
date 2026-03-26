FROM python:3.12-slim

WORKDIR /app

COPY realtime/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY realtime/ ./realtime/

CMD ["python", "-m", "realtime.app"]
