# Webhook Python

Um webhook simples e robusto para receber notificações da aplicação selecionada (ex: notificações bancárias), salvar os dados brutos, usando Flask.

## Funcionalidades

- Recebe notificações via POST `/webhook`.
- Salva todas as notificações brutas em `notificacoes.csv`.

## Como usar

1. Instale dependências:
    ```
   poetry add flask
    ```

2. Rode o servidor:
    ```
    poetry run python webhook_server.py
    ```

3. Faça uma requisição POST para `http://<IP>:5000/webhook` com um JSON:
    ```json
    {
      "app": "C6 Bank",
      "titulo": "Compra no crédito aprovada",
      "texto": "Sua compra no cartão final 1234 no valor de R$ 1,00, dia 16/06/2025 às 12:52, em MARABRAS So Paulo BRA, foi aprovada."
    }
    ```


## Configuração

- Arquivo CSV pode ser configurado por variável de ambiente `CSV_FILE`.
- Porta por `PORT`.

---