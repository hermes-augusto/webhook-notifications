import pytest

from webhook_server import utils

TEXTO_PIX = "Pix recebido no valor de R$ 50,00, de João Silva, em 20/09/2026."
TEXTO_PIX_CPF = (
    "Pix recebido no valor de R$ 0,01, de Hermes Augusto Barboza, "
    "CPF ***.554.858-**, em 16/06/2025."
)
TEXTO_CREDITO = (
    "Sua compra no cartão final 5038 no valor de R$ 88,53, dia 16/06/2025 às 20:42, "
    "em ASSB COMERCIO VAREJIST SAO PAULO     BRA, foi aprovada."
)
TEXTO_CREDITO_MILHAR = (
    "Sua compra no cartão final 1234 no valor de R$ 1.234,56, dia 01/01/2026 às 10:00, "
    "em LOJA TESTE SAO PAULO BRA, foi aprovada."
)
TEXTO_TAG = (
    "Você usou seu tag no dia 16/06/2025 as 18:55. Valor a debitar R$ 36,00. "
    "Estacionamento RUA TREZE DE MAIO 19470 SAO PAULO SP ."
)


@pytest.mark.parametrize(
    "titulo, texto, esperado",
    [
        (
            "Você recebeu um Pix",
            TEXTO_PIX,
            {"data": "20/09/2026", "valor": 50.0, "descricao": "de João Silva", "operacao": "PIX"},
        ),
        (
            "Você recebeu um Pix",
            TEXTO_PIX_CPF,
            {
                "data": "16/06/2025",
                "valor": 0.01,
                "descricao": "de Hermes Augusto Barboza, CPF ***.554.858-**",
                "operacao": "PIX",
            },
        ),
        (
            "Compra no crédito aprovada",
            TEXTO_CREDITO,
            {
                "data": "16/06/2025 20:42",
                "valor": 88.53,
                "descricao": "ASSB COMERCIO VAREJIST SAO PAULO     BRA",
                "operacao": "CREDITO",
            },
        ),
        (
            "Compra no crédito aprovada",
            TEXTO_CREDITO_MILHAR,
            {
                "data": "01/01/2026 10:00",
                "valor": 1234.56,
                "descricao": "LOJA TESTE SAO PAULO BRA",
                "operacao": "CREDITO",
            },
        ),
        (
            "Débito C6 Tag",
            TEXTO_TAG,
            {
                "data": "16/06/2025 18:55",
                "valor": 36.0,
                "descricao": "Estacionamento RUA TREZE DE MAIO 19470 SAO PAULO SP",
                "operacao": "TAG",
            },
        ),
    ],
)
def test_parse_notification_reconhecida(titulo, texto, esperado):
    assert utils.parse_notification(titulo, texto) == esperado


@pytest.mark.parametrize(
    "titulo, texto",
    [
        ("Título desconhecido", TEXTO_PIX),
        ("Você recebeu um Pix", "texto que não segue o padrão de nenhuma notificação"),
        ("Compra no crédito aprovada", "Sua compra foi aprovada."),
    ],
)
def test_parse_notification_nao_reconhecida(titulo, texto):
    assert utils.parse_notification(titulo, texto) is None


def test_check_file_exists_cria_apenas_o_diretorio(tmp_path):
    alvo = tmp_path / "sub" / "pasta" / "arquivo.csv"
    assert utils.check_file_exists(str(alvo)) is False
    assert alvo.parent.is_dir()
    assert not alvo.exists()
    assert utils.check_file_exists(str(alvo)) is False


def test_append_csv_grava_linha(tmp_path):
    alvo = tmp_path / "arquivo.csv"
    utils.append_csv(str(alvo), {"a": 1, "b": "dois"})
    assert alvo.read_text(encoding="utf-8").strip() == "1,dois"
