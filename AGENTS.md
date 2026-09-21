# AGENTS.md — Instruções para agentes de IA

## Visão geral do projeto

Serviço único e pequeno em **Python + Flask**, gerenciado com **Poetry** (`pyproject.toml` + `poetry.lock`). Roda em Docker no servidor pessoal.

**Foco central**: capturar as notificações do C6 Bank que chegam no celular e transformá-las em dados estruturados de gasto/recebimento. A cadeia é: MacroDroid (celular) → POST `/webhook` (Flask) → CSVs em `data/{env}/` → workflow n8n → Google Drive. Qualquer mudança deve preservar essa cadeia ponta a ponta.

Hoje só o ambiente `prod` está ativo e recebendo dados (container `webhook-flask`, porta 5000). O `dev` (porta 5001, container `webhook-flask-dev`) existe para testes locais.

O ponto frágil do sistema é o parsing em `webhook_server/utils.py` (`parse_notification`): o C6 Bank e o MacroDroid mudam o texto das notificações com o tempo, e quando mudam os regex param de casar e as mensagens caem só no CSV bruto com log `"Mensagem não reconhecida"`.

## Estrutura de código

```
webhook_server/
├── __init__.py            # vazio
├── webhook_server.py      # factory create_app(), rotas /ping e /webhook, main()
└── utils.py               # CSV (check_file_exists, append_csv) e parse_notification
tests/
├── test_utils.py          # parsing (PIX, CREDITO, TAG) + helpers de CSV
└── test_webhook.py        # endpoint /webhook (auth, 400, gravação, acúmulo)
```

- O app usa a **factory pattern** (`create_app()`) — manter novas rotas dentro dela, não no módulo global.
- Lógica auxiliar (CSV, parsing) vai em `webhook_server/utils.py`, não misturada com as rotas.
- Criação dos CSVs (header) acontece dentro de `create_app()` — importar o módulo não grava em `data/`, o que facilita os testes com `tmp_path` + monkeypatch.

## Comandos

### Escopo de arquivo (preferido — feedback rápido)

```bash
poetry run pytest tests/test_utils.py                          # um arquivo
poetry run pytest tests/test_utils.py::test_append_csv_grava_linha  # um teste
poetry run pytest -k "pix"                                     # por nome
```

### Suíte completa e execução local

```bash
poetry run pytest                                     # todos os testes — devem passar antes de entregar
poetry run python -m webhook_server.webhook_server    # sobe local na porta 5000
WEBHOOK_ENV=dev poetry run python -m webhook_server.webhook_server  # sobe apontando p/ data/dev
```

### Docker

```bash
docker compose up -d --build webhook-prod   # prod na porta 5000
docker compose up -d --build webhook-dev    # dev na porta 5001
```

## Rotas e contrato

- `POST /webhook` — recebe JSON `{app, titulo, texto}` com header `Authorization: Bearer <WEBHOOK_TOKEN>`; retorna 200 e grava no CSV bruto, e no formatado se o título for reconhecido. Duplicatas idênticas dentro de `DEDUP_WINDOW_MINUTES` são ignoradas com 200. 401 sem token/errado; 400 com campo ausente; 500 com log de exceção.
- `GET /stats` — contadores em memória (`recebidas`, `parseadas`, `nao_reconhecidas`, `duplicatas_ignoradas`, `taxa_reconhecimento`); zeram a cada restart. Alerta barato de drift de formato.
- `GET /ping` — health check, retorna `{"status": "success", "message": "Pong"}`.

Saídas (por ambiente, definido por `WEBHOOK_ENV`):

- `data/{env}/raw/notificacoes.csv` — todas as notificações: `timestamp, app, titulo, texto`.
- `data/{env}/formated/notificacoes_formatadas.csv` — só mensagens reconhecidas: `data, valor, descricao, tipo_operacao` (operações: `PIX`, `CREDITO`, `TAG`).

## Configuração

