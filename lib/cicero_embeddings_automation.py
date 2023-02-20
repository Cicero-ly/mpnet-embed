from bs4 import BeautifulSoup
from pymongo import MongoClient
import os
import banana_dev as banana
import pprint
from datetime import datetime
import pinecone
from nanoid import generate as generate_nanoid
from bson.objectid import ObjectId

pp = pprint.PrettyPrinter(indent=4)

# TODO: we'll want to future proof this for other thought collections
# besides just news


class Embed:
    def init_banana(self):
        self.banana = {
            "api_key": os.environ["BANANA_API_KEY"],
            "model_key": os.environ["BANANA_MODEL_KEY"],
        }

    def init_pinecone(self):
        pinecone.init(
            api_key=os.environ["PINECONE_API_KEY"],
            environment=os.environ["PINECONE_ENV"],
        )
        self.pinecone_index = pinecone.Index("thoughts")

    def init_mongodb(self):
        db_connection_string = os.environ["MONGO_CONNECTION_STRING"]
        client = MongoClient(db_connection_string)

        thoughts_db = client["cicero_thoughts"]
        logs_db = client["cicero_logs"]

        self.news = thoughts_db["news_test_embed"]
        self.embed_jobs = logs_db["embed_jobs"]

        print("MongoDB connection successful")

    def __init__(self):
        self.init_mongodb()
        self.init_pinecone()
        self.init_banana()

    def get_thoughts_for_embedding(self, job):
        # TODO: email if limit hit so we can scale
        thoughts_to_encode = []
        resuming_existing_job = len(job["thoughts_queued"]) > 0

        if resuming_existing_job:
            for thought_pointer in job["thoughts_queued"]:
                thought = self.news.find_one({"_id": thought_pointer["_id"]})
                serialized_thought = self.serialize_thought_for_model(thought)
                thoughts_to_encode.append(
                    (
                        thought_pointer["collection"],
                        thought_pointer["_id"],
                        serialized_thought,
                    )
                )
        else:
            limit = job.get("max_size", 5000)
            for thought in self.news.find(
                {
                    "mpnet_embedding_pinecone_key": {"$exists": False},
                    "valuable": True,
                    "reviewed": True,
                    "title": {"$ne": None},
                    "content": {"$ne": None},
                },
                {},
                limit=limit,
            ):
                serialized_thought = self.serialize_thought_for_model(thought)
                thoughts_to_encode.append(("news", thought["_id"], serialized_thought))
        return thoughts_to_encode

    def update_job(self, job_id, status, thoughts_queued=[], thoughts_encoded=[]):
        existing_job = self.embed_jobs.find_one({"_id": job_id})
        old_thoughts_queued = existing_job["thoughts_queued"]

        self.embed_jobs.update_one(
            {
                "_id": job_id,
            },
            {
                "$set": {
                    "status": status,
                    "last_updated_at": datetime.now(),
                    "thoughts_queued": thoughts_queued
                    if len(thoughts_queued) > 0
                    else old_thoughts_queued,
                    "thoughts_encoded": thoughts_encoded,
                },
            },
        )

    def serialize_thought_for_model(self, thought) -> str:
        soup = BeautifulSoup(thought["content"], "lxml")
        return thought["title"] + " " + soup.get_text(strip=True)

    def execute_job(self, job):
        job_id = job["_id"]
        i = 0
        status = "Starting job..."

        if len(job["thoughts_queued"]) > 0:
            status = "Resuming job..."
        
        self.update_job(job_id, status)

        thoughts_to_encode_tuples = self.get_thoughts_for_embedding(job)
        thoughts_to_encode = {
            "pointers": [
                {
                    "collection": x[0],
                    "_id": x[1],
                }
                for x in thoughts_to_encode_tuples
            ],
            "prompts": [x[2] for x in thoughts_to_encode_tuples],
        }

        status = "Thoughts queued."
        self.update_job(
            job_id,
            status,
            thoughts_queued=thoughts_to_encode["pointers"],
        )

        try:
            # Thoughts are aggregated and send to banana all at once
            # to minimize the time the workload is up (would rather it not be idle between API calls)
            # It's cheaper to run this job longer than run banana longer
            status = "Sending thoughts to banana for embedding..."
            self.update_job(job_id, status)

            # raise Exception("simulate banana failed")

            banana_output = banana.run(
                self.banana["api_key"],
                self.banana["model_key"],
                {"prompt": thoughts_to_encode["prompts"]},
            )
            vectors = banana_output["modelOutputs"][0]["data"]

            if len(vectors) != len(thoughts_to_encode_tuples):
                raise Exception(
                    "Number of thoughts sent to banana does not match number of thoughts returned"
                )

            status = "All embeddings received from banana. Uploading to pinecone... / Updating mongodb..."
            self.update_job(job_id, status)

            for i, element in enumerate(thoughts_to_encode_tuples):
                embedding_key = generate_nanoid()
                thought_collection = element[0]
                thought_id = element[1]
                thought_vector = vectors[i]

                self.pinecone_index.upsert(
                    [
                        (
                            embedding_key,
                            thought_vector,
                            {
                                "thought_collection": thought_collection,
                                "thought_id": str(thought_id),
                            },
                        )
                    ]
                )

                self.news.update_one(
                    {"_id": thought_id},
                    {"$set": {"mpnet_embedding_pinecone_key": embedding_key}},
                )
                i += 1

            status = "Success"
            self.update_job(
                job_id,
                status,
                thoughts_encoded=[
                    {"collection": x[0], "_id": x[1]} for x in thoughts_to_encode_tuples
                ],
            )
        except Exception as e:
            print("Error: ", e)
            status = "Error: " + str(e)
            self.update_job(job_id, status)

        print("Job complete.")
        return
