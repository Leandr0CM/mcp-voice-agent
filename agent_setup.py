# agent_setup.py

from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from config import LLM_MODEL, REACT_PROMPT_TEMPLATE
from tools import tools

def setup_agent():
    """Configura e retorna o agente LangChain usando arquitetura ReAct"""
    
    # LLM local via Ollama (certifique-se que Ollama está rodando)
    llm = ChatOllama(
        model=LLM_MODEL,
        temperature=0,  # Respostas mais determinísticas
        num_predict=150,  # REDUZIDO: limita tamanho da resposta
        top_p=0.9,
        repeat_penalty=1.2  # AUMENTADO: penaliza mais repetições
    )
    
    # Cria o prompt personalizado
    prompt = PromptTemplate.from_template(REACT_PROMPT_TEMPLATE)
    
    # Cria o agente ReAct
    agent = create_react_agent(llm, tools, prompt)
    
    # Executor do agente com tratamento de erros
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors="ERROR: Use English keywords only (Action, Thought, Observation, Final Answer). Never translate to Portuguese.",
        max_iterations=1,  # FORÇADO: apenas 1 iteração
        max_execution_time=10,  # 10 segundos timeout
        return_intermediate_steps=True  # Habilitado para pegar observations
    )
    
    return agent_executor