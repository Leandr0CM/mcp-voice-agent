# agent_setup.py

from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from config import LLM_MODEL, REACT_PROMPT_TEMPLATE
from tools import tools

def setup_agent():
    """Configura e retorna o agente LangChain usando arquitetura ReAct"""
    
    # LLM local via Ollama (Ollama tem que estar rodando)
    llm = ChatOllama(
        model=LLM_MODEL,
        temperature=0,
        num_predict=150,
        top_p=0.9,
        repeat_penalty=1.2
    )
    
    # Cria o prompt personalizado
    prompt = PromptTemplate.from_template(REACT_PROMPT_TEMPLATE)
    
    agent = create_react_agent(llm, tools, prompt)
    
    # Executor do agente com tratamento de erros
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors="ERROR: Use English keywords only (Action, Thought, Observation, Final Answer). Never translate to Portuguese.",
        max_iterations=1,
        max_execution_time=10,
        return_intermediate_steps=True  # Habilitado para pegar observations
    )
    
    return agent_executor
