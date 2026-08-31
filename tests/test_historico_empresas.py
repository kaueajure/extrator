from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.extrator.modelos import LugarExtraido
from src.servicos.historico_empresas import (
    caminho_banco,
    contagem_busca,
    estatisticas,
    limpar_historico_busca,
    listar_historico,
    registrar_lugar,
    urls_para_ignorar,
)


class HistoricoEmpresasTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["WEBRP_HISTORICO_PATH"] = str(Path(self.tmp.name) / "historico.sqlite3")
        self.lugar = LugarExtraido(
            id="abc123",
            nome="Clínica Sorriso",
            telefone="(17) 99999-8888",
            site="https://clinicasorriso.com.br",
            endereco="Rua Central, 10",
            url_referencia="https://www.google.com/maps/place/clinica-sorriso",
        )

    def tearDown(self) -> None:
        os.environ.pop("WEBRP_HISTORICO_PATH", None)
        self.tmp.cleanup()

    def test_salva_incrementalmente_e_atualiza_estado(self) -> None:
        registrar_lugar(self.lugar, "dentista", "Rio Preto", "extraida")
        self.assertEqual(contagem_busca("dentista", "Rio Preto"), 1)
        self.assertEqual(estatisticas()["extraida"], 1)

        registrar_lugar(self.lugar, "dentista", "Rio Preto", "importada", "Lead criado")
        registro = listar_historico()[0]
        self.assertEqual(registro.status, "importada")
        self.assertEqual(registro.ocorrencias, 2)
        self.assertTrue(registro.importado_em)

    def test_politicas_de_continuacao(self) -> None:
        registrar_lugar(self.lugar, "dentista", "Rio Preto", "extraida")
        self.assertEqual(len(urls_para_ignorar("dentista", "Rio Preto", "todas")), 1)
        self.assertEqual(urls_para_ignorar("dentista", "Rio Preto", "importadas"), set())

        registrar_lugar(self.lugar, "dentista", "Rio Preto", "importada")
        self.assertEqual(len(urls_para_ignorar("dentista", "Rio Preto", "importadas")), 1)

        with sqlite3.connect(caminho_banco()) as conexao:
            conexao.execute(
                "UPDATE buscas_empresas SET ultima_vista = '2020-01-01T00:00:00+00:00'"
            )
        self.assertEqual(urls_para_ignorar("dentista", "Rio Preto", "recentes30"), set())

    def test_mesma_empresa_pode_pertencer_a_varias_buscas(self) -> None:
        registrar_lugar(self.lugar, "dentista", "Rio Preto", "extraida")
        registrar_lugar(self.lugar, "clinica", "Rio Preto", "extraida")
        self.assertEqual(contagem_busca("dentista", "Rio Preto"), 1)
        self.assertEqual(contagem_busca("clinica", "Rio Preto"), 1)
        limpar_historico_busca("dentista", "Rio Preto")
        self.assertEqual(contagem_busca("dentista", "Rio Preto"), 0)
        self.assertEqual(contagem_busca("clinica", "Rio Preto"), 1)


if __name__ == "__main__":
    unittest.main()
