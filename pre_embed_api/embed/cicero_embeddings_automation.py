from bs4 import BeautifulSoup
import pandas as pd
from bson import ObjectId
from pymongo import MongoClient
from sklearn.preprocessing import normalize
import os
import banana_dev as banana


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

    def start_job(self, max_size):
        status = "Success"

        # Target only data that has content and title available.
        df = pd.DataFrame(
            self.news.find(
                {
                    "valuable": True,
                    "reviewed": True,
                    "mpnet_embeddings": {"$exists": False},
                }
            )
        )
        df = df[~((df["content"].isna()) + (df["title"].isna()))].iloc[:max_size]

        text_data = df.apply(
            lambda x: x["title"] + " " + BeautifulSoup(x["content"]).get_text(), axis=1
        ).tolist()
        print(text_data[0])

        sentence_embeddings = banana.run(
            self.banana["api_key"], self.banana["model_key"], {"prompt": text_data}
        )
        sentence_embeddings = normalize(sentence_embeddings)

        fields = sentence_embeddings.tolist()
        df["mpnet_embeddings"] = fields
        try:
            for row in df.to_dict("records"):
                self.news.update_one(
                    {"_id": ObjectId(row["_id"])},
                    {"$set": {"mpnet_embeddings": row["mpnet_embeddings"]}},
                    upsert=False,
                )
        except Exception as e:
            print(e)
            status = e
        return status, len(df)


model = Embed()


def get_model():
    return model
