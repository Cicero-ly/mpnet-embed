# 


FROM python:3.9

# 


WORKDIR /api

# 


COPY ./requirements.txt .

# 


RUN pip install --no-cache-dir --upgrade -r requirements.txt

# 


COPY ./lib .

# 

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "80"]