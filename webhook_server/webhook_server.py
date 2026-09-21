from flask import Flask, request, jsonify
import csv
import os
from datetime import datetime
from webhook_server import utils
import logging

logging.basicConfig(level=logging.INFO)

ENV = os.environ.get("WEBHOOK_ENV", "prod")
TOKEN = os.environ.get('WEBHOOK_TOKEN', 'token_teste')
DEDUP_WINDOW_MINUTES = int(os.environ.get('DEDUP_WINDOW_MINUTES', '10'))
STATS_MIN_RECEBIDAS = int(os.environ.get('STATS_MIN_RECEBIDAS', '10'))
STATS_TAXA_MINIMA_PCT = float(os.environ.get('STATS_TAXA_MINIMA_PCT', '50'))
STATS_SILENCIO_DIAS = float(os.environ.get('STATS_SILENCIO_DIAS', '7'))
CSV_FILE = f'data/{ENV}/raw/notificacoes.csv'
FORMATTED_CSV = f'data/{ENV}/formated/notificacoes_formatadas.csv'



def create_app():
    app = Flask(__name__)
    filtro = utils.FiltroDuplicatas(DEDUP_WINDOW_MINUTES)
    contadores = {
        "inicio": datetime.now(),
        "recebidas": 0,
        "parseadas": 0,
        "nao_reconhecidas": 0,
        "duplicatas_ignoradas": 0,
        "ultima_recebida": None,
    }

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

    @app.route('/stats', methods=['GET'])
    def stats():
        agora = datetime.now()
        ultima = contadores['ultima_recebida'] or contadores['inicio']
        dias_sem = round((agora - ultima).total_seconds() / 86400, 2)
        recebidas = contadores['recebidas']
        taxa = (contadores['parseadas'] / recebidas * 100) if recebidas else 0.0
        armado = recebidas >= STATS_MIN_RECEBIDAS
        return jsonify({
            "inicio_contagem": contadores['inicio'].isoformat(),
            "recebidas": recebidas,
            "parseadas": contadores['parseadas'],
            "nao_reconhecidas": contadores['nao_reconhecidas'],
            "duplicatas_ignoradas": contadores['duplicatas_ignoradas'],
            "ultima_recebida": ultima.isoformat(),
            "dias_sem_recebimento": dias_sem,
            "taxa_reconhecimento": f"{taxa:.1f}%" if armado else f"insuficiente (min. {STATS_MIN_RECEBIDAS} recebidas)",
            "taxa_reconhecimento_pct": round(taxa, 1) if armado else None,
            "alerta_drift": armado and taxa < STATS_TAXA_MINIMA_PCT,
            "alerta_silencio": dias_sem > STATS_SILENCIO_DIAS,
            "aviso": "contadores zeram a cada restart do container",
        }), 200

    @app.route('/webhook', methods=['POST'])
    def webhook():
        logging.info("evento=requisicao_recebida remote_addr=%s", request.remote_addr)
        auth = request.headers.get('Authorization')
        if not auth or auth != f'Bearer {TOKEN}':
            logging.info("evento=autenticacao_falhou remote_addr=%s", request.remote_addr)
            return jsonify({'status': 'error', 'message': 'Não autorizado'}), 401
        try:
            data = request.get_json()
            app_name = data['app']
            title = data['titulo']
            text = data['texto']
            contadores['recebidas'] += 1
            contadores['ultima_recebida'] = datetime.now()

            if filtro.eh_duplicata(app_name, title, text):
                contadores['duplicatas_ignoradas'] += 1
                logging.info("evento=notificacao_duplicada_ignorada titulo=%r", title)
                return jsonify({"status": "success", "message": "Notificação duplicada ignorada"}), 200

            timestamp = datetime.now().isoformat()

            utils.append_csv(CSV_FILE, {
                "timestamp": timestamp,
                "app": app_name,
                "titulo": title,
                "texto": text
            })

            logging.info("evento=notificacao_gravada tabela=raw titulo=%r", title)
            format_msg = utils.parse_notification(title, text)
            if format_msg:
                contadores['parseadas'] += 1
                logging.info("evento=notificacao_gravada tabela=formatada operacao=%s", format_msg['operacao'])
                utils.append_csv(FORMATTED_CSV, format_msg)
            else:
                contadores['nao_reconhecidas'] += 1
                logging.info("evento=notificacao_nao_reconhecida titulo=%r app=%r", title, app_name)

            return jsonify({"status": "success", "message": "Dados salvos"}), 200
        except KeyError as e:
            return jsonify({"status": "error", "message": f"Campo obrigatório ausente: {e}"}), 400
        except Exception as e:
            logging.exception("evento=erro_webhook detalhe=%s", e)
            return jsonify({"status": "error", "message": str(e)}), 500
    
    return app

def main():
    app = create_app()
    port = 5000
    app.run(host='0.0.0.0', port=port, debug=(ENV != "prod"))

if __name__ == "__main__":
    main()

