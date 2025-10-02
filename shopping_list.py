# shopping_list.py

import openpyxl
import os
from typing import Dict, List
from config import SPREADSHEET_FILENAME

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
    
list_manager = ShoppingListManager(SPREADSHEET_FILENAME)