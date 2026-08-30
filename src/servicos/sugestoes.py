from __future__ import annotations

import asyncio
import json
import re
from functools import lru_cache

import httpx

from src.config import chave_gemini, modelo_gemini

# Nichos concretos para prospecção (PME sem site / independente).
# Chave = termo digitado (ou raiz); valor = buscas úteis no Maps.
NICHOS: dict[str, list[str]] = {
    "restaurante": [
        "marmitaria delivery",
        "restaurante por quilo",
        "comida caseira delivery",
        "lanchonete de bairro",
        "churrascaria pequena",
    ],
    "hamburguer": [
        "hamburgueria artesanal",
        "hamburgueria delivery",
        "smash burger",
    ],
    "pizza": [
        "pizzaria delivery",
        "pizzaria de bairro",
        "rodízio de pizza",
    ],
    "padaria": [
        "padaria artesanal",
        "confeitaria de bairro",
        "panificadora",
    ],
    "cafe": [
        "cafeteria independente",
        "café da manhã",
        "coffee shop local",
    ],
    "café": [
        "cafeteria independente",
        "café da manhã",
    ],
    "clinica": [
        "clínica odontológica",
        "clínica de fisioterapia",
        "clínica de estética",
        "clínica médica popular",
    ],
    "clínica": [
        "clínica odontológica",
        "clínica de fisioterapia",
        "clínica de estética",
    ],
    "odonto": [
        "clínica odontológica",
        "dentista particular",
        "ortodontia",
        "implante dentário",
    ],
    "dentista": [
        "clínica odontológica",
        "dentista particular",
        "ortodontia",
    ],
    "estetica": [
        "clínica de estética",
        "estética facial",
        "depilação a laser",
        "micropigmentação",
    ],
    "estética": [
        "clínica de estética",
        "estética facial",
        "depilação a laser",
    ],
    "salao": [
        "salão de beleza",
        "barbearia",
        "manicure e pedicure",
        "cabeleireiro",
    ],
    "salão": [
        "salão de beleza",
        "barbearia",
        "manicure e pedicure",
    ],
    "barbearia": [
        "barbearia",
        "barbeiro",
        "barbershop",
    ],
    "academia": [
        "academia de bairro",
        "estúdio de pilates",
        "crossfit box",
        "personal trainer",
    ],
    "pilates": [
        "estúdio de pilates",
        "pilates solo",
        "fisioterapia e pilates",
    ],
    "veterinaria": [
        "clínica veterinária",
        "pet shop",
        "banho e tosa",
        "veterinário 24 horas",
    ],
    "veterinária": [
        "clínica veterinária",
        "pet shop",
        "banho e tosa",
    ],
    "pet": [
        "pet shop",
        "banho e tosa",
        "clínica veterinária",
        "creche para cães",
    ],
    "advogado": [
        "advogado trabalhista",
        "escritório de advocacia",
        "advogado previdenciário",
        "advogado de família",
    ],
    "advocacia": [
        "escritório de advocacia",
        "advogado trabalhista",
        "advogado previdenciário",
    ],
    "contabil": [
        "escritório de contabilidade",
        "contador",
        "abertura de empresa",
    ],
    "contábil": [
        "escritório de contabilidade",
        "contador",
    ],
    "contabilidade": [
        "escritório de contabilidade",
        "contador",
        "abertura de empresa",
    ],
    "imobiliaria": [
        "imobiliária",
        "corretor de imóveis",
        "administração de condomínios",
    ],
    "imobiliária": [
        "imobiliária",
        "corretor de imóveis",
    ],
    "oficina": [
        "oficina mecânica",
        "auto elétrica",
        "funilaria e pintura",
        "troca de óleo",
    ],
    "mecanica": [
        "oficina mecânica",
        "mecânica de carros",
        "auto elétrica",
    ],
    "mecânica": [
        "oficina mecânica",
        "mecânica de carros",
        "auto elétrica",
    ],
    "loja": [
        "loja de roupas",
        "loja de materiais de construção",
        "loja de autopeças",
        "loja de móveis",
        "papelaria",
    ],
    "roupa": [
        "loja de roupas",
        "boutique",
        "moda feminina",
        "moda infantil",
    ],
    "farmacia": [
        "farmácia de manipulação",
        "drogaria",
        "farmácia popular",
    ],
    "farmácia": [
        "farmácia de manipulação",
        "drogaria",
    ],
    "escola": [
        "escola de idiomas",
        "curso profissionalizante",
        "reforço escolar",
        "escola de música",
    ],
    "curso": [
        "curso profissionalizante",
        "curso de informática",
        "curso de inglês",
    ],
    "construcao": [
        "materiais de construção",
        "empreiteira",
        "pedreiro",
        "reforma residencial",
    ],
    "construção": [
        "materiais de construção",
        "empreiteira",
        "reforma residencial",
    ],
    "arquiteto": [
        "escritório de arquitetura",
        "arquiteto",
        "design de interiores",
    ],
    "arquitetura": [
        "escritório de arquitetura",
        "design de interiores",
    ],
    "fotografo": [
        "estúdio fotográfico",
        "fotógrafo de casamento",
        "fotografia infantil",
    ],
    "fotógrafo": [
        "estúdio fotográfico",
        "fotógrafo de casamento",
    ],
    "empresa": [
        "clínica odontológica",
        "salão de beleza",
        "oficina mecânica",
        "escritório de contabilidade",
        "pet shop",
    ],
    "comercio": [
        "padaria artesanal",
        "mercado de bairro",
        "farmácia de manipulação",
        "loja de roupas",
    ],
    "comércio": [
        "padaria artesanal",
        "mercado de bairro",
        "farmácia de manipulação",
    ],
}

