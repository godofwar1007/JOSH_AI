import asyncio
import uuid
import os
import itertools
import httpx  
from typing import TypedDict, Annotated, Literal
from contextlib import asynccontextmanager
from placement import placement_Retriever
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse  
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from qdrant import rulesretriever
from orcr import ORCR_Retriever
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool


# load_dotenv()
PASTE_GROQ_KEYS_HERE = "" #separated by commas


PASTE_SERPER_KEY_HERE = ""


SESSION_STORAGE = {}

class APIKeyRotator:
    def __init__(self, raw_keys_string: str):
        self.keys = [k.strip() for k in raw_keys_string.split(",") if k.strip()]
        if not self.keys:
            raise ValueError("CRITICAL: No valid API keys provided in configuration.")
        self.pool = itertools.cycle(self.keys)
        print(f"Successfully initialized Key Pool with {len(self.keys)} keys.")

    def get_next_key(self) -> str:
        return next(self.pool)

groq_key_rotator = APIKeyRotator(PASTE_GROQ_KEYS_HERE)

@asynccontextmanager
async def lifespan(app: FastAPI):
    agent.initialize()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

db_retriever = ORCR_Retriever()
retriever = rulesretriever()
placement_retriever = placement_Retriever()


@tool
async def retrieve_college_allocations_JEE_Adv(rank: int, category: str, gender: str) -> str:
    """Queries the database to look up acceptable engineering colleges and academic programs based on a student's rank. For specifically JEE MAINS and IIITs and NITs .
    Args 
     rank :the student's JEE ADVANCED rank in integer  .
     category : for e.g. OPEN,OBC-NCL,GEN-EWS,SC,ST ,
      gender : the gender of the user like Gender-Neutral or Female-Only."""   
    try:
        results = await asyncio.to_thread(db_retriever.runa, rank, category, gender)
        if not results:
            return "No colleges found"
        return "Database Matching Allocations:\n" + str(results)
    except Exception as e:
        return f"Database lookup failed: {str(e)}"
@tool
async def retrieve_college_allocations_JEE_Main(rank: int, category: str, gender: str) -> str:
    """Queries the database to look up acceptable engineering colleges and academic programs based on a student's rank. For specifically JEE MAINS and IIITs and NITs .
    Args 
     rank :the student's JEE MAIN rank in integer  .
     category : for e.g. OPEN,OBC-NCL,GEN-EWS,SC,ST ,
      gender : the gender of the user like Gender-Neutral or Female-Only."""
    try:
        results = await asyncio.to_thread(db_retriever.runm, rank, category, gender)
        if not results:
            return "No colleges found"
        return "Database Matching Allocations:\n" + str(results)
    except Exception as e:
        return f"Database lookup failed: {str(e)}"
@tool
async def placement_data(institute: str) -> str:
    """Fetches the latest placement statistics for a specified institute from the database."""
    try :
        results = await asyncio.to_thread(placement_retriever.run , institute)
        s = ""
        for item in results :
            s = s+ item
        if not results :
            return f"No placements data found for {institute} . "
        return f"placements results for {institute} are : {s}"
    except Exception as e:
        return f"placement data retrieval faile ."


@tool
async def search_jossa(query: str) -> str:
    """Queries the local indexed document cache for official JoSAA rules, requirements, and reference PDFs."""
    try:
        response = await asyncio.to_thread(retriever.search, query, 3)
        return f"Found response for '{query}':\nresponse : {response}"
    except Exception as e:
        return f"JoSAA local index search failed: {str(e)}"

@tool
async def search_google_images(query: str) -> str:
    """Searches Google Images using Serper.dev and returns the top image URL."""
    url = "https://google.serper.dev/images"
    payload = {"q": query, "num": 3}  
    headers = {"X-API-KEY": PASTE_SERPER_KEY_HERE, "Content-Type": "application/json"}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            images = data.get("images", [])
            if not images:
                return f"no images found for: {query}"
                
            fi = images[0]
            return f"image for '{query}' is:\nTitle: {fi.get('title', 'Image')}\nURL: {fi.get('imageUrl')}"
        except Exception as e:
            return f"image search failed for query: {query}"

@tool
async def search_web_serper(query: str) -> str:
    """Searches the web via live Google engines to retrieve the latest real-time status and information updates."""
    if not PASTE_SERPER_KEY_HERE:
        return "Error: SERPER_API_KEY is not set."
        
    url = "https://google.serper.dev/search"
    payload = {"q": query}
    headers = {"X-API-KEY": PASTE_SERPER_KEY_HERE, "Content-Type": "application/json"}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            snippets = []
            for item in data.get("organic", [])[0:3]:
                snippets.append(f"title : {item.get('title')}\nsnippet : {item.get('snippet')}")
            if not snippets:
                return f"found nothing on web about {query}"
            
            return "web search has given:\n" + "\n".join(snippets)
        except Exception as e:
            return f"Web search for query: {query} returned an error or empty context."


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    short_term_memory: list  
    session_id: str
    user_id: str
    current_input: str

