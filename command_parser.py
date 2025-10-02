# command_parser.py

from typing import List

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