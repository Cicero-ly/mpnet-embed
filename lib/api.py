from typing import Union
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from cicero_embeddings_automation import Embed, get_embed


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
    job_id: Union[str, None]
    max_size: Union[int, None]


@app.post("/run-embed")
async def embed(request: embedRequest, embed: Embed = Depends(get_embed)):
    print(request)
    if request.job_id is not None:
        return await embed.resume_job(request.job_id)
    return await embed.create_job(request.max_size)


@app.get("/get-job-status")
def get_job_status(id: str, embed: Embed = Depends(get_embed)):
    if id is None or id == "":
        return {"error": "No job id provided"}
    return embed.get_job_status(id)
