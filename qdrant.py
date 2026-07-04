import json
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams


dic={}
docs=[]
with open("rules.json","r") as file:
    dic=json.load(file)

c=1
for i in dic:
    doc={"text":i,"metadata":dic[i],"id":c}
    c=c+1
    docs.append(doc)


api="QDRANT-API-KEY"
url="QDRANT-URL"
model=SentenceTransformer("all-MiniLM-L6-v2")

payloads=[]
vectors=[]
ids=[]
for i in docs:
    vec=model.encode(i["text"],convert_to_numpy=True)
    vectors.append(vec)
    d={"text":i["text"],"metadata":i["metadata"]}
    payloads.append(d)
    ids.append(i["id"])


client = QdrantClient(
    url=url,
    api_key=api,
    cloud_inference=True,  # Enable remote inference
)

client.create_collection(
    collection_name="rules",
    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
)

client.upload_collection(
    collection_name="rules",
    vectors=vectors,
    ids=ids,
    payload=payloads,
)


