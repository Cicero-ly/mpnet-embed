FROM python:3.9

WORKDIR /cron

COPY ./cron/requirements.txt .

RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY cron .

CMD ["python", "cron.py"]