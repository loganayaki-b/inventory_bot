# agents/workflow_agent.py
from langchain.agents import AgentExecutor, create_react_agent
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from tools.inventory_tool import StockAnalysisTool
from tools.vendor_tool import VendorLookupTool
from tools.email_tool import SendOrderEmailTool
import sys
from pathlib import Path

# Add the parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import settings
import google.generativeai as genai


def create_workflow_agent():
	# Configure Gemini API
	genai.configure(api_key=settings.GEMINI_API_KEY)
	
	# Initialize Gemini LLM
	llm = ChatGoogleGenerativeAI(
		model=settings.GEMINI_MODEL_NAME,
		google_api_key=settings.GEMINI_API_KEY,
		temperature=0.7,
		convert_system_message_to_human=True
	)
	
	# Tools for our workflow
	tools = [
		StockAnalysisTool(),
		VendorLookupTool(),
		SendOrderEmailTool()
	]
	
	# Comprehensive prompt template for the entire workflow
	prompt_template = """You are an intelligent inventory management assistant that handles the complete workflow:
	1. Analyze stock levels vs provided demand
	2. Find vendor information
	3. Coordinate ordering when needed
	
	Use the available tools in sequence:
	- First call stock_analysis with JSON args containing keys: product_name, category, demand, and optionally product_id.
	  Match by product_name and category (case-insensitive, trimmed). Only if name+category fails, try product_id.
	- Then call vendor_lookup with the vendor_id from stock_analysis.
	- Finally call send_order_email if reordering is needed, passing vendor details and order info.
	
	Be precise and avoid guessing. If item not found, report clearly.
	
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