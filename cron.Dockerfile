# 


FROM python:3.9

# 


WORKDIR /cron_embed

# 


COPY ./requirements.txt /cron_embed/requirements.txt

# 


RUN pip install --no-cache-dir --upgrade -r /cron_embed/requirements.txt

# 


COPY ./pre_cron_embed /cron_embed/app

# 
CMD [ "python", "./cicero_embeddings_automation.py"]
