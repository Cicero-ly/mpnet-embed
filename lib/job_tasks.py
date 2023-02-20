import json
from bson.objectid import ObjectId
import asyncio
from datetime import datetime
from pymongo import MongoClient
import os
from cicero_embeddings_automation import Embed
from functools import partial

db_connection_string = os.environ["MONGO_CONNECTION_STRING"]
client = MongoClient(db_connection_string)

logs_db = client["cicero_logs"]
embed_jobs = logs_db["embed_jobs"]

embed = Embed()


def validate_job(job_id):
    if not ObjectId.is_valid(job_id):
        raise TypeError("job_id is not a valid ObjectId")
    job_id = ObjectId(job_id)
    job = embed_jobs.find_one({"_id": job_id})
    if job is None:
        raise Exception("Could not find job with id: " + str(job_id))
    
    return job_id

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
        created_job = embed_jobs.find_one({"_id": job.inserted_id})
        asyncio.create_task(
          asyncio.to_thread(partial(embed.execute_job, created_job))
        ) 
        return {
            "message": "Job created successfully",
            "job_id": str(job.inserted_id),
        }
    except Exception as e:
        print("Error creating job: ", e)
        return "Error creating job"


async def resume_job(job_id):
    try:
        validate_job(job_id)
        job = embed_jobs.find_one({"_id": ObjectId(job_id)})

        if job["status"] == "Success" and len(job["thoughts_encoded"]) > 0:
            raise Exception(f"Job {job_id} has already been completed")

        asyncio.create_task(
          asyncio.to_thread(partial(embed.execute_job, job))
        )

        return {
            "message": "Job resumed",
            "job_id": str(job_id),
        }
    except Exception as e:
        print("Error resuming job: ", e)
        return {
            "error": "Error resuming job",
            "message": str(e),
        }


def get_job_status(job_id):
    try:
        validate_job(job_id)
        job = embed_jobs.find_one({"_id": ObjectId(job_id)})
        # Ugly hack for converting ObjectId to string, since FastAPI's json_encoder
        # can't handle serializing ObjectId
        json_response = json.loads(json.dumps(job, indent=4, default=str))
        return json_response
    except Exception as e:
        print("Error getting job status: ", e)
        return {
            "error": "Error getting job status",
            "message": str(e),
        }
