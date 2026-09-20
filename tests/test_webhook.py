import csv

import pytest

from webhook_server import webhook_server as ws

TOKEN_TESTE = "token-teste"

TEXTO_PIX = "Pix recebido no valor de R$ 50,00, de João Silva, em 20/09/2026."
TEXTO_CREDITO = (
    "Sua compra no cartão final 5038 no valor de R$ 88,53, dia 16/06/2025 às 20:42, "
    "em ASSB COMERCIO VAREJIST SAO PAULO     BRA, foi aprovada."
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(ws, "CSV_FILE", str(tmp_path / "raw" / "notificacoes.csv"))
    monkeypatch.setattr(ws, "FORMATTED_CSV", str(tmp_path / "formated" / "notificacoes_formatadas.csv"))
    monkeypatch.setattr(ws, "TOKEN", TOKEN_TESTE)
    app = ws.create_app()
    app.config["TESTING"] = True
    return app.test_client()


def auth():
    return {"Authorization": f"Bearer {TOKEN_TESTE}"}


def ler_linhas(caminho):
    with open(caminho, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def test_ping(client):
    resposta = client.get("/ping")
    assert resposta.status_code == 200
    assert resposta.get_json()["message"] == "Pong"


def test_webhook_sem_token_retorna_401(client):
    resposta = client.post("/webhook", json={"app": "C6 Bank", "titulo": "x", "texto": "y"})
    assert resposta.status_code == 401
    assert resposta.get_json()["status"] == "error"


def test_webhook_token_errado_retorna_401(client):
    resposta = client.post(
        "/webhook",
        headers={"Authorization": "Bearer errado"},
        json={"app": "C6 Bank", "titulo": "x", "texto": "y"},
    )
    assert resposta.status_code == 401


def test_webhook_mensagem_reconhecida_grava_raw_e_formatado(client):
    resposta = client.post(
        "/webhook",
        headers=auth(),
        json={"app": "C6 Bank", "titulo": "Compra no crédito aprovada", "texto": TEXTO_CREDITO},
    )
    assert resposta.status_code == 200

    raw = ler_linhas(ws.CSV_FILE)
    assert len(raw) == 2
    assert raw[0] == ["timestamp", "app", "titulo", "texto"]
    assert raw[1][1:] == ["C6 Bank", "Compra no crédito aprovada", TEXTO_CREDITO]

    formatado = ler_linhas(ws.FORMATTED_CSV)
    assert len(formatado) == 2
    assert formatado[1] == ["16/06/2025 20:42", "88.53", "ASSB COMERCIO VAREJIST SAO PAULO     BRA", "CREDITO"]


def test_webhook_titulo_desconhecido_grava_apenas_raw(client):
    resposta = client.post(
        "/webhook",
        headers=auth(),
        json={"app": "C6 Bank", "titulo": "Agendamento processad", "texto": "algum texto novo"},
    )
    assert resposta.status_code == 200
    assert len(ler_linhas(ws.CSV_FILE)) == 2
    assert len(ler_linhas(ws.FORMATTED_CSV)) == 1


def test_webhook_campo_ausente_retorna_400_sem_gravar(client):
    resposta = client.post("/webhook", headers=auth(), json={"app": "C6 Bank"})
    assert resposta.status_code == 400
    assert "Campo obrigatório ausente" in resposta.get_json()["message"]
    assert len(ler_linhas(ws.CSV_FILE)) == 1


def test_webhook_duas_notificacoes_acumulam_linhas(client):
    for _ in range(2):
        resposta = client.post(
            "/webhook",
            headers=auth(),
            json={"app": "C6 Bank", "titulo": "Você recebeu um Pix", "texto": TEXTO_PIX},
        )
        assert resposta.status_code == 200
    assert len(ler_linhas(ws.CSV_FILE)) == 3
    assert len(ler_linhas(ws.FORMATTED_CSV)) == 3
