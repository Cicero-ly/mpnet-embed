# mpnet-embed
Automating embedding for daily uploaded content to cicero

Having two seperate docker files:
- cron.Dockerfile: Create an image for the python script that can be executed anytime.
- api.Dockerfile: Create an image for the fastapi server to call the script even if it fails.

Building the image: 
docker build -f x.Dockerfile -t y .
