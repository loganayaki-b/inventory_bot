# agents/email_agent.py
from langchain.agents import AgentExecutor, create_react_agent
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from tools.email_tool import SendOrderEmailTool
from config.settings import settings
import google.generativeai as genai

def create_email_agent():
    # Configure Gemini API
    genai.configure(api_key=settings.GEMINI_API_KEY)
    
    # Initialize Gemini LLM
    llm = ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL_NAME,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.7,
        convert_system_message_to_human=True
    )
    
    # Tools for email agent
    tools = [SendOrderEmailTool()]
    
    # Custom prompt template
    prompt_template = """You are an email automation assistant that sends purchase orders to vendors.
    Use the send_order_email tool to communicate with vendors.

    Tools available:
    - send_order_email: Send purchase order email to vendor

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