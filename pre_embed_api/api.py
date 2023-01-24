from typing import Dict
from fastapi import Depends, FastAPI
from pydantic import BaseModel
import os
from fastapi.middleware.cors import CORSMiddleware
from typing import List
print(os.getcwd())
from .embed.cicero_embeddings_automation import Embed_Model, get_model


app = FastAPI()


origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#For now, it's just the daily cron, that can be triggered by a post trigger to start working
#Can add a limit for how many rows to change, using -1
class embedRequest(BaseModel):
    max_size: int

class embedResponse(BaseModel):
    count: int
    status: str

@app.post("/run_embed", response_model= embedResponse)
def embed(request: embedRequest, model: Embed_Model = Depends(get_model)):
    print(request)
    status, count = model.start_job(request.max_size)
    
    return embedResponse(
       status = status,
        count = count
    )
