from flask import Flask, request, jsonify
import csv
import os
from datetime import datetime
from typing import Optional, Dict
import re

app = Flask(__name__)

ENV = os.environ.get("WEBHOOK_ENV", "prod")

CSV_FILE = f'data/{ENV}/raw/notificacoes.csv'
FORMATTED_CSV = f'data/{ENV}/formated/notificacoes_formatadas.csv'


def check_file_exists(file_path: str) -> bool:
    if not os.path.isdir(os.path.dirname(file_path)):
        os.makedirs(os.path.dirname(file_path))
    return os.path.isfile(file_path)

def append_csv(file_path: str, data: list) -> None:
    with open(file_path, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(data)

def parse_notification(titulo: str, texto: str):
    if titulo == "Você recebeu um Pix":
        padrao = r'Pix recebido no valor de R\$ ([\d,.]+), (de .+?), em (\d{2}/\d{2}/\d{4})\.'
        m = re.search(padrao, texto)
        if m:
            valor = float(m.group(1).replace('.', '').replace(',', '.'))
            return {
                "operacao": "PIX",
                "valor": valor,
                "descricao": m.group(2),
                "data": m.group(3)
            }
    elif titulo == "Compra no crédito aprovada":
        padrao = r'Sua compra no cartão final \d+ no valor de R\$ ([\d,.]+), dia (\d{2}/\d{2}/\d{4}) às (\d{2}:\d{2}), em (.*), foi aprovada\.'
        m = re.search(padrao, texto)
        if m:
            valor = float(m.group(1).replace('.', '').replace(',', '.'))
            data = f"{m.group(2)} {m.group(3)}"
            return {
                "operacao": "CREDITO",
                "valor": valor,
                "descricao": m.group(4).strip(),
                "data": data
            }
    elif titulo == "Débito C6 Tag":
        padrao = r'Você usou seu tag no dia (\d{2}/\d{2}/\d{4}) as (\d{2}:\d{2}). Valor a debitar R\$ ([\d,.]+)\. (.+) \.'
        m = re.search(padrao, texto)
        if m:
            valor = float(m.group(3).replace('.', '').replace(',', '.'))
            data = f"{m.group(1)} {m.group(2)}"
            return {
                "operacao": "TAG",
                "valor": valor,
                "descricao": m.group(4).strip(),
                "data": data
            }
    return None


if not check_file_exists(CSV_FILE):
    with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['timestamp', 'app', 'titulo', 'texto'])

if not check_file_exists(FORMATTED_CSV):
    with open(FORMATTED_CSV, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['data', 'valor', 'tipo_operacao', 'descricao'])

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        app_name = data['app']
        title = data['titulo']
        text = data['texto']
        timestamp = datetime.now().isoformat()
        format_msg = parse_notification(title, text)
        print(format_msg)
        with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, app_name, title, text])

        return jsonify({"status": "success", "message": "Dados salvos"}), 200
    except KeyError as e:
        return jsonify({"status": "error", "message": f"Campo obrigatório ausente: {e}"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def main():
    port = int(os.environ.get('PORT', 5000 if ENV == "prod" else 5001))
    app.run(host='0.0.0.0', port=port, debug=port==5001)

if __name__ == "__main__":
    main()

