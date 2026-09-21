import csv
import os
import re

def check_file_exists(file_path: str) -> bool:
    if not os.path.isdir(os.path.dirname(file_path)):
        os.makedirs(os.path.dirname(file_path))
    return os.path.isfile(file_path)

def append_csv(file_path: str, data: dict) -> None:
    with open(file_path, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(data.values())

def parse_notification(titulo: str, texto: str):
    if titulo == "Você recebeu um Pix":
        padrao = r'Pix recebido no valor de R\$ ([\d,.]+), (de .+?), em (\d{2}/\d{2}/\d{4})\.'
        m = re.search(padrao, texto)
        if m:
            valor = float(m.group(1).replace('.', '').replace(',', '.'))
            return {
                "data": m.group(3),
                "valor": valor,
                "descricao": m.group(2),
                "operacao": "PIX",
            }
    elif titulo == "Compra no crédito aprovada":
        padrao = r'Sua compra no cartão final \d+ no valor de R\$ ([\d,.]+), dia (\d{2}/\d{2}/\d{4}) às (\d{2}:\d{2}), em (.*), foi aprovada\.'
        m = re.search(padrao, texto)
        if m:
            valor = float(m.group(1).replace('.', '').replace(',', '.'))
            data = f"{m.group(2)} {m.group(3)}"
            return {
                "data": data,
                "valor": valor,
                "descricao": m.group(4).strip(),
                "operacao": "CREDITO",
                
            }
    elif titulo == "Débito C6 Tag":
        padrao = r'Você usou seu tag no dia (\d{2}/\d{2}/\d{4}) as (\d{2}:\d{2}). Valor a debitar R\$ ([\d,.]+)\. (.+?) ?\.'
        m = re.search(padrao, texto)
        if m:
            valor = float(m.group(3).replace('.', '').replace(',', '.'))
            data = f"{m.group(1)} {m.group(2)}"
            return {
                "data": data,
                "valor": valor,
                "descricao": m.group(4).strip(),
                "operacao": "TAG"
            }
    return None