GENERICAS = frozenset({
    "empresa", "empresas", "negocio", "negócio", "negocios", "negócios",
    "comercio", "comércio", "loja", "lojas", "servico", "serviço",
    "servicos", "serviços", "estabelecimento", "local", "lugar",
})


def _normalizar(texto: str) -> str:
    return " ".join(texto.strip().lower().split())


def _consulta_generica(consulta: str) -> bool:
    norm = _normalizar(consulta)
    if not norm:
        return False
    if norm in GENERICAS or norm in NICHOS:
        return True
    palavras = norm.split()
    if len(palavras) == 1 and len(norm) >= 3:
        return True
    if len(palavras) <= 2 and any(p in NICHOS or p.rstrip("s") in NICHOS for p in palavras):
        return True
    return False


def _sugestoes_por_regras(consulta: str) -> list[str]:
    norm = _normalizar(consulta)
    if norm in NICHOS:
        return list(NICHOS[norm])

    for chave, sugestoes in NICHOS.items():
        if norm.startswith(chave) or chave.startswith(norm):
            return list(sugestoes)
        if len(norm) >= 4 and chave.startswith(norm[:4]):
            return list(sugestoes)

    raiz = norm.rstrip("s")
    if raiz in NICHOS:
        return list(NICHOS[raiz])

    for palavra in norm.split():
        if palavra in NICHOS:
            return list(NICHOS[palavra])
        if palavra.rstrip("s") in NICHOS:
            return list(NICHOS[palavra.rstrip("s")])

    return []


def sugestoes_locais_rapidas(consulta: str, local: str = "") -> list[str]:
    """Sugestões instantâneas (sem rede) — seguro chamar na UI thread."""
    termo = consulta.strip()
    if len(termo) < 2:
        return []

    cidade = ""
    if local:
        cidade = local.split(",")[0].strip()

    vistos: set[str] = set()
    resultado: list[str] = []

    def add(item: str) -> None:
        limpo = item.strip()
        chave = limpo.lower()
        if len(limpo) < 3 or chave == termo.lower() or chave in vistos:
            return
        vistos.add(chave)
        resultado.append(limpo)

    for item in _sugestoes_por_regras(termo):
        add(item)

    if cidade and len(cidade) >= 3 and len(resultado) < 5:
        for item in list(resultado[:3]):
            add(f"{item} {cidade}")

    return resultado[:8]


def _montar_prompt(consulta: str, local: str) -> str:
    cidade = local.split(",")[0].strip() if local else local
    return (
        "Você é especialista em prospecção B2B para agência web que vende sites.\n"
        f'Termo digitado: "{consulta}"\n'
        f'Cidade/região: "{cidade}"\n\n'
        "Gere exatamente 6 termos de busca para Google Maps que encontrem "
        "PMEs locais (donos de negócio pequeno/médio), NÃO redes nacionais "
        "(iFood, McDonald's, OdontoCompany, etc.).\n\n"
        "Regras:\n"
        "- Cada termo deve ser ESPECÍFICO (ex.: «farmácia de manipulação», "
        "não «farmácia»).\n"
        "- Foque nichos que costumam não ter site profissional.\n"
        "- Varie especialidades, porte e formato (delivery, bairro, particular).\n"
        "- NÃO repita o termo digitado.\n"
        "- NÃO use sufixos genéricos sozinhos («familiar», «de bairro») "
        "sem especializar o tipo de negócio.\n"
        "- Português do Brasil.\n"
        "- Responda SOMENTE um JSON array de strings."
    )


