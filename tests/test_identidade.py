from __future__ import annotations

import unittest

from src.extrator.modelos import LugarExtraido
from src.servicos.identidade import (
    IndiceIdentidades,
    normalizar_dominio,
    normalizar_telefone,
)


class IdentidadeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.indice = IndiceIdentidades(
            maps_ids={"maps-123"},
            nomes={"clinica sorriso"},
            telefones={"17999998888"},
            dominios={"clinicasorriso.com.br"},
            nome_enderecos={"clinica sorriso|rua central 10"},
        )

    def test_prioriza_identificadores_fortes(self) -> None:
        lugar = LugarExtraido(id="maps-123", nome="Outro nome")
        resultado = self.indice.avaliar(lugar)
        self.assertTrue(resultado.duplicado)
        self.assertIn("Maps", resultado.motivo)

        lugar = LugarExtraido(id="novo", nome="Outro", telefone="(17) 99999-8888")
        self.assertEqual(self.indice.avaliar(lugar).motivo, "mesmo telefone")

        lugar = LugarExtraido(id="novo", nome="Outro", site="https://www.clinicasorriso.com.br/")
        self.assertEqual(self.indice.avaliar(lugar).motivo, "mesmo domínio do site")

    def test_nome_isolado_e_apenas_alerta(self) -> None:
        lugar = LugarExtraido(id="novo", nome="Clínica Sorriso")
        resultado = self.indice.avaliar(lugar)
        self.assertFalse(resultado.duplicado)
        self.assertTrue(resultado.apenas_alerta)

    def test_normalizadores_evitam_dominios_genericos(self) -> None:
        self.assertEqual(normalizar_telefone("+55 (17) 99999-8888"), "17999998888")
        self.assertEqual(normalizar_dominio("https://instagram.com/empresa"), "")
        self.assertEqual(normalizar_dominio("empresa.com.br/contato"), "empresa.com.br")


if __name__ == "__main__":
    unittest.main()