class OrchestratorAgent:
    def __init__(self, window_size = 5):
        self.tools = []
        self.llm_pool = None 
        self.graph = None 
        self.ws = window_size

    def initialize(self):
             
                      
        self.tools = [search_google_images, search_web_serper,search_jossa,retrieve_college_allocations_JEE_Main ,placement_data ,retrieve_college_allocations_JEE_Adv ]
        
        
        keys = [it.strip() for it in PASTE_GROQ_KEYS_HERE.split(",") if it.strip()]
        if not keys:
            raise ValueError("No keys found please check the api store.")
            
        llm_instances = []
        for key in keys:
            instance = ChatGroq(
                model="openai/gpt-oss-120b", 
                temperature=0,
                groq_api_key=key
            ).bind_tools(self.tools)
            llm_instances.append(instance)
            
        self.llm_pool = itertools.cycle(llm_instances)
        print(f"Successfully initialized LLM Pool with {len(llm_instances)} distinct API connections.")
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(AgentState)
        builder.add_node("load_memory", self._load_memory_node)
        builder.add_node("agent", self._agent_node)
        builder.add_node("tools", self._tools_node)
        
        builder.add_edge(START, "load_memory")
        builder.add_edge("load_memory", "agent")
        builder.add_conditional_edges(
            "agent",
            self._route_after_agent,
            {"tools": "tools", END: END}
        )
        builder.add_edge("tools", "agent")
        return builder.compile()

    def _load_memory_node(self, state: AgentState) -> dict:
        system_prompt = """You are a highly capable AI assistant with access to web search for both Text and Images.
        INSTRUCTIONS:
        1. Use `search_google_images` when the user wants an image. Format it cleanly like: [Image Link](url)
        2. Use `search_web_serper` for live news or current events.
        3. Give short, crisp, and to-the-point answers. Do not elaborate unless specifically asked.
        4. If someone asks about IIT Indore, welcome them with sweet words as you are the AI hosted by IIT Indore.
        5. If asked to search about Opening and Closing ranks of any IIT and any branch, use retrieve_college_allocations.
        """
        convmsg = [SystemMessage(content=system_prompt)]
        for item in state.get("short_term_memory", [])[-5:]:
            if item.get("role") == "user":
                convmsg.append(HumanMessage(content=item["content"]))
            elif item.get("role") == "ai":
                convmsg.append(AIMessage(content=item["content"]))
                
        convmsg.append(HumanMessage(content=state.get("current_input")))
        return {"messages": convmsg} 
    
    async def _agent_node(self, state: AgentState) -> dict:
        current_llm = next(self.llm_pool)
        try:
            response = await current_llm.ainvoke(state["messages"])
            return {"messages": [response]}
        except Exception as e:
            print(f"   [LLM Pool Failover Triggered] Error context: {e}")
            fallback_message = AIMessage(content="⚠️ Request peak limit reached across current pipeline node. Retrying connection...")
            return {"messages": [fallback_message]}
    
    async def _tools_node(self, state: AgentState) -> dict:
        last_message = state["messages"][-1]
        tools_lookup = {t.name: t for t in self.tools}
        tool_results = []
        
        for tool_call in last_message.tool_calls:
            tool_func = tools_lookup.get(tool_call["name"])
            if tool_func:
                result = await tool_func.ainvoke(tool_call["args"])
                tool_results.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
                
        return {"messages": tool_results}
    
    def _route_after_agent(self, state: AgentState) -> Literal["tools", END]:
        last_message = state["messages"][-1]
        return "tools" if hasattr(last_message, "tool_calls") and last_message.tool_calls else END

    def get_stream(self, initial_state: dict):
        return self.graph.astream(initial_state, stream_mode="messages")

agent = OrchestratorAgent(window_size=5)


@app.post("/chat")
async def joshai(
    query: str, 
    username: str = Query(..., description="Unique user identification name required to access chat"),
    session_id: str = Query(default="default_session")
):    
    cleaned_username = username.strip()
    if not cleaned_username or len(cleaned_username) < 3:
        raise HTTPException(
            status_code=400, 
            detail="Access Denied: A valid, unique username (minimum 3 characters) must be provided."
        )

    storage_key = f"{cleaned_username}_{session_id}"
    
    global SESSION_STORAGE
    history = SESSION_STORAGE.get(storage_key, [])
    
    initial_state = {
        "messages": [],
        "short_term_memory": list(history),
        "session_id": session_id,
        "user_id": cleaned_username, 
        "current_input": query,
    }

    async def token_streamer():
        full_reply = ""
        async for message, metadata in agent.get_stream(initial_state):
            if isinstance(message, AIMessage) and metadata.get("langgraph_node") == "agent":
                if message.content:
                    full_reply += message.content
                    yield message.content

        history.append({"role": "user", "content": query})
        history.append({"role": "ai", "content": full_reply})
        SESSION_STORAGE[storage_key] = history[-10:]  

    return StreamingResponse(token_streamer(), media_type="text/plain")
