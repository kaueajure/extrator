from __future__ import annotations

import unittest

from src.servicos.atualizacoes import _interpretar, _partes_versao


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


if __name__ == "__main__":
    unittest.main()
