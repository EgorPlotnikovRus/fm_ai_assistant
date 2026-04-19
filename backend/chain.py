from dotenv import load_dotenv
import os

from langchain_core.tools import Tool
from langchain_community.vectorstores import FAISS
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.utilities import SQLDatabase
from langchain_classic.chains import RetrievalQA
from langgraph.prebuilt import create_react_agent

from prompts import get_master_prompt

load_dotenv("config.env")
API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL")

model = ChatOpenAI(
    model="gpt-5-mini",
    temperature=0.7,
    openai_api_key=API_KEY,
    base_url=BASE_URL
)

db = SQLDatabase.from_uri("sqlite:///data/fm_players.db")
sql_toolkit = SQLDatabaseToolkit(db=db, llm=model)
sql_tools = sql_toolkit.get_tools()

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large",
    openai_api_key=API_KEY,
    base_url=BASE_URL
)
vector_store = FAISS.load_local("data/faiss_index", embeddings, allow_dangerous_deserialization=True) 

qa_chain = RetrievalQA.from_chain_type(
    llm=model,
    chain_type="stuff",
    retriever=vector_store.as_retriever(search_kwargs={"k": 4})
)

def translate_to_english(query: str) -> str:
    response = model.invoke([
        {"role": "system", "content": "Translate the following query to English. Return only the translation, nothing else."},
        {"role": "user", "content": query}
    ])
    return response.content

def rag_search(query: str) -> str:
    english_query = translate_to_english(query)
    result = qa_chain.invoke({"query": english_query})
    return result.get("result", result)

rag_tool = Tool(
    name="football_manager_guides",
    description="""Use this tool for questions about:
    - Set pieces (corners, free kicks, throw-ins)
    - Training schedules and player development
    - Tactical theory and instructions
    - Match preparation
    Do NOT use for player search or statistics.""",
    func=rag_search,  
)

all_tools = sql_tools + [rag_tool]

MASTER_PROMPT = get_master_prompt(db)

agent = create_react_agent(
    model,
    all_tools,
    prompt=MASTER_PROMPT,
)

def run_agent(question: str) -> str:
    messages = []
    for step in agent.stream(
        {"messages": [{"role": "user", "content": question}]},
        stream_mode="values",
    ):
        messages = step["messages"]
    
    # последнее сообщение от агента
    return messages[-1].content