| Variável de ambiente | Padrão | Descrição |
|---|---|---|
| `WEBHOOK_ENV` | `prod` | Define se grava em `data/prod` ou `data/dev` |
| `WEBHOOK_TOKEN` | `token_teste` | Token do header `Authorization` (valor real no `.env`) |
| `DEDUP_WINDOW_MINUTES` | `10` | Janela do dedup de notificações idênticas (minutos) |

O `dockerfile` fixa `WEBHOOK_ENV=prod` e expõe a porta 5000. O `docker-compose.yml` monta `./data/{env}` como volume, então os CSVs ficam no host e sobrevivem a rebuilds.

## Convenções de código

- Logs em português via `logging`, no formato estruturado `evento=chave=valor` (ex.: `evento=notificacao_gravada tabela=raw titulo=%r`). Em handlers de exceção usar `logging.exception("evento=erro detalhe=%s", e)` — nunca passar `str(e)` como segundo argumento posicional, pois quebra a formatação.
- Ambientes separados por `WEBHOOK_ENV` (`prod` → `data/prod`, porta 5000; `dev` → `data/dev`, porta 5001). Toda mudança deve funcionar nos dois.
- Novos formatos de notificação: seguir o padrão dos `elif` existentes em `parse_notification` com padrão nomeado em nível de módulo (`PADRAO_*` com exemplo de texto real em comentário), retornando dict com chaves `data, valor, descricao, operacao` nessa ordem.
- Não adicionar dependências sem necessidade real; o projeto usa apenas Flask (pytest em dev, fixado em `<9` porque o 9 exige Python ≥3.10 e o projeto aceita 3.9).

## Testes

- Rodar `poetry run pytest` antes de entregar qualquer mudança — todos devem passar.
- `tests/test_utils.py` cobre os 3 formatos com textos reais (incluindo valores com separador de milhar e Pix com CPF mascarado). Ao adicionar parsing novo, adicionar o caso com o **texto real da notificação** aqui — nunca quebrar os formatos existentes.
- `tests/test_webhook.py` usa `tmp_path` + monkeypatch (não grava em `data/`) e cobre auth (401), 400 sem gravação e acúmulo de linhas.

## Permissões

### Liberado sem perguntar
- Ler e editar código e testes.
- Rodar pytest (arquivo isolado ou suíte completa).
- Subir o servidor local com `WEBHOOK_ENV=dev` e testar com curl/cliente de teste (grava só em `data/dev`).

### Sempre pedir autorização antes
- **`git push`, `git commit` ou qualquer operação git que altere o remoto.**
- **Qualquer comando Docker que pare ou reinicie o container `webhook-flask` de prod** (`docker compose down`, rebuild de prod, etc.) — o serviço recebe notificações do banco em tempo real e precisa ficar no ar.
- Instalar dependências novas (`poetry add`).
- Mexer no `.env`, no `docker-compose.yml` de prod ou nos dados de `data/prod/`.
- Deletar arquivos ou diretórios.

## Segurança

- Nunca commitar nem expor o `.env` (segredos: `WEBHOOK_TOKEN`); nunca logar valores de segredos.
- Nunca commitar `data/` (já está no `.gitignore`).
- O n8n lê os CSVs de `data/` e faz o upload para o Google Drive — o upload não é responsabilidade deste serviço.
- Mensagens do usuário são em português — responder e documentar em português.

## Quando travar, perguntar

- Se testes falharem de forma repetida após 2-3 tentativas de correção, parar e pedir revisão humana.
- Se o texto de uma notificação real não casar com nenhum padrão conhecido, pedir o texto completo ao usuário em vez de adivinhar o regex.
- Se uma mudança exigir downtime do prod, avisar antes e propor o melhor momento.

## Manutenção deste arquivo

Este arquivo é **vivo**: sempre que houver mudança relevante de comportamento, arquitetura, configuração ou decisão (novo formato de notificação, novo ambiente, mudança de fluxo, etc.), atualizá-lo junto com a mudança. O histórico do que foi feito vive no **git log** — não duplicá-lo aqui; este arquivo contém só instruções acionáveis.
