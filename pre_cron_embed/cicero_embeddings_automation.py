from bs4 import BeautifulSoup
import pandas as pd
from bson import  ObjectId
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import normalize
from pymongo import MongoClient


client = MongoClient("mongodb+srv://ramsishammadi:hWzgQHYmGkJum15B@cluster0.crcvzwu.mongodb.net/?retryWrites=true&w=majority")

db = client["cicero_thoughts"]

news = db['news']
#Initiating our model. We have a local instance for the mpnet-weights. We need it so we don't use the cloud everytime we call our cron-job
#local_path
path = "assets/milvus"
huggingface_link = "paraphrase-mpnet-base-v2"
model = SentenceTransformer(path)

# Filtering out unscanned data
df = pd.DataFrame(news.find({"valuable": True, "reviewed":True, "mpnet_embeddings": {"$exists": False}}))

# Target only data that has content and title available.
df = df[~((df['content'].isna()) + (df['title'].isna()))]

# Including both title and content in our embedding
# Some content is in html format, need to convert it to text
text_data = df.apply(lambda x: x['title']+' '+BeautifulSoup(x['content']).get_text(), axis = 1).tolist()

#Encoding text data into a vector
sentence_embeddings = model.encode(text_data)
# Assuring there is no bias/high variance in the generated vectors by normalizing the data
sentence_embeddings = normalize(sentence_embeddings)


fields = sentence_embeddings.tolist()

df['mpnet_embeddings'] = fields
#Updating only the mpnet_embeddings column for the target rows
for row in df.to_dict("records"):
  news.update_one({'_id' : ObjectId(row['_id'])},{'$set': {'mpnet_embeddings': row['mpnet_embeddings']}}, upsert = False)
