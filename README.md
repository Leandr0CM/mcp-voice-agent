# MCP - Master Control Program

Assistente inteligente com comando de voz para gerenciamento de listas de compra, construído com Python, LangChain e Ollama.

## Funcionalidades

- **Controle por Voz:** Adicione, remova, liste e envie itens usando comandos de voz em linguagem natural.
- **Persistência de Dados:** A lista de compras é salva em um arquivo `.xlsx`, com suporte a quantidades.
- **Inteligência Artificial Local:** Utiliza um LLM (Large Language Model) rodando localmente via Ollama para interpretar os comandos.
- **Integração com WhatsApp:** Envia a lista de compras formatada para o WhatsApp através de um link `wa.me`.
- **Execução via Terminal:** Interface de linha de comando simples e direta.

## Setup & Execução

1.  **Clone o repositório:**
    ```bash
    git clone [https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git](https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git)
    cd NOME_DO_REPOSITORIO
    ```

2.  **Crie e ative um ambiente virtual:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # ou venv\Scripts\activate no Windows
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Baixe um modelo LLM com Ollama:**
    ```bash
    ollama pull mistral
    ```
    Se não tiver instalado no computador, baixe aqui: https://ollama.com/download

5.  **Execute o programa:**
    ```bash
    python main.py
    ```

## Estrutura do Projeto

O projeto é modularizado para separação de responsabilidades:

- `main.py`: Ponto de entrada e loop principal da aplicação.
- `config.py`: Constantes e configurações globais, incluindo o template do prompt.
- `shopping_list.py`: Gerenciamento da lógica do arquivo Excel.
- `tools.py`: Definição das ferramentas (`@tool`) para o agente LangChain.
- `agent_setup.py`: Construção e configuração do agente ReAct.
- `voice_controller.py`: Lógica de reconhecimento de fala (STT) e síntese de voz (TTS).
- `command_parser.py`: Funções auxiliares para parsing de comandos.