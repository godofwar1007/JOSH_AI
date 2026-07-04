import os
import asyncio
from qdrant_client import AsyncQdrantClient, models 
from rank_bm25 import BM25Okapi

api = "API-KEY"
url = "QDRANT-URL"

class RulesRetriever:
     def __init__(self):
          self.client = AsyncQdrantClient(
                url=url,
                api_key=api,
                cloud_inference=True
          )
          
     async def search(self, query: str, numberofchunks: int):
          response = await self.client.query_points(
               collection_name="rules",
               query=models.Document(
                   text=query,
                   model="sentence-transformers/all-MiniLM-L6-v2" 
               ), 
               limit=numberofchunks * 4
          )
          
          results = response.points
          
          l = []
          k = []
          for r in results:
               p = r.payload
               m = p["metadata"]
               t = m.split()
               l.append(t)
               k.append(p["text"])
          
          bm25 = BM25Okapi(l)
          i = query.split()
          scores = bm25.get_scores(i)
          scores = sorted(enumerate(scores), reverse=True, key=lambda x: x[1])[:numberofchunks:1]
          
          selectedchunks = ""
          for idx, s in scores:
               selectedchunks = selectedchunks + (k[idx])
          return selectedchunks
     
async def main():
    retriever = RulesRetriever()
    query = "What are the eligibility criteria for JEE Advanced?"
    print(f"Searching for: {query}")
    result = await retriever.search(query, numberofchunks=2)
    print("\n--- Retrieved Chunks ---")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
