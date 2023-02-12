from bs4 import BeautifulSoup
from pymongo import MongoClient
import os
import banana_dev as banana
import pprint
import sys
import pinecone
from nanoid import generate as generate_nanoid

pp = pprint.PrettyPrinter(indent=4)


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
        db = client["cicero_thoughts"]
        self.news = db["news_test_embed"]
        print("MongoDB connection successful")

    def __init__(self):
        self.init_mongodb()
        self.init_pinecone()
        self.init_banana()

    def serialize_thought_for_model(self, thought) -> str:
        soup = BeautifulSoup(thought["content"], "lxml")
        return thought["title"] + " " + soup.get_text(strip=True)

    def start_job(self, max_size):
        # TODO: immediately return 200 response to client and start job in background, since it will take a while
        # TODO: add job status to mongodb
        # Should be able to poll job status
        status = "Success"
        i = 0
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

        print(
            "Thoughts serialized successfully. Number of thoughts to embed: ",
            len(thoughts_to_encode),
        )

        try:
            prompts = [x[2] for x in thoughts_to_encode]

            # Thoughts are aggregated and send to banana all at once
            # to minimize the time the workload is up (would rather it not be idle between API calls)
            # It's cheaper to run this job longer than run banana longer
            print("Sending thoughts to banana for embedding...")
            banana_output = banana.run(
                self.banana["api_key"], self.banana["model_key"], {"prompt": prompts}
            )
            vectors = banana_output["modelOutputs"][0]["data"]

            print("sample of banana output: ")
            for vector in vectors:
                pp.pprint(vector[:3])

            assert len(thoughts_to_encode) == len(vectors)

            print("All embeddings received from banana. Uploading to pinecone...")

            for i, element in enumerate(thoughts_to_encode):
                embedding_key = generate_nanoid()
                # TODO: we'll want to future proof this for other thought collections
                # besides just news
                thought_collection = element[0]
                thought_id = element[1]
                thought_vector = vectors[i]

                print("Uploading embedding for thought ", thought_id, " to pinecone...")
                print("sample of thought_vector: ")
                pp.pprint(thought_vector[:3])
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

                print(
                    "Updating embedding key for thought ", thought_id, " in mongodb..."
                )
                self.news.update_one(
                    {"_id": thought_id},
                    {"$set": {"mpnet_embedding_pinecone_key": embedding_key}},
                )
                print("Done")
                i += 1

        except Exception as e:
            print("Error: ", e)
            status = "Error: " + str(e)

        print("Job completed with status: ", status, " and ", i, " thoughts embedded.")
        return status, i


model = Embed()


def get_model():
    return model
