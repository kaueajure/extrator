from __future__ import annotations

import unittest
from unittest.mock import patch

import httpx

from src.servicos.webrp import ClienteWebRP


class _ClienteSequencial:
    def __init__(self, respostas: list[object]) -> None:
        self.respostas = respostas
        self.chamadas = 0

    def request(self, metodo: str, url: str, **_kwargs):
        resposta = self.respostas[self.chamadas]
        self.chamadas += 1
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


class WebRPRetryTest(unittest.TestCase):
    def _cliente(self, respostas: list[object]) -> tuple[ClienteWebRP, _ClienteSequencial]:
        cliente = ClienteWebRP("https://webriopreto.com")
        cliente.cliente.close()
        falso = _ClienteSequencial(respostas)
        cliente.cliente = falso  # type: ignore[assignment]
        return cliente, falso

    @patch("src.servicos.webrp.time.sleep", return_value=None)
    def test_repete_erro_temporario_do_servidor(self, _sleep) -> None:
        requisicao = httpx.Request("GET", "https://webriopreto.com/api/admin/leads")
        cliente, falso = self._cliente(
            [
                httpx.Response(503, request=requisicao),
                httpx.Response(200, request=requisicao, json={"leads": []}),
            ]
        )
        resposta = cliente._requisitar("GET", str(requisicao.url))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(falso.chamadas, 2)

    @patch("src.servicos.webrp.time.sleep", return_value=None)
    def test_repete_timeout_de_rede(self, _sleep) -> None:
        requisicao = httpx.Request("GET", "https://webriopreto.com/api/admin/leads")
        cliente, falso = self._cliente(
            [
                httpx.ReadTimeout("demorou", request=requisicao),
                httpx.Response(200, request=requisicao, json={"leads": []}),
            ]
        )
        resposta = cliente._requisitar("GET", str(requisicao.url))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(falso.chamadas, 2)


if __name__ == "__main__":
    unittest.main()
