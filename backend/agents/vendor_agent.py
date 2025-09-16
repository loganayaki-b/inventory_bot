# agents/vendor_agent.py
from langchain.agents import AgentExecutor, create_react_agent
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from tools.vendor_tool import VendorLookupTool
from config.settings import settings
import google.generativeai as genai

def create_vendor_agent():
    # Configure Gemini API
    genai.configure(api_key=settings.GEMINI_API_KEY)
    
    # Initialize Gemini LLM
    llm = ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL_NAME,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.7,
        convert_system_message_to_human=True
    )
    
    # Tools for vendor agent
    tools = [VendorLookupTool()]
    
    # Custom prompt template
    prompt_template = """You are a vendor management assistant that helps identify suppliers for products.
    Use the available tools to find vendor information.

    Tools available:
    - vendor_lookup: Find vendor for a specific vendor ID

    Question: {input}
    Thought: {agent_scratchpad}
    """
    
    prompt = PromptTemplate.from_template(prompt_template)
    
    # Create agent
    agent = create_react_agent(llm, tools, prompt)
    memory = ConversationBufferMemory(memory_key="chat_history")
    
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory,
        verbose=True,
        handle_parsing_errors=True
    )
    
    return agent_executor