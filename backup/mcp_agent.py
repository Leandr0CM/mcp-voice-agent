# mcp_agent.py - Agente Inteligente com Comando de Voz para Lista de Compras
# Autor: Sistema MCP (Master Control Program)
# Descrição: Agente que gerencia lista de compras via voz usando LangChain + Ollama

import speech_recognition as sr
import openpyxl
import webbrowser
import pyttsx3
import os
from urllib.parse import quote
from typing import List, Dict
import json
import re

from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import tool
from langchain.prompts import PromptTemplate

# =============================================================================
# CONFIGURAÇÕES GLOBAIS
# =============================================================================

SPREADSHEET_FILENAME = "lista_de_compras.xlsx"
LLM_MODEL = "mistral"  # Pode usar: llama3:instruct, mistral, phi3, etc.

# Template ReAct SIMPLIFICADO - formato mais rigoroso
REACT_PROMPT_TEMPLATE = """You are a shopping list assistant. Always respond in Brazilian Portuguese, but use ENGLISH keywords.

Tools available: {tool_names}

{tools}

STRICT FORMAT (copy exactly):

Question: user's command
Thought: what should I do
Action: tool_name_here
Action Input: input_here
Observation: tool output appears here
Thought: I now know the final answer
Final Answer: your response in Portuguese

CRITICAL RULES:
1. Keywords MUST be in English: Question, Thought, Action, Action Input, Observation, Final Answer
2. NEVER translate keywords to Portuguese (no "Questão", "Pensamento", "Ação", "Observação")
3. NO markdown, NO asterisks, NO bold text
4. Execute the action ONLY ONCE - after you see the Observation, STOP and give Final Answer
5. DO NOT repeat the Question/Thought/Action/Action Input after Observation
6. The format is: Question → Thought → Action → Action Input → (wait for Observation) → Thought → Final Answer

WRONG (DO NOT DO THIS):
Question: remove leite
Thought: User wants to remove milk
Action: remove_from_shopping_list
Action Input: ["leite"]
Observation: ✓ Diminuí: Leite (agora 2x).
Question: remove leite  ← WRONG! Do not repeat
Thought: User wants to remove milk  ← WRONG! Do not repeat
Action: remove_from_shopping_list  ← WRONG! Do not repeat

CORRECT:
Question: remove leite
Thought: User wants to remove milk
Action: remove_from_shopping_list
Action Input: ["leite"]
Observation: ✓ Diminuí: Leite (agora 2x).
Thought: I now know the final answer
Final Answer: Removi um leite da lista.

NOW START (remember: ONE action only, then Final Answer):

Question: {input}
Thought:{agent_scratchpad}
"""

# =============================================================================
# GERENCIADOR DE LISTA DE COMPRAS (EXCEL COM QUANTIDADE)
# =============================================================================

