from flask import Flask, request, jsonify
import csv
import os
from datetime import datetime
from webhook_server import utils
import logging

logging.basicConfig(level=logging.INFO)

ENV = os.environ.get("WEBHOOK_ENV", "prod")
TOKEN = os.environ.get('WEBHOOK_TOKEN', 'token_teste')
CSV_FILE = f'data/{ENV}/raw/notificacoes.csv'
FORMATTED_CSV = f'data/{ENV}/formated/notificacoes_formatadas.csv'



def create_app():
    app = Flask(__name__)

    for path, header in (
        (CSV_FILE, ['timestamp', 'app', 'titulo', 'texto']),
        (FORMATTED_CSV, ['data', 'valor', 'descricao', 'tipo_operacao']),
    ):
        if not utils.check_file_exists(path):
            with open(path, mode='w', newline='', encoding='utf-8') as file:
                csv.writer(file).writerow(header)

    @app.route('/ping', methods=['GET'])
    def ping():
        return jsonify({"status": "success", "message": "Pong"}), 200

    @app.route('/webhook', methods=['POST'])
    def webhook():
        logging.info(f"Requisição recebida de {request.remote_addr}")
        auth = request.headers.get('Authorization')
        if not auth or auth != f'Bearer {TOKEN}':
            return jsonify({'status': 'error', 'message': 'Não autorizado'}), 401
        try:
            data = request.get_json()
            app_name = data['app']
            title = data['titulo']
            text = data['texto']
            timestamp = datetime.now().isoformat()

            utils.append_csv(CSV_FILE, {
                "timestamp": timestamp,
                "app": app_name,
                "titulo": title,
                "texto": text
            })

            logging.info(f"Salvando RAW : {title}")
            format_msg = utils.parse_notification(title, text)
            if format_msg:
                logging.info(f"Salvando Formatada: {format_msg['operacao']}")
                utils.append_csv(FORMATTED_CSV, format_msg)
            else:
                logging.info("Mensagem não reconhecida")

            return jsonify({"status": "success", "message": "Dados salvos"}), 200
        except KeyError as e:
            return jsonify({"status": "error", "message": f"Campo obrigatório ausente: {e}"}), 400
        except Exception as e:
            logging.exception("Erro ao processar webhook: %s", e)
            return jsonify({"status": "error", "message": str(e)}), 500
    
    return app

def main():
    app = create_app()
    port = 5000
    app.run(host='0.0.0.0', port=port, debug=(ENV != "prod"))

if __name__ == "__main__":
    main()

