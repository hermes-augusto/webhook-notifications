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
    for titulo, texto in (("Você recebeu um Pix", TEXTO_PIX), ("Compra no crédito aprovada", TEXTO_CREDITO)):
        resposta = client.post(
            "/webhook",
            headers=auth(),
            json={"app": "C6 Bank", "titulo": titulo, "texto": texto},
        )
        assert resposta.status_code == 200
    assert len(ler_linhas(ws.CSV_FILE)) == 3
    assert len(ler_linhas(ws.FORMATTED_CSV)) == 3


def test_webhook_notificacao_duplicada_nao_grava_novamente(client):
    payload = {"app": "C6 Bank", "titulo": "Você recebeu um Pix", "texto": TEXTO_PIX}
    r1 = client.post("/webhook", headers=auth(), json=payload)
    r2 = client.post("/webhook", headers=auth(), json=payload)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert "duplicada" in r2.get_json()["message"]
    assert len(ler_linhas(ws.CSV_FILE)) == 2
    assert len(ler_linhas(ws.FORMATTED_CSV)) == 2


def test_webhook_notificacoes_diferentes_gravam_normalmente(client):
    for texto in (TEXTO_PIX, TEXTO_CREDITO):
        resposta = client.post(
            "/webhook",
            headers=auth(),
            json={"app": "C6 Bank", "titulo": "Qualquer", "texto": texto},
        )
        assert resposta.status_code == 200
    assert len(ler_linhas(ws.CSV_FILE)) == 3


def test_stats_conta_recebidas_parseadas_e_duplicatas(client):
    assert client.get("/stats").get_json()["recebidas"] == 0

    payload = {"app": "C6 Bank", "titulo": "Você recebeu um Pix", "texto": TEXTO_PIX}
    client.post("/webhook", headers=auth(), json=payload)
    client.post("/webhook", headers=auth(), json=payload)
    client.post(
        "/webhook",
        headers=auth(),
        json={"app": "C6 Bank", "titulo": "Agendamento processado", "texto": "texto novo do banco"},
    )

    stats = client.get("/stats").get_json()
    assert stats["recebidas"] == 3
    assert stats["parseadas"] == 1
    assert stats["nao_reconhecidas"] == 1
    assert stats["duplicatas_ignoradas"] == 1
    assert stats["dias_sem_recebimento"] == 0.0
    assert stats["alerta_drift"] is False
    assert stats["alerta_silencio"] is False
    # menos de STATS_MIN_RECEBIDAS recebidas: taxa ainda não é significativa
    assert stats["taxa_reconhecimento_pct"] is None
    assert "insuficiente" in stats["taxa_reconhecimento"]


def test_stats_alerta_drift_quando_taxa_abaixo_do_minimo(client):
    for i in range(10):
        client.post(
            "/webhook",
            headers=auth(),
            json={"app": "C6 Bank", "titulo": f"título novo {i}", "texto": f"texto que não casou {i}"},
        )
    stats = client.get("/stats").get_json()
    assert stats["recebidas"] == 10
    assert stats["taxa_reconhecimento_pct"] == 0.0
    assert stats["alerta_drift"] is True


def test_stats_alerta_silencio_apos_janela_sem_recebimento(client, monkeypatch):
    client.post(
        "/webhook",
        headers=auth(),
        json={"app": "C6 Bank", "titulo": "Você recebeu um Pix", "texto": TEXTO_PIX},
    )
    assert client.get("/stats").get_json()["alerta_silencio"] is False

    from datetime import datetime as datetime_real, timedelta

    class DataFake(datetime_real):
        @classmethod
        def now(cls):
            return datetime_real.now() + timedelta(days=8)

    monkeypatch.setattr(ws, "datetime", DataFake)
    stats = client.get("/stats").get_json()
    assert stats["alerta_silencio"] is True
    assert stats["dias_sem_recebimento"] > 7
