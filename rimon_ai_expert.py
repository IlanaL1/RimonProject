### Agent
### system prompt tells agent what to do
### the system prompt tells the agent when and how to use tool
### we tell it to list all docuemnts (a tool byond simple page)

from __future__ import annotations as _annotations

from dataclasses import dataclass
from dotenv import load_dotenv
import logfire
import asyncio
import httpx
import os

from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.models.openai import OpenAIModel
from openai import AsyncOpenAI
from supabase import Client
from typing import List
import streamlit as st

#load_dotenv()
OPENAI_API_KEY= st.secrets["OPENAI_API_KEY"]
SUPABASE_URL=st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_KEY=st.secrets["SUPABASE_SERVICE_KEY"]
LLM_MODEL=st.secrets["LLM_MODEL"]

llm = os.getenv('LLM_MODEL', 'gpt-4o-mini')
model = OpenAIModel(llm)

logfire.configure(send_to_logfire='if-token-present')

@dataclass
class PydanticAIDeps:
    supabase: Client
    openai_client: AsyncOpenAI

system_prompt = """
You are an expert at understanding the Pomegranate Place Facebook group documents that you have access to, which concerns Jewish life around the world, or the Israel-Palestine conflict, or US politics, or antisemitism or Zionism or racism or culture or community. 

Your only job is to assist with this and you don't answer other questions besides describing what you are able to do.

Don't ask the user before taking an action, just do it. Always make sure you look at the documentation with the provided tools before answering the user's question unless you have already.

When you first look at the documentation, always start with RAG.
Please extract paragraphs from each returned chunk in RAG, and add a citation for that paragraph. 
The citation should appear directly below the paragraph, and should contain the article title, author, date and url which is the source of the chunk used to extract this paragraph.  

Then also always check the list of available Pomegranate Place article urls and retrieve the content of page(s) if it'll help.
Please extract paragraphs from each returned page content that is relevant, 
The citation should appear directly below the paragraph, and should contain the article title, author, date and url which is the source of the chunk used to extract this paragraph.  


A citation should contain the article title, publication name, author(s), and date of publication, and url link to full article. 


Always let the user know when you didn't find the answer in the documentation or the right URL - be honest.
"""

rimon_ai_expert = Agent(
    model,
    system_prompt=system_prompt,
    deps_type=PydanticAIDeps,
    retries=2
)

async def get_embedding(text: str, openai_client: AsyncOpenAI) -> List[float]:
    """Get embedding vector from OpenAI."""
    try:
        response = await openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return [0] * 1536  # Return zero vector on error

@rimon_ai_expert.tool
async def retrieve_relevant_documentation(ctx: RunContext[PydanticAIDeps], user_query: str) -> str:
    """
    Retrieve relevant documentation chunks based on the query with RAG.
    
    Args:
        ctx: The context including the Supabase client and OpenAI client
        user_query: The user's question or query
        
    Returns:
        A formatted string containing the top 5 most relevant documentation chunks
    """
    try:
        # Get the embedding for the query
        query_embedding = await get_embedding(user_query, ctx.deps.openai_client)
        
        # Query Supabase for relevant documents
        result = ctx.deps.supabase.rpc(
            'match_rimon_pages',
            {
                'query_embedding': query_embedding,
                'match_count': 5,
                #'filter': {'source': 'pydantic_ai_docs'}
            }
        ).execute()
        
        if not result.data:
            return "No relevant documentation found."
            
        # Format the results
        formatted_chunks = []
        for doc in result.data:
            chunk_text = f"""
# {doc['title']}

{doc['content']}

{doc['url']}
"""
            formatted_chunks.append(chunk_text)
            
        # Join all chunks with a separator
        return "\n\n---\n\n".join(formatted_chunks)
        
    except Exception as e:
        print(f"Error retrieving documentation: {e}")
        return f"Error retrieving documentation: {str(e)}"

@rimon_ai_expert.tool
async def list_documentation_pages(ctx: RunContext[PydanticAIDeps]) -> List[str]:
    """
    Retrieve a list of all available Pomegranate Place article urls.
    
    Returns:
        List[str]: List of unique URLs for all Pomegranate Place article urls
    """
    try:
        # Query Supabase for unique URLs where source is pydantic_ai_docs
        result = ctx.deps.supabase.from_('rimon_pages')\
            .select('url') \
            .execute()
           # .eq('metadata->>source', 'pydantic_ai_docs') \ #IL remove

        
        if not result.data:
            return []
            
        # Extract unique URLs
        urls = sorted(set(doc['url'] for doc in result.data))
        return urls
        
    except Exception as e:
        print(f"Error retrieving pages: {e}")
        return []

@rimon_ai_expert.tool
async def get_page_content(ctx: RunContext[PydanticAIDeps], url: str) -> str:
    """
    Retrieve the full content of a specific documentation page by combining all its chunks.
    
    Args:
        ctx: The context including the Supabase client
        url: The URL of the page to retrieve
        
    Returns:
        str: The complete page content with all chunks combined in order
    """
    try:
        # Query Supabase for all chunks of this URL, ordered by chunk_number
        result = ctx.deps.supabase.from_('rimon_pages') \
            .select('title, content, chunk_number,url') \
            .eq('url', url) \
            .order('chunk_number') \
            .execute()
            # .eq('metadata->>source', 'pydantic_ai_docs') \ #IL rmeove
        
        if not result.data:
            return f"No content found for URL: {url}"
            
        # Format the page with its title and all chunks
        page_title = result.data[0]['title'].split(' - ')[0]  # Get the main title
        formatted_content = [f"# {page_title}\n"]
        
        # Add each chunk's content
        for chunk in result.data:
            formatted_content.append(chunk['content'])
            
        # Join everything together
        return "\n\n".join(formatted_content)
        
    except Exception as e:
        print(f"Error retrieving page content: {e}")
        return f"Error retrieving page content: {str(e)}"