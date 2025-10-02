# main.py

from agent_setup import setup_agent
from voice_controller import VoiceController
from shopping_list import list_manager
from command_parser import split_compound_command

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
    voice_controller.speak("MCP versão 2 on.")
    
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

if __name__ == "__main__":
    main()