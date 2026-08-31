from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.servicos.atualizacoes import (
    _interpretar,
    _nome_download,
    _partes_versao,
    _selecionar_asset,
    baixar_atualizacao,
)


class _RespostaDownloadFake:
    headers = {"content-length": "6"}

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        pass

    def raise_for_status(self) -> None:
        pass

    def iter_bytes(self, chunk_size: int):
        del chunk_size
        yield b"abc"
        yield b"123"


class _ClienteDownloadFake:
    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        pass

    def stream(self, *_args, **_kwargs):
        return _RespostaDownloadFake()


class AtualizacoesTest(unittest.TestCase):
    def test_compara_versoes_sem_ordenacao_lexicografica(self) -> None:
        self.assertGreater(_partes_versao("v1.10.0"), _partes_versao("1.9.9"))

    def test_interpreta_api_webrp_e_github(self) -> None:
        self.assertEqual(
            _interpretar({"versao": "1.3.0", "url_download": "https://exemplo/arquivo"}),
            ("1.3.0", "https://exemplo/arquivo"),
        )
        self.assertEqual(
            _interpretar({"tag_name": "v1.3.1", "html_url": "https://github/release"}),
            ("1.3.1", "https://github/release"),
        )

    def test_seleciona_instalador_correto_para_o_sistema(self) -> None:
        dados = {
            "assets": [
                {
                    "name": "WebRP-Extrator-x86_64.AppImage",
                    "browser_download_url": "https://exemplo/app.AppImage",
                },
                {
                    "name": "WebRP-Extrator_amd64.deb",
                    "browser_download_url": "https://exemplo/app.deb",
                },
                {
                    "name": "WebRP-Extrator-Setup.exe",
                    "browser_download_url": "https://exemplo/app.exe",
                },
            ]
        }

        self.assertEqual(
            _selecionar_asset(dados, "linux"),
            ("https://exemplo/app.deb", "WebRP-Extrator_amd64.deb"),
        )
        self.assertEqual(
            _selecionar_asset(dados, "win32"),
            ("https://exemplo/app.exe", "WebRP-Extrator-Setup.exe"),
        )

    def test_higieniza_nome_do_download(self) -> None:
        self.assertEqual(
            _nome_download("https://exemplo/arquivo.deb", "WebRP:Extrator?.deb"),
            "WebRP_Extrator_.deb",
        )

    @patch("src.servicos.atualizacoes.httpx.Client", return_value=_ClienteDownloadFake())
    def test_baixa_instalador_com_progresso(self, _cliente) -> None:
        progresso: list[tuple[int, int]] = []
        with tempfile.TemporaryDirectory() as temporario:
            caminho = baixar_atualizacao(
                "https://exemplo/arquivo.deb",
                Path(temporario),
                "WebRP-Extrator.deb",
                lambda recebido, total: progresso.append((recebido, total)),
            )

            self.assertEqual(caminho.read_bytes(), b"abc123")
            self.assertEqual(progresso, [(3, 6), (6, 6)])
            self.assertFalse((Path(temporario) / "WebRP-Extrator.deb.part").exists())


if __name__ == "__main__":
    unittest.main()
