# Webhook Notificações — C6 Bank

Webhook em Flask que recebe as notificações do **C6 Bank** capturadas pelo **MacroDroid** no celular, salva os dados brutos e uma versão formatada em CSV, para depois um workflow no **n8n** subir esses arquivos para o Google Drive.

Roda em Docker no servidor pessoal (hoje só o ambiente `prod` está ativo e recebendo dados; `dev` existe para testes).

## Como funciona

```mermaid
flowchart LR
    subgraph Celular
        MD[MacroDroid<br/>intercepta notificações do C6 Bank]
    end

    subgraph Servidor["Servidor (Docker)"]
        WB["Flask Webhook<br/>POST /webhook"]
        RAW["data/prod/raw/<br/>notificacoes.csv"]
        FMT["data/prod/formated/<br/>notificacoes_formatadas.csv"]
    end

    subgraph Cloud
        N8N[n8n Workflow]
        DRIVE[Google Drive]
    end

    MD -- "POST JSON<br/>Bearer WEBHOOK_TOKEN" --> WB
    WB -- "salva bruto" --> RAW
    WB -- "extrai data, valor,<br/>descrição e operação" --> FMT
    RAW --> N8N
    FMT --> N8N
    N8N --> DRIVE
```

## Formato da notificação

O MacroDroid envia um POST para `/webhook` com o header `Authorization: Bearer <WEBHOOK_TOKEN>` e um JSON:

```json
{
  "app": "C6 Bank",
  "titulo": "Compra no crédito aprovada",
  "texto": "Sua compra no cartão final 1234 no valor de R$ 1,00, dia 16/06/2025 às 12:52, em MARABRAS So Paulo BRA, foi aprovada."
}
```

Saídas:

- `data/{env}/raw/notificacoes.csv` — todas as notificações, com `timestamp, app, titulo, texto`.
- `data/{env}/formated/notificacoes_formatadas.csv` — só mensagens reconhecidas, com `data, valor, descricao, tipo_operacao` (operacões suportadas: `PIX`, `CREDITO`, `TAG`).

O parsing das mensagens acontece em `webhook_server/utils.py:15` — se o C6 mudar o texto das notificações (como ocorreu na atualização do MacroDroid em 07/07), os padrões de regex precisam ser ajustados lá.

## Rodando com Docker

```bash
docker compose up -d --build webhook-prod   # prod na porta 5000 (único ambiente ativo hoje)
docker compose up -d --build webhook-dev    # dev na porta 5001 (para testes locais)
```

O diretório `data/` é montado como volume, então os CSVs ficam no host e sobrevivem a rebuilds do container.

## Rodando local (sem Docker)

1. Instale as dependências: `poetry install`
2. Rode: `poetry run python -m webhook_server.webhook_server`

## Testes

```
poetry run pytest
```

Cobrem o parsing dos formatos de notificação (PIX, crédito, TAG) com textos reais e o comportamento do endpoint `/webhook` (autenticação, erros e gravação nos CSVs). Ao adicionar um novo formato em `parse_notification`, adicione o caso de teste correspondente em `tests/test_utils.py`.

## Configuração

| Variável de ambiente | Padrão | Descrição |
|---|---|---|
| `WEBHOOK_ENV` | `prod` | Define se grava em `data/prod` ou `data/dev` |
| `WEBHOOK_TOKEN` | `token_teste` | Token do header `Authorization` (defina no `.env`) |

## Rotas

- `POST /webhook` — recebe a notificação (exige `Bearer` token).
- `GET /ping` — health check, retorna `{"message": "Pong"}`.

## Observações

- O token e outros segredos ficam no `.env` (não versionado).
- Mensagens com título não reconhecido são salvas só no CSV bruto, com log `"Mensagem não reconhecida"`.
- O n8n lê os CSVs de `data/` e faz o upload para o Drive — o upload não é responsabilidade deste serviço.
