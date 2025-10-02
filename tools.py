# tools.py

import json
import webbrowser
from urllib.parse import quote
from langchain.tools import tool
from shopping_list import list_manager

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

# Lista exportável de ferramentas para o agente
tools = [
    add_to_shopping_list,
    remove_from_shopping_list,
    list_shopping_items,
    send_list_via_whatsapp,
    clear_shopping_list
]