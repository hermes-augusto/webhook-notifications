import csv
import hashlib
import os
import re
from collections import deque
from datetime import datetime, timedelta

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

class FiltroDuplicatas:
    """Ignora notificações idênticas recebidas dentro da janela (retries do MacroDroid).

    Limitação: o payload não tem ID único, então o dedup é por conteúdo exato em
    memória — reiniciar o container zera a janela e transações legítimas repetidas
    dentro dela também são ignoradas (por isso a janela deve ser curta).
    """

    def __init__(self, janela_minutos: int = 10):
        self.janela = timedelta(minutes=janela_minutos)
        self._vistos = deque()

    def _chave(self, app: str, titulo: str, texto: str) -> str:
        return hashlib.sha1(f"{app}|{titulo}|{texto}".encode('utf-8')).hexdigest()

    def eh_duplicata(self, app: str, titulo: str, texto: str, agora: datetime = None) -> bool:
        agora = agora or datetime.now()
        corte = agora - self.janela
        while self._vistos and self._vistos[0][1] < corte:
            self._vistos.popleft()
        chave = self._chave(app, titulo, texto)
        if any(k == chave for k, _ in self._vistos):
            return True
        self._vistos.append((chave, agora))
        return False
