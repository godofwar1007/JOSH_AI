import asyncio
import uuid
import os
import requests
import wikipedia
from typing import TypedDict, Annotated, Literal,cast
from datetime import datetime

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from dotenv import load_dotenv
from pydantic import SecretStr
import httpx
import asyncpg


from Asyncrulesretriever import rulesretriever
from orcr_retriever import ORCR_Retriever
from user_crud_asyncpg import init_db_pool,close_db_pool,get_by_id,get_by_email,pool,get_pool,upadate_schema,usage_schema,update_user

load_dotenv()

josaa_retriever = None

async def get_josaa_retriver():
    global josaa_retriever
    if josaa_retriever is None:
        josaa_retriever=rulesretriever()
    return josaa_retriever

@tool
async def search_josaa_rules(query:str)-> str:
    """"
      Retrieve official JoSAA counselling rules, seat allocation policies, fee structure,
    document verification, and other procedural guidelines.
    Use this tool for any question about JoSAA rules, not for rank-based college prediction.
    
    Args:
        query: The specific rule or policy question, e.g., "seat acceptance fee", "document verification deadline".
    
    """
    print(f"    [Tool Execution] Searching JoSAA rules for: {query}")
    try:

        retriever=await get_josaa_retriver()
        chunks=await retriever.search(query,3)

        if not chunks:
            return "No relevant josaa rules found"
        
        result =  "Relevant josaa rules:\n\n"+"\n---\n".join(chunks)
        return result 
    
    except Exception as e:

        error=f"josaa rule retrieval failed : {str(e)}" 
        return error 

orcr_retriever = None

async def get_orcr_retriever():
    global orcr_retriever
    if orcr_retriever is None:
        orcr_retriever=ORCR_Retriever()
    return orcr_retriever

@tool
async def search_orcr_colleges(rank: int,category: str,gender:str)->str:
    """
      Predict possible colleges based on JoSAA opening/closing rank data.
    Use this when the user asks for college prediction, seat chances, or which IIT/NIT they might get.
    Do NOT use for rules or fee queries.
    
    Args:
        rank: User's JEE Advanced rank (integer).
        category: Seat category like "OPEN", "OBC-NCL", "SC", "ST", "EWS".
        gender: "Gender-Neutral" or "Female-only".
    """    
    print(f"   [Tool Execution] ORCR prediction for rank={rank}, category={category}, gender={gender}")

    try:
        retriever=await get_orcr_retriever()
        results=await retriever.run(rank,category,gender)

        if not results:
            resultt=f"No colleges found for rank {rank} in {category} ({gender})"  
            return resultt

        lines = [f"Possible colleges for rank {rank} ({category}, {gender}):\n"]
        for i,item in enumerate(results,1):
            lines.append(
                f"{i}. {item['Institute']} – {item['Academic program']}\n"
                f"   Opening: {item['Opening Rank']} | Closing: {item['Closing Rank']} | Seat: {item['Seat Type']}\n"
            )
        return "\n".join(lines)
    except Exception as e:
        result = f"ORCR search failed {str(e)}"
        return result    

@tool
async def search_wikipedia_with_images(query: str) -> str:
    """
    Searches Wikipedia for a given topic and returns a brief summary along with the main image URL.
    Use this tool for encyclopedic information, facts, or when the user asks for an image of a concept.
    
    Args:
        query: The topic to search for e.g.,( "IIT Bombay" , "IIT Indore" etc)
    """
    print(f"   [Tool Execution] Searching Wikipedia for: {query}")
    try:
        page = await asyncio.to_thread(wikipedia.page,query, auto_suggest=True)
        summary = await asyncio.to_thread(wikipedia.summary,query, sentences=3, auto_suggest=True)
        valid_images = [img for img in page.images if not img.endswith('.svg')]
        image_url = valid_images[0] if valid_images else "No image available."
        
        return f"Summary: {summary}\nImage URL: {image_url}"
        
    except wikipedia.exceptions.DisambiguationError as e:
        options = ", ".join(e.options[:5])
        return f"Query '{query}' is too ambiguous. Did you mean one of these? {options}"
    except wikipedia.exceptions.PageError:
        return f"No Wikipedia page found for '{query}'."
    except Exception as e:
        return f"Wikipedia error: {str(e)}"