class ShoppingListManager:
    """Gerencia a lista de compras em formato Excel (.xlsx) com quantidades"""
    
    def __init__(self, filename: str):
        self.filename = filename
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Cria o arquivo Excel se não existir"""
        if not os.path.exists(self.filename):
            workbook = openpyxl.Workbook()
            sheet = workbook.active
            sheet.title = "Produtos"
            sheet["A1"] = "Item"
            sheet["B1"] = "Quantidade"
            # Formatação
            sheet.column_dimensions['A'].width = 30
            sheet.column_dimensions['B'].width = 12
            workbook.save(self.filename)
            print(f"✓ Arquivo '{self.filename}' criado com sucesso.")
        else:
            # Valida se o arquivo tem a estrutura correta
            try:
                workbook = openpyxl.load_workbook(self.filename)
                sheet = workbook.active
                
                # Verifica se tem os cabeçalhos corretos
                if sheet["A1"].value != "Item" or sheet["B1"].value != "Quantidade":
                    print("⚠️  Estrutura do Excel incorreta. Recriando...")
                    sheet["A1"] = "Item"
                    sheet["B1"] = "Quantidade"
                    sheet.column_dimensions['A'].width = 30
                    sheet.column_dimensions['B'].width = 12
                    workbook.save(self.filename)
                    print("✓ Estrutura do Excel corrigida.")
            except Exception as e:
                print(f"⚠️  Erro ao validar Excel: {e}. Usando arquivo existente.")
    
    def get_products(self) -> Dict[str, int]:
        """Retorna todos os produtos com suas quantidades em um dicionário"""
        try:
            workbook = openpyxl.load_workbook(self.filename)
            sheet = workbook.active
            products = {}
            
            for row in sheet.iter_rows(min_row=2, values_only=True):
                # Verifica se a linha tem pelo menos um elemento e não está vazia
                if not row or not row[0]:
                    continue
                
                item = str(row[0]).strip()
                if not item:
                    continue
                    
                # Pega a quantidade (padrão = 1 se não existir ou for inválida)
                quantity = 1
                if len(row) > 1 and row[1]:
                    try:
                        quantity = int(row[1])
                    except (ValueError, TypeError):
                        quantity = 1
                
                products[item] = quantity
            
            return products
        except FileNotFoundError:
            return {}
        except Exception as e:
            print(f"⚠️  Erro ao ler produtos: {e}")
            return {}

    def _save_products(self, products: Dict[str, int]):
        """Salva a lista de produtos no Excel"""
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Produtos"
        sheet["A1"] = "Item"
        sheet["B1"] = "Quantidade"
        
        # Formatação dos cabeçalhos
        for cell in sheet["1:1"]:
            cell.font = openpyxl.styles.Font(bold=True)
        
        sheet.column_dimensions['A'].width = 30
        sheet.column_dimensions['B'].width = 12
        
        # Adiciona os produtos
        for index, (product, quantity) in enumerate(sorted(products.items()), start=2):
            sheet[f"A{index}"] = product
            sheet[f"B{index}"] = quantity
        
        workbook.save(self.filename)

    def add(self, items: List[str]) -> str:
        """Adiciona itens à lista (incrementa quantidade se já existir)"""
        current_products = self.get_products()
        added_items = []
        updated_items = []
        
        for item in items:
            # Limpa e formata o item
            formatted_item = item.strip().capitalize()
            if not formatted_item:
                continue
            
            # Procura se o item já existe (case-insensitive)
            existing_key = None
            for key in current_products.keys():
                if key.lower() == formatted_item.lower():
                    existing_key = key
                    break
            
            if existing_key:
                # Item já existe - incrementa quantidade
                current_products[existing_key] += 1
                updated_items.append(f"{existing_key} (agora {current_products[existing_key]}x)")
            else:
                # Item novo - adiciona com quantidade 1
                current_products[formatted_item] = 1
                added_items.append(formatted_item)
        
        if added_items or updated_items:
            self._save_products(current_products)
            msg_parts = []
            if added_items:
                msg_parts.append(f"✓ Adicionei: {', '.join(added_items)}")
            if updated_items:
                msg_parts.append(f"✓ Atualizei: {', '.join(updated_items)}")
            return ". ".join(msg_parts) + "."
        else:
            return "Nenhum item válido para adicionar."

    def remove(self, items: List[str]) -> str:
        """Remove itens da lista (decrementa quantidade ou remove completamente)"""
        current_products = self.get_products()
        removed_items = []
        decremented_items = []
        not_found = []
        
        for item in items:
            formatted_item = item.strip()
            if not formatted_item:
                continue
            
            # Procura o item (case-insensitive e ignora acentos)
            existing_key = None
            item_lower = formatted_item.lower()
            
            for key in current_products.keys():
                if key.lower() == item_lower:
                    existing_key = key
                    break
            
            if existing_key:
                if current_products[existing_key] > 1:
                    # Decrementa quantidade
                    current_products[existing_key] -= 1
                    decremented_items.append(f"{existing_key} (agora {current_products[existing_key]}x)")
                else:
                    # Remove completamente
                    del current_products[existing_key]
                    removed_items.append(existing_key)
            else:
                # Debug: mostra o que está na lista para ajudar
                not_found.append(formatted_item)
                print(f"🔍 Debug: '{formatted_item}' não encontrado. Itens na lista: {list(current_products.keys())}")
        
        if removed_items or decremented_items:
            self._save_products(current_products)
            msg_parts = []
            if removed_items:
                msg_parts.append(f"✓ Removi: {', '.join(removed_items)}")
            if decremented_items:
                msg_parts.append(f"✓ Diminuí: {', '.join(decremented_items)}")
            if not_found:
                msg_parts.append(f"('{', '.join(not_found)}' não estava na lista)")
            return ". ".join(msg_parts) + "."
        else:
            return f"✗ Nenhum dos itens foi encontrado: {', '.join(not_found)}."

    def clear_all(self) -> str:
        """Limpa toda a lista"""
        self._save_products({})
        return "✓ Lista de compras completamente limpa."

# Instância global do gerenciador
list_manager = ShoppingListManager(SPREADSHEET_FILENAME)

# =============================================================================
# FERRAMENTAS PARA O AGENTE LANGCHAIN
# =============================================================================

@tool
def add_to_shopping_list(items: str) -> str:
    """Adiciona um ou mais itens à lista de compras. 
    Input: uma lista JSON de strings como '["leite", "pão", "ovos"]' 
    Se o item já existe, incrementa a quantidade."""
    try:
        # Tenta parsear como JSON primeiro
        item_list = json.loads(items)
        if not isinstance(item_list, list):
            item_list = [str(item_list)]
    except (json.JSONDecodeError, TypeError):
        # Se falhar, tenta dividir por vírgulas
        if ',' in items:
            item_list = [i.strip() for i in items.split(',')]
        else:
            item_list = [items.strip()]
    
    return list_manager.add(item_list)

@tool
def remove_from_shopping_list(items: str) -> str:
    """Remove ou decrementa um ou mais itens da lista de compras.
    Input: uma lista JSON de strings como '["leite"]'
    Se quantidade > 1, apenas decrementa. Se = 1, remove completamente."""
    try:
        item_list = json.loads(items)
        if not isinstance(item_list, list):
            item_list = [str(item_list)]
    except (json.JSONDecodeError, TypeError):
        if ',' in items:
            item_list = [i.strip() for i in items.split(',')]
        else:
            item_list = [items.strip()]
    
    return list_manager.remove(item_list)

@tool
def list_shopping_items(placeholder: str = "none") -> str:
    """Lista todos os itens atualmente na lista de compras com suas quantidades.
    Input: use 'none' (esta ferramenta não precisa de input real)."""
    products = list_manager.get_products()
    if not products:
        return "A lista de compras está vazia no momento."
    
    count = len(products)
    total_items = sum(products.values())
    items_text = "\n".join([f"  • {item}: {qty}x" for item, qty in sorted(products.items())])
    return f"Você tem {count} tipo(s) de produto(s) ({total_items} itens no total):\n{items_text}"

@tool
def send_list_via_whatsapp(placeholder: str = "none") -> str:
    """Envia a lista de compras completa via WhatsApp.
    Input: use 'none' (esta ferramenta não precisa de input real)."""
    products = list_manager.get_products()
    if not products:
        return "✗ Não posso enviar uma lista vazia. Adicione itens primeiro."
    
    # Monta a mensagem formatada
    header = "*🛒 MINHA LISTA DE COMPRAS*\n\n"
    list_text = "\n".join([f"✓ {item} - {qty}x" for item, qty in sorted(products.items())])
    total_items = sum(products.values())
    footer = f"\n\n_Total: {len(products)} tipos de produtos ({total_items} itens)_"
    message = header + list_text + footer
    
    # Codifica e abre no WhatsApp
    encoded_message = quote(message)
    whatsapp_url = f"https://wa.me/?text={encoded_message}"
    
    try:
        webbrowser.open(whatsapp_url)
        return f"✓ WhatsApp aberto! Envie sua lista com {len(products)} tipos de produtos ({total_items} itens no total)."
    except Exception as e:
        return f"✗ Erro ao abrir WhatsApp: {e}"

@tool
def clear_shopping_list(placeholder: str = "none") -> str:
    """Limpa completamente a lista de compras.
    Input: use 'none' (esta ferramenta não precisa de input real)."""
    return list_manager.clear_all()

# =============================================================================
# CONFIGURAÇÃO DO AGENTE INTELIGENTE
# =============================================================================

def setup_agent():
    """Configura e retorna o agente LangChain usando arquitetura ReAct"""
    tools = [
        add_to_shopping_list,
        remove_from_shopping_list,
        list_shopping_items,
        send_list_via_whatsapp,
        clear_shopping_list
    ]
    
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

# =============================================================================
# CONTROLADOR DE VOZ
# =============================================================================

class VoiceController:
    """Gerencia entrada de voz (STT) e saída de voz (TTS)"""
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.tts_engine = pyttsx3.init()
        
        # Configurações de voz
        voices = self.tts_engine.getProperty('voices')
        # Tenta usar voz em português (se disponível)
        for voice in voices:
            if 'portuguese' in voice.name.lower() or 'brazil' in voice.name.lower():
                self.tts_engine.setProperty('voice', voice.id)
                break
        
        self.tts_engine.setProperty('rate', 150)  # Velocidade
        self.tts_engine.setProperty('volume', 0.9)  # Volume
        
        # Calibração do microfone
        print("🎤 Calibrando microfone para ruído ambiente...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        print("✓ Microfone calibrado e pronto!\n")

    def speak(self, text: str):
        """Fala o texto usando TTS"""
        # Remove emojis e caracteres especiais para o TTS
        clean_text = re.sub(r'[^\w\s,.\-!?()]', '', text)
        clean_text = clean_text.replace('✓', '').replace('✗', '')
        print(f"🤖 MCP: {text}")
        self.tts_engine.say(clean_text)
        self.tts_engine.runAndWait()

    def listen(self) -> str | None:
        """Escuta e converte fala em texto"""
        with self.microphone as source:
            print("👂 Ouvindo...")
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                print("🔄 Processando fala...")
                text = self.recognizer.recognize_google(audio, language="pt-BR")
                print(f"✓ Você disse: '{text}'")
                return text
            except sr.WaitTimeoutError:
                print("⏱️  Timeout: nenhum comando detectado")
                return None
            except sr.UnknownValueError:
                self.speak("Desculpe, não entendi. Pode repetir?")
                return None
            except sr.RequestError as e:
                error_msg = f"Erro no serviço de reconhecimento: {e}"
                print(f"❌ {error_msg}")
                self.speak("Estou com problemas no serviço de voz.")
                return None

# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def split_compound_command(command: str) -> List[str]:
    """
    Detecta e separa comandos compostos em ações individuais.
    
    Exemplos:
    - "adiciona leite e remove café" → ["adiciona leite", "remove café"]
    - "coloca pão e tira ovo" → ["coloca pão", "tira ovo"]
    - "remove leite e adiciona café e mostra lista" → ["remove leite", "adiciona café", "mostra lista"]
    """
    lower_cmd = command.lower()
    
    # Palavras-chave que indicam ações
    action_keywords = {
        'add': ['adiciona', 'adicione', 'coloca', 'coloque', 'põe', 'ponha', 'inclui', 'inclua'],
        'remove': ['remove', 'remova', 'tira', 'tire', 'retira', 'retire', 'exclui', 'exclua'],
        'list': ['mostra', 'mostre', 'lista', 'liste', 'exibe', 'exiba', 'vê', 'ver'],
        'send': ['envia', 'envie', 'manda', 'mande', 'whatsapp'],
        'clear': ['limpa', 'limpe', 'apaga', 'apague', 'zera', 'zere']
    }
    
    # Conectores que separam ações
    connectors = [' e ', ' depois ', ' também ', ' e depois ', ' e também ']
    
    # Conta quantas ações diferentes existem no comando
    action_count = 0
    found_actions = []
    
    for action_type, keywords in action_keywords.items():
        for keyword in keywords:
            if keyword in lower_cmd:
                # Encontra todas as posições dessa palavra-chave
                positions = [i for i in range(len(lower_cmd)) if lower_cmd.startswith(keyword, i)]
                for pos in positions:
                    found_actions.append((pos, keyword, action_type))
    
    # Se encontrou menos de 2 ações, não é comando composto
    if len(found_actions) < 2:
        return [command]
    
    # Ordena ações por posição no texto
    found_actions.sort(key=lambda x: x[0])
    
    # Tenta dividir o comando usando conectores
    parts = [command]
    for connector in connectors:
        new_parts = []
        for part in parts:
            new_parts.extend(part.split(connector))
        parts = new_parts
    
    # Filtra partes vazias e limpa espaços
    parts = [p.strip() for p in parts if p.strip()]
    
    # Se conseguiu dividir em partes válidas, retorna
    if len(parts) > 1:
        # Valida que cada parte tem pelo menos uma ação
        valid_parts = []
        for part in parts:
            part_lower = part.lower()
            has_action = any(
                keyword in part_lower 
                for keywords in action_keywords.values() 
                for keyword in keywords
            )
            if has_action:
                valid_parts.append(part)
        
        if len(valid_parts) > 1:
            return valid_parts
    
    # Se não conseguiu dividir bem, retorna comando original
    return [command]

# =============================================================================
# LOOP PRINCIPAL
# =============================================================================

def main():
    """Loop principal do assistente MCP"""
    print("\n" + "="*60)
    print("🤖 MCP - MASTER CONTROL PROGRAM")
    print("   Assistente Inteligente de Lista de Compras (v2.0)")
    print("="*60 + "\n")
    
    # Inicializa componentes
    print("⚙️  Inicializando agente inteligente...")
    agent_executor = setup_agent()
    
    print("🎤 Inicializando controle de voz...")
    voice_controller = VoiceController()
    
    # Mensagem de boas-vindas
    voice_controller.speak("MCP versão 2 ativado e pronto para atender.")
    
    print("\n" + "-"*60)
    print("📋 COMANDOS:")
    print("  • Pressione ENTER para dar um comando de voz")
    print("  • Digite 'sair' para encerrar o programa")
    print("  • Digite 'debug' para ver o conteúdo do Excel")
    print("-"*60)
    print("\n💡 Exemplos de comandos:")
    print("  - 'Adiciona leite e pão na lista'")
    print("  - 'Adiciona mais leite' (incrementa quantidade)")
    print("  - 'Remove café da lista'")
    print("  - 'Mostra minha lista'")
    print("  - 'Envia no WhatsApp'")
    print("  - 'Limpa tudo'")
    print("-"*60 + "\n")

    while True:
        user_input = input("🎯 Aguardando comando (ENTER para falar, 'sair' para encerrar): ").strip()

        if user_input.lower() in ['sair', 'exit', 'quit']:
            voice_controller.speak("Encerrando MCP. Até logo!")
            print("\n👋 Programa encerrado.\n")
            break
        
        # Comando de debug
        if user_input.lower() == 'debug':
            products = list_manager.get_products()
            print("\n" + "="*60)
            print("🔍 DEBUG - Conteúdo do Excel:")
            print("="*60)
            if products:
                for item, qty in products.items():
                    print(f"  '{item}' → {qty}x")
                print(f"\nTotal: {len(products)} tipos de produtos")
            else:
                print("  (Lista vazia)")
            print("="*60 + "\n")
            continue
        
        # Comando de voz
        voice_controller.speak("Pode falar agora.")
        voice_command = voice_controller.listen()

        if voice_command:
            try:
                print(f"\n🧠 Processando: '{voice_command}'...\n")
                
                # Detecta e separa comandos compostos
                actions = split_compound_command(voice_command)
                
                if len(actions) > 1:
                    print(f"⚠️  Comando composto detectado! {len(actions)} ações identificadas.")
                    voice_controller.speak(f"Entendi. Vou executar {len(actions)} ações.")
                    
                    # Executa cada ação separadamente
                    all_success = True
                    last_list_state = list_manager.get_products().copy()  # Salva estado antes
                    
                    for i, action in enumerate(actions, 1):
                        print(f"\n📌 Executando ação {i}/{len(actions)}: '{action}'")
                        try:
                            # Verifica estado antes da ação
                            state_before = list_manager.get_products().copy()
                            
                            result = agent_executor.invoke({"input": action})
                            
                            # Verifica se o estado mudou (confirma que ação foi executada)
                            state_after = list_manager.get_products()
                            
                            if state_before == state_after:
                                print(f"⚠️  Ação {i} não alterou a lista (possível erro)")
                            
                            print(f"✓ Ação {i} concluída\n")
                            
                        except Exception as e:
                            error_msg = f"Erro na ação {i}: {str(e)}"
                            print(f"❌ {error_msg}")
                            all_success = False
                    
                    # Resume o resultado
                    if all_success:
                        voice_controller.speak(f"Pronto! Executei todas as {len(actions)} ações com sucesso.")
                    else:
                        voice_controller.speak(f"Executei as ações, mas algumas tiveram problemas.")
                else:
                    # Comando simples - executa normalmente
                    result = agent_executor.invoke({"input": voice_command})
                    final_answer = result.get("output", "")
                    
                    # Se a resposta for genérica ou vazia, tenta extrair info útil
                    if not final_answer or final_answer == "Comando executado com sucesso!" or "Agent stopped" in final_answer:
                        # Tenta pegar a última observação das ferramentas executadas
                        intermediate_steps = result.get('intermediate_steps', [])
                        if intermediate_steps and len(intermediate_steps) > 0:
                            # Pega o resultado da última ferramenta executada
                            last_tool_output = intermediate_steps[-1][1]
                            if last_tool_output and isinstance(last_tool_output, str):
                                final_answer = last_tool_output
                            else:
                                final_answer = "Pronto! Comando executado."
                        else:
                            final_answer = "Pronto! Comando executado."
                    
                    # Limpa mensagens de erro de parsing se já temos uma resposta válida
                    if "✓" in final_answer or "✗" in final_answer:
                        # Pega só a parte útil antes de qualquer erro
                        final_answer = final_answer.split("For troubleshooting")[0].strip()
                        final_answer = final_answer.split("Check your output")[0].strip()
                    
                    voice_controller.speak(final_answer)
                
            except Exception as e:
                error_message = f"Erro ao processar comando: {str(e)}"
                print(f"❌ {error_message}")
                voice_controller.speak("Desculpe, ocorreu um erro. Tente novamente.")
        else:
            voice_controller.speak("Não recebi nenhum comando. Vamos tentar de novo?")
        
        print("\n" + "-"*60 + "\n")

# =============================================================================
# EXECUÇÃO
# =============================================================================

if __name__ == "__main__":
    main()