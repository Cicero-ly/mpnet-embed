from bs4 import BeautifulSoup
from pymongo import MongoClient
import os
import banana_dev as banana
import pprint
from datetime import datetime
import pinecone
from nanoid import generate as generate_nanoid

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

    def get_thoughts_for_embedding(self, max_size):
        thoughts_to_encode = []
        for thought in self.news.find(
            {
                "mpnet_embedding_pinecone_key": {"$exists": False},
                "valuable": True,
                "reviewed": True,
                "title": {"$ne": None},
                "content": {"$ne": None},
            },
            {},
            limit=max_size,
        ):
            serialized_thought = self.serialize_thought_for_model(thought)
            thoughts_to_encode.append(("news", thought["_id"], serialized_thought))
        return thoughts_to_encode

    def get_job_status(self, job_id):
        return self.embed_jobs.find_one({"_id": job_id}, {"_id": 1, "status": 1})

    def update_job_status(self, job_id, status, thoughts_encoded=[]):
        self.embed_jobs.update_one(
            {
                "_id": job_id,
            },
            {
                "$set": {
                    "status": status,
                    "last_updated_at": datetime.now(),
                    "thoughts_encoded": thoughts_encoded,
                }
            },
        )

    def serialize_thought_for_model(self, thought) -> str:
        soup = BeautifulSoup(thought["content"], "lxml")
        return thought["title"] + " " + soup.get_text(strip=True)

    def create_job(self, max_size: int):
        now = datetime.now()
        try:
            job = self.embed_jobs.insert_one(
                {
                    "max_size": max_size,
                    "status": "Created",
                    "created_at": now,
                    "last_updated_at": now,
                }
            )
            self.execute_job(job.inserted_id)
            return str("Job created successfully. Job ID: " + str(job.inserted_id))
        except Exception as e:
            print("Error creating job: ", e)
            return "Error creating job"

    def execute_job(self, job_id):
        i = 0

        status = "Started"
        self.update_job_status(job_id, status)

        job = self.embed_jobs.find_one({"_id": job_id})
        print(job)
        thoughts_to_encode = self.get_thoughts_for_embedding(job["max_size"])

        status = (
            "Thoughts serialized successfully. Number of thoughts to embed: "
            + str(len(thoughts_to_encode))
        )
        self.update_job_status(job_id, status)

        try:
            prompts = [x[2] for x in thoughts_to_encode]

            # Thoughts are aggregated and send to banana all at once
            # to minimize the time the workload is up (would rather it not be idle between API calls)
            # It's cheaper to run this job longer than run banana longer
            status = "Sending thoughts to banana for embedding..."
            self.update_job_status(job_id, status)

            banana_output = banana.run(
                self.banana["api_key"], self.banana["model_key"], {"prompt": prompts}
            )
            vectors = banana_output["modelOutputs"][0]["data"]

            assert len(thoughts_to_encode) == len(vectors)

            status = "All embeddings received from banana. Uploading to pinecone... / Updating mongodb..."
            self.update_job_status(job_id, status)

            for i, element in enumerate(thoughts_to_encode):
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
                            },
                        )
                    ]
                )

                self.news.update_one(
                    {"_id": thought_id},
                    {"$set": {"mpnet_embedding_pinecone_key": embedding_key}},
                )
                i += 1

        except Exception as e:
            print("Error: ", e)
            status = "Error: " + str(e)

        status = "Success"
        self.update_job_status(
            job_id,
            status,
            thoughts_encoded=[
                {"thought_collection": x[0], "thought_id": x[1]}
                for x in thoughts_to_encode
            ],
        )

        return


model = Embed()


def get_model():
    return model
