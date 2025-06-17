from flask import Flask, request, jsonify
import csv
import os
from datetime import datetime

app = Flask(__name__)

ENV = os.environ.get("WEBHOOK_ENV", "prod")  
CSV_FILE = f'data/{ENV}/raw/notificacoes.csv'
FORMATTED_CSV = os.environ.get('FORMATTED_CSV', f'data/{ENV}/formated/notificacoes_formatadas.csv')

if not os.path.isfile(CSV_FILE):
    with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['timestamp', 'app', 'titulo', 'texto'])

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        app_name = data.get('app', 'N/A')
        title = data.get('titulo', 'N/A')
        text = data.get('texto', 'N/A')
        timestamp = datetime.now().isoformat()

        with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, app_name, title, text])

        return jsonify({"status": "success", "message": "Dados salvos"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def main():
    port = int(os.environ.get('PORT', 5000 if ENV == "prod" else 5001))
    app.run(host='0.0.0.0', port=port, debug=port==5001)

if __name__ == "__main__":
    main()

