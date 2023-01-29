# mpnet-embed
Automating embedding for daily uploaded content to cicero

1- Download [Model]( https://drive.google.com/file/d/1nv9OEJUiqP3ByeoBAKEttL56K8qRfgII/view?usp=share_link)

2- Copy to assets/milvus path for both 

Having two seperate docker files:
- cron.Dockerfile: Create an image for the python script that can be executed anytime.
- api.Dockerfile: Create an image for the fastapi server to call the script even if it fails.

Building the image: 
docker build -f x.Dockerfile -t y .
