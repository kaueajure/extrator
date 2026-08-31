import unittest

from src.extrator.modelos import LugarExtraido
from src.extrator.score import FiltrosLead, eh_perfil_social


def _lugar(site: str | None) -> LugarExtraido:
    return LugarExtraido(id="empresa-1", nome="Empresa", site=site)


class FiltroSemSiteTest(unittest.TestCase):
    def test_perfis_sociais_passam_no_filtro_sem_site(self) -> None:
        filtro = FiltrosLead(sem_site=True)
        perfis = (
            "https://instagram.com/empresa",
            "https://www.facebook.com/empresa",
            "br.linkedin.com/company/empresa",
            "https://tiktok.com/@empresa",
            "https://wa.me/5517999999999",
            "https://linktr.ee/empresa",
        )

        self.assertTrue(all(eh_perfil_social(site) for site in perfis))
        self.assertTrue(all(filtro.passa(_lugar(site), score=50) for site in perfis))

    def test_site_oficial_nao_passa_no_filtro_sem_site(self) -> None:
        filtro = FiltrosLead(sem_site=True)

        self.assertFalse(filtro.passa(_lugar("https://empresa.com.br"), score=50))
        self.assertFalse(
            filtro.passa(_lugar("https://empresa.com.br/instagram"), score=50)
        )

    def test_empresa_sem_link_passa_no_filtro_sem_site(self) -> None:
        filtro = FiltrosLead(sem_site=True)

        self.assertTrue(filtro.passa(_lugar(None), score=50))
        self.assertTrue(filtro.passa(_lugar("  "), score=50))


if __name__ == "__main__":
    unittest.main()
