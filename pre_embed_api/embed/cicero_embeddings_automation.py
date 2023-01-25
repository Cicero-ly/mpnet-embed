from bs4 import BeautifulSoup
import pandas as pd
from bson import  ObjectId
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import normalize


class Embed_Model():
  def __init__(self):
        #local_path
        path = "pre_embed_api/assets/milvus"
        huggingface_link = "paraphrase-mpnet-base-v2"
        model = SentenceTransformer(path)
        self.model = model
        client = MongoClient("mongodb+srv://ramsishammadi:hWzgQHYmGkJum15B@cluster0.crcvzwu.mongodb.net/?retryWrites=true&w=majority")

        print("Connection Successful")
        db = client["cicero_thoughts"]

        self.news = db['news']

  def start_job(self, max_size):
        
        status = "Success"

        # Target only data that has content and title available.
        df = pd.DataFrame(self.news.find({"valuable": True, "reviewed":True, "mpnet_embeddings": {"$exists": False}}))
        df = df[~((df['content'].isna()) + (df['title'].isna()))].iloc[:max_size]

        text_data = df.apply(lambda x: x['title']+' '+BeautifulSoup(x['content']).get_text(), axis = 1).tolist()
        print(text_data[0])

        sentence_embeddings = self.model.encode(text_data)
        sentence_embeddings = normalize(sentence_embeddings)

        fields = sentence_embeddings.tolist()
        df['mpnet_embeddings'] = fields
        try:
          for row in df.to_dict("records"):
            self.news.update_one({'_id' : ObjectId(row['_id'])},{'$set': {'mpnet_embeddings': row['mpnet_embeddings']}}, upsert = False)
        except Exception as e:
          print(e)
          status = e
        return  status, len(df)

model = Embed_Model()
        
def get_model():
    return model