@tool
async def search_web_serper(query: str) -> str:
    """
    Searches the web using Google Search (via Serper.dev).
    Use this for real-time information, current events, or things not found on Wikipedia.
    
    Args:
        query: The search query.
    """
    print(f"   [Tool Execution] Searching Web for: {query}")
    api_key = "7ef07e2e60a140a65c987db2f86dd2ae40be136" 
    if not api_key:
        return "Error: SERPER_API_KEY is not set in environment variables."
        
    url = "https://google.serper.dev/search"
    payload = {"q": query}
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Extract the top 3 organic snippets
            snippets = []
            for item in data.get("organic", [])[:3]:
                snippets.append(f"- {item.get('title')}: {item.get('snippet')}")
                
            if not snippets:
                return "No web results found."
                
            return "Web Search Results:\n" + "\n".join(snippets)
        
    except Exception as e:
        return f"Web search failed: {str(e)}"



class AgentState(TypedDict):
   
    messages: Annotated[list, add_messages]
    short_term_memory: list  
    session_id: str
    user_id: str
    user_email:str
    turn_count: int
    tools_used: list
    api_calls_count: int
    errors: list
    current_input: str
    final_response: str
    output_json: dict


class OrchestratorAgent:
    def __init__(self, window_size: int = 5):
        self.llm = None
        self.tools = []
        self.graph = None
        self.window_size = window_size 
    
    async def initialize(self):
        """Set up local tools and build the graph."""
        

        self.tools = [search_wikipedia_with_images, search_web_serper,search_josaa_rules,search_orcr_colleges]

     
        groq_api_key=SecretStr("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"  )
        
        self.llm = ChatGroq(
            model="openai/gpt-oss-120b",
            temperature=0,
            api_key=groq_api_key
         ).bind_tools(self.tools)
        
        self.graph = self._build_graph()

    
    def _build_graph(self):
        builder = StateGraph(AgentState)
        
        builder.add_node("load_memory", self._load_memory_node)
        builder.add_node("agent", self._agent_node)
        builder.add_node("tools", self._tools_node)
        builder.add_node("save_memory", self._save_memory_node)
        builder.add_node("format_output", self._format_output_node)
        
        builder.add_edge(START, "load_memory")
        builder.add_edge("load_memory", "agent")
        
        builder.add_conditional_edges(
            "agent",
            self._route_after_agent,
            {"tools": "tools", "save_memory": "save_memory"}
        )
        
        builder.add_edge("tools", "agent")
        builder.add_edge("save_memory", "format_output")
        builder.add_edge("format_output", END)
        
        return builder.compile()

    async def _load_memory_node(self, state: AgentState) -> dict:

        user_profile=None
        pool=get_pool()
        if pool is not None:
            async with pool.acquire() as conn:
                user_profile=await get_by_email(cast(asyncpg.Connection,conn),state["user_email"])

        if user_profile:
            user_info = f"""
                    - Name: {user_profile.name}
                    - Advanced Rank: {user_profile.adv_rank}
                    - Category: {user_profile.category.value}
                    - Gender: {user_profile.gender.value}
                    - Preferred Branches: {', '.join(user_profile.preferred_branches) if user_profile.preferred_branches else 'None'}
                    """    
        else:
            user_info="\n- User not found. Please register first."

        
               


        system_prompt = f"""You are a highly capable AI assistant with access to web search and Wikipedia.
        
        USER PROFILE ={user_info}
        INSTRUCTIONS:
        1. Use `search_wikipedia_with_images` for encyclopedic facts, history, or when the user wants an image.
        2. Use `search_web_serper` for live news, current events, or technical documentation.
        3. ALWAYS provide the image URL to the user if the Wikipedia tool returns one. Format it cleanly like: [Image Link](url)
        4. Use the conversation history to understand context.
        """
        
        convmsg = [SystemMessage(content=system_prompt)]
        for memory_item in state.get("short_term_memory", []):
            if memory_item["role"] == "user":
                convmsg.append(HumanMessage(content=memory_item["content"]))
            elif memory_item["role"] == "ai":
                convmsg.append(AIMessage(content=memory_item["content"]))
                
        convmsg.append(HumanMessage(content=state["current_input"]))
        
        return {"messages": convmsg}
    
    async def _agent_node(self, state: AgentState) -> dict:
        print(f"\n [AGENT NODE] - API call #{state.get('api_calls_count', 0) + 1}")
        try:
            response = await self.llm.ainvoke(state["messages"])

            tool_calls_requested = response.tool_calls if hasattr(response, 'tool_calls') else []
            if tool_calls_requested:
                print(f"   Tool calls requested: {[tc['name'] for tc in tool_calls_requested]}")
            
            return {
                "messages": [response],
                "api_calls_count": state.get("api_calls_count", 0) + 1
            }
        except Exception as e:
            print(f"   LLM call failed: {e}")
            return {
                "messages": [AIMessage(content=f"Error: {str(e)}")],
                
                "errors": state.get("errors", []) + [str(e)],
                "api_calls_count": state.get("api_calls_count", 0) + 1
            }
    
    async def _tools_node(self, state: AgentState) -> dict:
        print("\n[TOOLS NODE]") # for debugging
        last_message = state["messages"][-1]
        tools_lookup = {t.name: t for t in self.tools}
        
        tool_results = []
        tools_used = state.get("tools_used", [])
        errors = state.get("errors", [])
        
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_call_id = tool_call["id"]
            
            print(f"   Executing: {tool_name}")
            try:
                tool_func = tools_lookup.get(tool_name)
                result = await tool_func.ainvoke(tool_args) if tool_func else f"Tool '{tool_name}' not found"
                tools_used.append({"tool": tool_name, "args": tool_args, "success": True})
                tool_results.append(ToolMessage(content=str(result), tool_call_id=tool_call_id))
            except Exception as e:
                print(f"   Tool {tool_name} failed: {e}")
                tools_used.append({"tool": tool_name, "args": tool_args, "success": False, "error": str(e)})
                errors.append(str(e))
                tool_results.append(ToolMessage(content=f"Error: {str(e)}", tool_call_id=tool_call_id))
                
        return {"messages": tool_results, "tools_used": tools_used, "errors": errors}
    
    def _save_memory_node(self, state: AgentState) -> dict:
        print("\n[SAVE MEMORY NODE]")
        final_ai_response = ""
        for msg in reversed(state["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                final_ai_response = msg.content
                break
        
        current_memory = state.get("short_term_memory", [])
        current_memory.append({"role": "user", "content": state["current_input"]})
        current_memory.append({"role": "ai", "content": final_ai_response})
        
        max_messages = self.window_size * 2
        if len(current_memory) > max_messages:
            current_memory = current_memory[-max_messages:]
            print(f"   Trimming memory to last {self.window_size} turns.")
        
        return {
            "short_term_memory": current_memory,
            "turn_count": state.get("turn_count", 0) + 1,
            "final_response": final_ai_response
        }
    
    def _format_output_node(self, state: AgentState) -> dict:
        print("\n[FORMAT OUTPUT NODE]")
        output_json = {
            "status": "success" if not state.get("errors") else "partial_success",
            "session_id": state["session_id"],
            "user_id": state["user_id"],
            "turn": state.get("turn_count", 1),
            "output": {"response": state.get("final_response", "")},
            "memory": {"messages_in_window": len(state.get("short_term_memory", []))},
            "performance": {"api_calls_made": state.get("api_calls_count", 0)},
            "errors": state.get("errors", [])
        }
        return {"output_json": output_json}
    
    def _route_after_agent(self, state: AgentState) -> Literal["tools", "save_memory"]:
        last_message = state["messages"][-1]
        return "tools" if hasattr(last_message, "tool_calls") and last_message.tool_calls else "save_memory"

    async def chat(self, user_message: str, user_id: str, session_id: str = None, short_term_memory: list = None) -> dict:
        initial_state = {
            "messages": [],
            "short_term_memory": short_term_memory or [],
            "session_id": session_id or str(uuid.uuid4()),
            "user_id": user_id,
            "current_input": user_message,
        }
        final_state = await self.graph.ainvoke(initial_state)
        return {
            "output_json": final_state["output_json"],
            "updated_memory": final_state["short_term_memory"]
        }

#main function
async def main():

    await init_db_pool()

    
    try:
        agent = OrchestratorAgent(window_size=5)
        await agent.initialize()
    except Exception as e:
        print(f"Agent initialization faled{e}")    
        return 
    
    current_short_term_memory = [] 
    

   
    
    while True:
        user_input = input("  You: ")
        if user_input.lower() in ['quit', 'exit', 'q']:
            break
            
        try:
            result = await agent.chat(
                user_message=user_input,
                user_id="iit_dev_001",
                short_term_memory=current_short_term_memory
            )
            
            current_short_term_memory = result["updated_memory"]
            ai_response = result["output_json"].get("output", {}).get("response", "")
            
            print(f"\n AI:\n{ai_response}\n")
            print("-" * 50)
            
        except Exception as e:
            print(f"\n Execution Error: {e}\n")

if __name__ == "__main__":
    asyncio.run(main())
