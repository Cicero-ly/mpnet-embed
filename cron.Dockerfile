FROM python:3.9

WORKDIR /cron

COPY cron .

RUN pip install --no-cache-dir --upgrade -r requirements.txt

CMD ["python", "cron.py"]