import os
from typing import Dict, List

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

print(os.getcwd())
from cicero_embeddings_automation import Embed, get_model


app = FastAPI()


origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# For now, it's just the daily cron, that can be triggered by a post trigger to start working
# Can add a limit for how many rows to change, using -1
class embedRequest(BaseModel):
    max_size: int


class embedResponse(BaseModel):
    count: int
    status: str


@app.post("/run-embed", response_model=embedResponse)
def embed(request: embedRequest, model: Embed = Depends(get_model)):
    print(request)
    status, count = model.start_job(request.max_size)

    return embedResponse(status=status, count=count)
