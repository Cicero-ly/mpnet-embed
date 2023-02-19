import json
from bson.objectid import ObjectId
import asyncio
from datetime import datetime
from pymongo import MongoClient
import os
from cicero_embeddings_automation import Embed

db_connection_string = os.environ["MONGO_CONNECTION_STRING"]
client = MongoClient(db_connection_string)

logs_db = client["cicero_logs"]
embed_jobs = logs_db["embed_jobs"]

embed = Embed()


async def create_job(max_size: int):
    now = datetime.now()
    try:
        job = embed_jobs.insert_one(
            {
                "max_size": max_size,
                "status": "Created",
                "created_at": now,
                "last_updated_at": now,
                "thoughts_queued": [],
            }
        )
        asyncio.ensure_future(embed.execute_job(job.inserted_id))
        return {
            "message": "Job created successfully",
            "job_id": str(job.inserted_id),
        }
    except Exception as e:
        print("Error creating job: ", e)
        return "Error creating job"


async def resume_job(job_id):
    try:
        asyncio.ensure_future(embed.execute_job(job_id))
        return {
            "message": "Job resumed",
            "job_id": str(job_id),
        }
    except Exception as e:
        print("Error resuming job: ", e)
        return "Error resuming job"


def get_job_status(job_id):
    job = embed_jobs.find_one({"_id": ObjectId(job_id)})
    # Ugly hack for converting ObjectId to string, since FastAPI's json_encoder
    # can't handle serializing ObjectId
    json_response = json.loads(json.dumps(job, indent=4, default=str))
    return json_response
