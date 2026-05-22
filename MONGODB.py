from pymongo import MongoClient
from pymongo.server_api import ServerApi
import json


uri = "mongodb+srv://mayankkhoria2007_db_user:WNcDEuR6gw3VcfQ6@cluster0.kuldc5t.mongodb.net/?appName=Cluster0"


# Create a MongoClient with a MongoClientOptions object to set the Stable API version
client = MongoClient(uri, server_api=ServerApi(
    version='1', strict=True, deprecation_errors=True))



with open("C:/Users/Mayank/OneDrive/Documents/CYNAPTICS/2025_iit_cutoffs.json", 'r') as file:
    data = json.load(file)

try:
   
    # Send a ping to confirm a successful connection
    client.admin.command({'ping': 1})
    print("Pinged your deployment. You successfully connected to MongoDB!")
    database=client["joshai"]
    collection=database["orcr"]
    #result=collection.insert_many(data)
    result=list(collection.find())
    print(result[3114])
    #print(len(list(result)))
finally:
    # Ensures that the client will close when you finish/error
    client.close()
