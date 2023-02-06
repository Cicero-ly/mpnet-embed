from bs4 import BeautifulSoup
from pymongo import MongoClient
import os
import banana_dev as banana
import pprint

pp = pprint.PrettyPrinter(indent=4)


class Embed:
    def __init__(self):
        db_connection_string = os.environ["MONGO_CONNECTION_STRING"]
        client = MongoClient(db_connection_string)

        print("MongoDB connection successful")
        db = client["cicero_thoughts"]

        self.news = db["news"]

        self.banana = {
            "api_key": os.environ["BANANA_API_KEY"],
            "model_key": os.environ["BANANA_MODEL_KEY"],
        }

    def serialize_thought_for_model(self, thought):
        soup = BeautifulSoup(thought["content"], "lxml")
        return thought["title"] + " " + soup.get_text(strip=True)

    def start_job(self, max_size):
        status = "Success"
        thoughts_to_encode = []

        for thought in self.news.find(
            {
                "valuable": True,
                "reviewed": True,
                "mpnet_embeddings": {"$exists": False},
                "title": {"$ne": None},
                "content": {"$ne": None},
            },
            {},
            limit=max_size,
        ):
            # print("thought: ", thought)
            serialized_thought = self.serialize_thought_for_model(thought)
            thoughts_to_encode.append(serialized_thought)

        pp.pprint(thoughts_to_encode)

        # banana_output = banana.run(
        #     self.banana["api_key"],
        #     self.banana["model_key"],
        #     {"prompt": text_data.tolist()},
        # )
        # TODO: make sure the following line is correct
        # sentence_embeddings = banana_output["modelOutputs"][0]["data"]

        # TODO: We're going to use Pinecone instead to store vectors.
        return status, len(thoughts_to_encode)


model = Embed()


def get_model():
    return model
