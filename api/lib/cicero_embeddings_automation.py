from bs4 import BeautifulSoup
from pymongo import MongoClient
import os
import banana_dev as banana
import pprint
from datetime import datetime
import pinecone
from nanoid import generate as generate_nanoid
from langchain.text_splitter import RecursiveCharacterTextSplitter

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
        # This is a vanity API call to make sure that 
        # activity is logged in Pinecone no matter what happens
        # with the job. Otherwise, our index gets dropped after
        # 7 days of inactivity!
        self.pinecone_index.describe_index_stats()

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
        # Init text splitter to split an article into chunks
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        

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
                # thoughts_to_encode new format: ['news', 'id', {'0': par0, '1': par1, ...}]
                thoughts_to_encode.append(("news", thought["_id"], serialized_thought))
                
        if len(thoughts_to_encode) == 0:
            return None
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
        
        # We will be returning a list of the paragraphs, each with an_id
        chunks = self.text_splitter.split_text(thought)
        return {i: chunk for i,chunk in enumerate(chunks)}

    def execute_job(self, job):
        job_id = job["_id"]
        i = 0
        status = "Starting job..."

        if len(job["thoughts_queued"]) > 0:
            status = "Resuming job..."

        self.update_job(job_id, status)


        try:
            thoughts_to_encode_tuples = self.get_thoughts_for_embedding(job)
            if thoughts_to_encode_tuples is None:
                status = "Job complete, no thoughts to embed. (Check to make sure integrations is okay)"
                self.update_job(job_id, status)
                return

            thoughts_to_encode = {
                "pointers": [
                    {
                        "collection": x[0],
                        "_id": x[1],
                    }
                    for x in thoughts_to_encode_tuples
                ],
                # flattening all chunks
                "prompts": [y for x in thoughts_to_encode_tuples for y in x[2].values()],
            }

            status = "Thoughts queued."
            self.update_job(
                job_id,
                status,
                thoughts_queued=thoughts_to_encode["pointers"],
            )
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
                    embedding_ids = []
                    for j, chunk in enumerate(thoughts_to_encode_tuples[i]):
                        
                        embedding_key = generate_nanoid()
                        embedding_ids.append(embedding_key)

                        thought_collection = element[0]
                        thought_id = element[1] 
                        thought_vector = vectors[i+j]
                        # Pinecone should be updated for each chunk since it has it's own proper vector but is still linked to one single thought id
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
                    # Mongodb should be updated once we have all our embeddings for chunks in order.
                    self.news.update_one(
                        {"_id": thought_id},
                        {"$set": {"mpnet_embedding_pinecone_keys": embedding_ids}},
                    )
                    # i += 1

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