def _extrair_lista_json(conteudo: str) -> list[str]:
    texto = conteudo.strip()
    if texto.startswith("```"):
        texto = texto.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    try:
        sugestoes = json.loads(texto)
        if isinstance(sugestoes, list):
            return [str(item).strip() for item in sugestoes if str(item).strip()]
    except json.JSONDecodeError:
        pass

    match = re.search(r"\[(?:\s*\"[^\"]+\"\s*,?)+\]", texto, re.DOTALL)
    if match:
        try:
            sugestoes = json.loads(match.group(0))
            if isinstance(sugestoes, list):
                return [str(item).strip() for item in sugestoes if str(item).strip()]
        except json.JSONDecodeError:
            pass

    return []


async def _sugestoes_por_gemini(consulta: str, local: str) -> list[str]:
    chave = chave_gemini()
    if not chave:
        return []

    modelo = modelo_gemini()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"

    async with httpx.AsyncClient(timeout=12.0) as cliente:
        resposta = await cliente.post(
            url,
            params={"key": chave},
            json={
                "systemInstruction": {
                    "parts": [{
                        "text": (
                            "Responda apenas JSON válido: array de 6 strings "
                            "com termos de busca específicos para Google Maps."
                        ),
                    }],
                },
                "contents": [{
                    "role": "user",
                    "parts": [{"text": _montar_prompt(consulta, local)}],
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "responseMimeType": "application/json",
                },
            },
        )
        resposta.raise_for_status()
        corpo = resposta.json()

    candidatos = corpo.get("candidates") or []
    if not candidatos:
        return []

    partes = candidatos[0].get("content", {}).get("parts") or []
    if not partes:
        return []

    return _extrair_lista_json(str(partes[0].get("text", "")))[:6]


def _mesclar(preferidas: list[str], extras: list[str], consulta: str, limite: int = 6) -> list[str]:
    vistos = {_normalizar(consulta)}
    saida: list[str] = []
    for item in preferidas + extras:
        chave = _normalizar(item)
        if not chave or chave in vistos:
            continue
        vistos.add(chave)
        saida.append(item.strip())
        if len(saida) >= limite:
            break
    return saida


async def sugerir_consulta(consulta: str, local: str) -> dict:
    termo = consulta.strip()
    locais = sugestoes_locais_rapidas(termo, local)
    generica = _consulta_generica(termo) or bool(locais)

    if len(termo) < 3:
        return {
            "generica": False,
            "sugestoes": [],
            "mensagem": "",
            "origem": "nenhuma",
            "ia_disponivel": bool(chave_gemini()),
        }

    origem = "regras"
    sugestoes = locais

    if chave_gemini() and (generica or len(termo) >= 4):
        try:
            gemini = await _sugestoes_por_gemini(termo, local)
            if gemini:
                sugestoes = _mesclar(gemini, locais, termo)
                origem = "gemini"
        except Exception:
            pass

    if not sugestoes:
        return {
            "generica": False,
            "sugestoes": [],
            "mensagem": "",
            "origem": "nenhuma",
            "ia_disponivel": bool(chave_gemini()),
        }

    return {
        "generica": True,
        "sugestoes": sugestoes[:6],
        "mensagem": "Sugestões específicas para achar PMEs (evitam redes grandes).",
        "origem": origem,
        "ia_disponivel": bool(chave_gemini()),
    }


@lru_cache(maxsize=32)
def _sugerir_cache(consulta: str, local: str) -> str:
    """Cache serializado para evitar Gemini repetido no mesmo termo."""
    return json.dumps(asyncio.run(sugerir_consulta(consulta, local)), ensure_ascii=False)


def sugerir_consulta_sync(consulta: str, local: str) -> dict:
    try:
        return json.loads(_sugerir_cache(consulta.strip().lower(), local.strip().lower()))
    except Exception:
        return {
            "generica": bool(sugestoes_locais_rapidas(consulta, local)),
            "sugestoes": sugestoes_locais_rapidas(consulta, local),
            "mensagem": "Sugestões locais.",
            "origem": "regras",
            "ia_disponivel": bool(chave_gemini()),
        }


# Compatibilidade com imports antigos
CONSULTAS_GENERICAS = NICHOS
