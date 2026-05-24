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


api="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIiwic3ViamVjdCI6ImFwaS1rZXk6MjBhZWUyOWYtMDU5OC00OGM0LWJkMDMtNGU4YTE3MGFiMDEzIn0.gJ9hIQCNvLleJydfDp0PrWVSZE5R7GAbi5cKI5f5GCM"
url="https://3463a70a-212e-4ee7-b027-a65de3c43055.us-east4-0.gcp.cloud.qdrant.io"
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


