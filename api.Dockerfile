# 


FROM python:3.9

# 


WORKDIR /embed_api

# 


COPY ./requirements.txt /embed_api/requirements.txt

# 


RUN pip install --no-cache-dir --upgrade -r /embed_api/requirements.txt

# 


COPY ./pre_embed_api /embed_api/app

# 

CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "80"]