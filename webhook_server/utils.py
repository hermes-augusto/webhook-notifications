import csv
import os
import re

# Textos reais que cada padrão deve casar (C6 Bank):
#   "Pix recebido no valor de R$ 50,00, de João Silva, em 20/09/2026."
PADRAO_PIX = re.compile(
    r'Pix recebido no valor de R\$ ([\d,.]+), (de .+?), em (\d{2}/\d{2}/\d{4})\.'
)
#   "Sua compra no cartão final 5038 no valor de R$ 88,53, dia 16/06/2025 às 20:42, em ASSB COMERCIO VAREJIST SAO PAULO     BRA, foi aprovada."
PADRAO_CREDITO = re.compile(
    r'Sua compra no cartão final [\d*]+ no valor de R\$ ([\d,.]+), dia (\d{2}/\d{2}/\d{4}) às (\d{2}:\d{2}), em (.*), foi aprovada\.'
)
#   "Você usou seu tag no dia 16/06/2025 as 18:55. Valor a debitar R$ 36,00. Estacionamento RUA TREZE DE MAIO 19470 SAO PAULO SP ."
#   "Você usou seu tag no dia 30/06/2025 as 08:10. Valor a debitar R$ 3,80. Pedágio SP280 180 OESTE OSASCO  SP."
PADRAO_TAG = re.compile(
    r'Você usou seu tag no dia (\d{2}/\d{2}/\d{4}) as (\d{2}:\d{2})\. Valor a debitar R\$ ([\d,.]+)\. (.+?) ?\.'
)

def check_file_exists(file_path: str) -> bool:
    if not os.path.isdir(os.path.dirname(file_path)):
        os.makedirs(os.path.dirname(file_path))
    return os.path.isfile(file_path)

def append_csv(file_path: str, data: dict) -> None:
    with open(file_path, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(data.values())

def _valor(texto: str) -> float:
    return float(texto.replace('.', '').replace(',', '.'))

def parse_notification(titulo: str, texto: str):
    if titulo == "Você recebeu um Pix":
        m = PADRAO_PIX.search(texto)
        if m:
            return {
                "data": m.group(3),
                "valor": _valor(m.group(1)),
                "descricao": m.group(2),
                "operacao": "PIX",
            }
    elif titulo == "Compra no crédito aprovada":
        m = PADRAO_CREDITO.search(texto)
        if m:
            return {
                "data": f"{m.group(2)} {m.group(3)}",
                "valor": _valor(m.group(1)),
                "descricao": m.group(4).strip(),
                "operacao": "CREDITO",
            }
    elif titulo == "Débito C6 Tag":
        m = PADRAO_TAG.search(texto)
        if m:
            return {
                "data": f"{m.group(1)} {m.group(2)}",
                "valor": _valor(m.group(3)),
                "descricao": m.group(4).strip(),
                "operacao": "TAG"
            }
    return None
