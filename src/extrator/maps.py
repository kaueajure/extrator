from __future__ import annotations

import re
import time
from collections.abc import Callable
from urllib.parse import quote_plus, unquote, urlparse

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, TimeoutError as PlaywrightTimeout, sync_playwright

from src.config import LIMITE_MAXIMO_RESULTADOS
from src.extrator.ids import id_maps, normalizar_url_maps
from src.extrator.modelos import CaptchaDetectado, ExtracaoCancelada, LugarExtraido, ResultadoExtracao
from src.servicos.perfil_google import (
    diretorio_perfil,
    limpar_marcador_sessao,
    limpar_sessao,
    marcar_sessao_ativa,
)

LogCallback = Callable[[str], None]
LugarCallback = Callable[[LugarExtraido], None]
CancelCallback = Callable[[], bool]

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
ARGS_CHROMIUM = ["--lang=pt-BR", "--disable-blink-features=AutomationControlled"]


def _log(callback: LogCallback | None, mensagem: str) -> None:
    if callback:
        callback(mensagem)


def _montar_url_busca(consulta: str, local: str) -> str:
    termo = f"{consulta} em {local}"
    return f"https://www.google.com/maps/search/{quote_plus(termo)}"


def _opcoes_contexto() -> dict:
    return {
        "locale": "pt-BR",
        "viewport": {"width": 1400, "height": 900},
        "user_agent": USER_AGENT,
    }


def _abrir_contexto(
    playwright: Playwright,
    visivel: bool,
    usar_perfil_google: bool,
) -> tuple[BrowserContext, Page, Browser | None]:
    opcoes = _opcoes_contexto()
    if usar_perfil_google:
        # Sessão Google quase nunca sobrevive em headless — abre o Chromium visível.
        pasta = diretorio_perfil()
        pasta.mkdir(parents=True, exist_ok=True)
        context = playwright.chromium.launch_persistent_context(
            str(pasta),
            headless=False,
            slow_mo=250 if visivel else 50,
            args=ARGS_CHROMIUM,
            **opcoes,
        )
        page = context.pages[0] if context.pages else context.new_page()
        return context, page, None

    browser = playwright.chromium.launch(
        headless=not visivel,
        slow_mo=250 if visivel else 0,
        args=ARGS_CHROMIUM,
    )
    context = browser.new_context(**opcoes)
    return context, context.new_page(), browser


def _fechar_contexto(context: BrowserContext, browser: Browser | None) -> None:
    context.close()
    if browser:
        browser.close()


TEMPO_ESPERA_CAPTCHA = 300

FRAGMENTOS_CAPTCHA = (
    ("tráfego incomum", "Tráfego incomum detectado pelo Google"),
    ("unusual traffic", "Tráfego incomum detectado pelo Google"),
    ("not a robot", "Confirmação «não sou um robô»"),
    ("não é um robô", "Confirmação «não sou um robô»"),
    ("verify you're human", "Verificação humana solicitada"),
    ("confirme que você", "Verificação humana solicitada"),
    ("before you continue", "Google pediu confirmação antes de continuar"),
    ("antes de continuar", "Google pediu confirmação antes de continuar"),
    ("detectamos atividade incomum", "Atividade incomum detectada"),
    ("our systems have detected", "Sistema anti-abuso do Google"),
    ("automated queries", "Consultas automatizadas bloqueadas"),
    ("consultas automatizadas", "Consultas automatizadas bloqueadas"),
    ("can't access google maps", "Acesso ao Maps bloqueado"),
    ("não é possível acessar o google maps", "Acesso ao Maps bloqueado"),
    ("solve the challenge", "Desafio de segurança pendente"),
    ("complete the security check", "Verificação de segurança pendente"),
)

SELETORES_CAPTCHA = (
    'iframe[src*="recaptcha"]',
    'iframe[title*="reCAPTCHA"]',
    'iframe[title*="recaptcha"]',
    "#recaptcha",
    ".g-recaptcha",
    '[id*="captcha"]',
    'form[action*="sorry"]',
)


def detectar_captcha(page: Page) -> str | None:
    url = page.url.lower()
    if "/sorry/" in url or "google.com/sorry" in url:
        return "Página de verificação do Google (sorry)"
    if "accounts.google.com" in url and "challenge" in url:
        return "Desafio de segurança na conta Google"

    for seletor in SELETORES_CAPTCHA:
        try:
            if page.locator(seletor).count() > 0:
                return "reCAPTCHA detectado na página"
        except Exception:
            continue

    try:
        texto = page.locator("body").inner_text(timeout=3000).lower()
    except Exception:
        texto = ""

    for trecho, motivo in FRAGMENTOS_CAPTCHA:
        if trecho in texto:
            return motivo

    try:
        titulo = page.title().lower()
        if "sorry" in titulo or "unusual traffic" in titulo:
            return "Bloqueio temporário do Google"
    except Exception:
        pass

    return None


def aguardar_resolucao_captcha(
    page: Page,
    callback: LogCallback | None,
    timeout: int = TEMPO_ESPERA_CAPTCHA,
) -> bool:
    inicio = time.time()
    aviso_periodico = inicio
    while time.time() - inicio < timeout:
        if not detectar_captcha(page):
            return True
        if time.time() - aviso_periodico >= 15:
            _log(callback, "Aguardando resolução do captcha na janela do navegador…")
            aviso_periodico = time.time()
        try:
            page.wait_for_timeout(2000)
        except Exception:
            return False
    return False


def _verificar_captcha(page: Page, visivel: bool, callback: LogCallback | None) -> None:
    motivo = detectar_captcha(page)
    if not motivo:
        return

    _log(callback, f"Captcha detectado: {motivo}")
    if visivel:
        _log(
            callback,
            f"Resolva a verificação na janela do navegador (até {TEMPO_ESPERA_CAPTCHA // 60} min)…",
        )
        if aguardar_resolucao_captcha(page, callback):
            _log(callback, "Captcha resolvido — continuando.")
            return

    raise CaptchaDetectado(motivo)


COOKIES_LOGIN_GOOGLE = (
    "SID",
    "HSID",
    "SSID",
    "APISID",
    "SAPISID",
    "__Secure-1PSID",
    "__Secure-3PSID",
)


def cookies_indicam_login(context: BrowserContext) -> bool:
    try:
        nomes = {cookie.get("name", "") for cookie in context.cookies()}
    except Exception:
        return False
    return any(nome in nomes for nome in COOKIES_LOGIN_GOOGLE)


def esta_logado_google(page: Page) -> bool:
    """Confirma login por cookies + UI do Maps (evita falso negativo genérico)."""
    url = page.url.lower()
    if "accounts.google.com" in url and "servicelogin" in url.replace("_", ""):
        return False

    # Cookies de sessão Google são o sinal mais confiável
    try:
        if cookies_indicam_login(page.context):
            # Se o botão explícito de login ainda aparece, a sessão expirou na prática
            if _botao_fazer_login_visivel(page):
                return False
            return True
    except Exception:
        pass

    if _botao_fazer_login_visivel(page):
        return False

    seletores_conta = (
        'button[aria-label*="Conta do Google"]',
        'button[aria-label*="Google Account"]',
        'a[aria-label*="Conta do Google"]',
        'a[aria-label*="Google Account"]',
        'button[aria-label*="Conta Google"]',
        'a[href*="accounts.google.com/SignOutOptions"]',
        'img[src*="googleusercontent.com"]',
        'a[aria-label*="Foto do perfil"]',
    )
    for seletor in seletores_conta:
        try:
            if page.locator(seletor).count() > 0:
                return True
        except Exception:
            continue
    return False


def _botao_fazer_login_visivel(page: Page) -> bool:
    """Só o CTA real de login — não confundir com outros botões «Entrar»."""
    rotulos = (
        "Fazer login",
        "Fazer Login",
        "Sign in",
        "Sign in to Google",
        "Fazer login no Google",
    )
    for rotulo in rotulos:
        try:
            link = page.get_by_role("link", name=rotulo, exact=True)
            if link.count() > 0 and link.first.is_visible():
                return True
            botao = page.get_by_role("button", name=rotulo, exact=True)
            if botao.count() > 0 and botao.first.is_visible():
                return True
        except Exception:
            continue

    # Fallback parcial, mas exige «login» / «sign in» no texto
    try:
        for papel in ("link", "button"):
            candidatos = page.get_by_role(papel)
            total = min(candidatos.count(), 40)
            for i in range(total):
                try:
                    texto = (candidatos.nth(i).inner_text(timeout=500) or "").strip().lower()
                except Exception:
                    continue
                if texto in {"fazer login", "sign in", "fazer login no google", "sign in to google"}:
                    if candidatos.nth(i).is_visible():
                        return True
    except Exception:
        pass
    return False


def _pagina_em_login(pagina: Page) -> bool:
    url = pagina.url.lower()
    return "accounts.google.com" in url or "myaccount.google.com" in url


def _confirmar_e_marcar_login(page: Page, callback: LogCallback | None) -> bool:
    if not esta_logado_google(page):
        return False
    marcar_sessao_ativa()
    if cookies_indicam_login(page.context):
        _log(callback, "Login Google confirmado (cookies + Maps).")
    else:
        _log(callback, "Login Google confirmado no Maps.")
    return True


def abrir_login_google(callback: LogCallback | None = None) -> bool:
    _log(callback, "Abrindo navegador para login no Google…")
    _log(
        callback,
        "No Maps, clique em «Fazer login» (se aparecer), conclua o login "
        "e aguarde — o app não vai interromper a página.",
    )

    logado = False
    prazo = time.time() + 600
    aviso_aguardo = 0.0

    with sync_playwright() as playwright:
        context, page, browser = _abrir_contexto(playwright, visivel=True, usar_perfil_google=True)
        try:
            page.goto(
                "https://www.google.com/maps",
                wait_until="domcontentloaded",
                timeout=45000,
            )
            _aceitar_cookies(page)
            page.wait_for_timeout(1500)

            if _confirmar_e_marcar_login(page, callback):
                logado = True
                _log(callback, "Você já está logado no Google Maps — sessão salva.")
                page.wait_for_timeout(3000)
            else:
                _log(callback, "Clique em «Fazer login» no Maps e complete o acesso à sua conta.")

            while time.time() < prazo and not logado:
                if not context.pages:
                    _log(callback, "Navegador fechado.")
                    break

                em_login = False
                for pagina in context.pages:
                    if _pagina_em_login(pagina):
                        em_login = True
                        break

                if em_login:
                    if time.time() - aviso_aguardo >= 20:
                        _log(callback, "Aguardando você concluir o login no Google…")
                        aviso_aguardo = time.time()
                    page.wait_for_timeout(2000)
                    continue

                pagina = context.pages[0]
                url = pagina.url.lower()

                if "google.com/maps" not in url and not _pagina_em_login(pagina):
                    try:
                        pagina.goto(
                            "https://www.google.com/maps",
                            wait_until="domcontentloaded",
                            timeout=30000,
                        )
                        _aceitar_cookies(pagina)
                        pagina.wait_for_timeout(1500)
                    except Exception:
                        pagina.wait_for_timeout(2000)
                        continue

                if _confirmar_e_marcar_login(pagina, callback):
                    logado = True
                    _log(callback, "Sessão salva para próximas buscas.")
                    pagina.wait_for_timeout(4000)
                    break

                if time.time() - aviso_aguardo >= 20:
                    _log(
                        callback,
                        "Ainda sem login detectado. Clique em «Fazer login» no Maps e termine o acesso.",
                    )
                    aviso_aguardo = time.time()

                try:
                    pagina.wait_for_timeout(2000)
                except Exception:
                    break
        finally:
            _fechar_contexto(context, browser)

    if not logado:
        limpar_marcador_sessao()
        _log(callback, "Login não confirmado. Tente de novo e conclua antes de fechar o navegador.")
    return logado


def _aceitar_cookies(page: Page) -> None:
    rotulos = [
        "Aceitar tudo",
        "Accept all",
        "Recusar tudo",
        "Reject all",
        "Aceitar",
        "Accept",
    ]
    for rotulo in rotulos:
        try:
            botao = page.get_by_role("button", name=rotulo, exact=False)
            if botao.count() > 0:
                botao.first.click(timeout=2000)
                page.wait_for_timeout(500)
                return
        except PlaywrightTimeout:
            continue
        except Exception:
            continue


def _normalizar_url_lugar(url: str) -> str:
    return normalizar_url_maps(url)


def _extrair_id(url: str) -> str:
    return id_maps(url)


def _parse_coordenadas(url: str) -> tuple[float | None, float | None]:
    padrao = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", url)
    if not padrao:
        return None, None
    return float(padrao.group(1)), float(padrao.group(2))


def _texto_aria(page: Page, seletor: str) -> str | None:
    try:
        elemento = page.locator(seletor).first
        if elemento.count() == 0:
            return None
        rotulo = elemento.get_attribute("aria-label")
        if rotulo:
            return rotulo.strip()
        texto = elemento.inner_text(timeout=2000).strip()
        return texto or None
    except Exception:
        return None


def _limpar_rotulo(valor: str | None, prefixos: list[str]) -> str | None:
    if not valor:
        return None
    texto = valor.strip()
    for prefixo in prefixos:
        if texto.lower().startswith(prefixo.lower()):
            texto = texto[len(prefixo):].strip()
    return texto or None


def _resultado_parcial(
    inicio: float,
    lugares: list[LugarExtraido],
    urls_vistas: set[str],
    ignorados_webrp: int,
    ignorados_continuacao: int,
) -> ResultadoExtracao:
    return ResultadoExtracao(
        lugares=list(lugares),
        duracao_segundos=round(time.time() - inicio, 1),
        urls_processadas=sorted(urls_vistas),
        ignorados_webrp=ignorados_webrp,
        ignorados_continuacao=ignorados_continuacao,
    )


def _levantar_se_cancelado(
    deve_cancelar: CancelCallback | None,
    inicio: float,
    lugares: list[LugarExtraido],
    urls_vistas: set[str],
    ignorados_webrp: int,
    ignorados_continuacao: int,
) -> None:
    if deve_cancelar and deve_cancelar():
        raise ExtracaoCancelada(
            _resultado_parcial(inicio, lugares, urls_vistas, ignorados_webrp, ignorados_continuacao)
        )


def _coletar_links(
    page: Page,
    limite: int,
    ignorar_urls: set[str],
    callback: LogCallback | None,
    visivel: bool = False,
    deve_cancelar: CancelCallback | None = None,
) -> tuple[list[str], set[str], int]:
    _verificar_captcha(page, visivel, callback)

    feed = page.locator('div[role="feed"]')
    try:
        feed.wait_for(state="visible", timeout=20000)
    except PlaywrightTimeout:
        motivo = detectar_captcha(page)
        if motivo:
            _verificar_captcha(page, visivel, callback)
        raise

    links: list[str] = []
    vistos: set[str] = set()
    tentativas_sem_novos = 0
    pulados_continuacao = 0

    while len(links) < limite and tentativas_sem_novos < max(12, limite // 4):
        if deve_cancelar and deve_cancelar():
            _log(callback, "Coleta interrompida pelo usuário.")
            break

        _verificar_captcha(page, visivel, callback)

        candidatos = page.locator('a[href*="/maps/place/"]').all()
        novos = 0
        for item in candidatos:
            href = item.get_attribute("href")
            if not href:
                continue
            url = _normalizar_url_lugar(href)
            if url in vistos:
                continue
            vistos.add(url)
            novos += 1
            if url in ignorar_urls:
                pulados_continuacao += 1
                continue
            links.append(url)
            if len(links) >= limite:
                break

        if pulados_continuacao and len(links) == 0:
            _log(callback, f"Pulando {pulados_continuacao} lugar(es) já visto(s) nesta busca…")

        _log(callback, f"Links coletados: {len(links)} de {limite}.")
        if len(links) >= limite:
            break

        if novos == 0:
            tentativas_sem_novos += 1
        else:
            tentativas_sem_novos = 0

        try:
            feed.evaluate("el => { el.scrollTop = el.scrollHeight; }")
        except Exception:
            page.mouse.wheel(0, 1800)
        page.wait_for_timeout(1200)

    return links[:limite], vistos, pulados_continuacao


def _extrair_categoria(page: Page) -> str | None:
    seletores = [
        "button[jsaction*='category']",
        "span.DkEaL",
        "button[aria-label*='Categoria']",
    ]
    for seletor in seletores:
        try:
            elemento = page.locator(seletor).first
            if elemento.count() == 0:
                continue
            texto = elemento.inner_text(timeout=1500).strip()
            if texto and len(texto) < 80:
                return texto
        except Exception:
            continue
    return None


def _extrair_nota(page: Page) -> tuple[float | None, int | None]:
    try:
        nota_el = page.locator('span[aria-hidden="true"]').filter(has_text=re.compile(r"^\d,\d$|^\d\.\d$"))
        if nota_el.count() == 0:
            nota_el = page.locator("div.F7nice span").first
        nota_texto = nota_el.inner_text(timeout=1500).replace(",", ".") if nota_el.count() else ""
        nota = float(nota_texto) if re.match(r"^\d+(\.\d+)?$", nota_texto) else None
    except Exception:
        nota = None

    avaliacoes = None
    try:
        bloco = page.locator("span[aria-label*='avalia']").first
        if bloco.count() == 0:
            bloco = page.locator("button[aria-label*='avalia']").first
        if bloco.count() > 0:
            rotulo = bloco.get_attribute("aria-label") or bloco.inner_text()
            numeros = re.search(r"([\d\.]+)", rotulo or "")
            if numeros:
                avaliacoes = int(float(numeros.group(1).replace(".", "")))
    except Exception:
        pass

    return nota, avaliacoes


def _extrair_detalhes(
    page: Page,
    url: str,
    callback: LogCallback | None,
    visivel: bool = False,
) -> LugarExtraido:
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    _verificar_captcha(page, visivel, callback)
    page.wait_for_selector("h1", timeout=20000)
    page.wait_for_timeout(800)

    nome = page.locator("h1").first.inner_text(timeout=5000).strip()
    endereco = _limpar_rotulo(
        _texto_aria(page, 'button[data-item-id="address"]') or _texto_aria(page, '[data-item-id="address"]'),
        ["Endereço:", "Address:"],
    )
    telefone = _limpar_rotulo(
        _texto_aria(page, 'button[data-item-id="phone"]') or _texto_aria(page, '[data-item-id="phone"]'),
        ["Telefone:", "Phone:"],
    )

    site = None
    try:
        link_site = page.locator('a[data-item-id="authority"]').first
        if link_site.count() > 0:
            site = link_site.get_attribute("href")
    except Exception:
        site = None

    categoria = _extrair_categoria(page)
    nota, avaliacoes = _extrair_nota(page)
    latitude, longitude = _parse_coordenadas(page.url)

    _log(callback, f"Extraído: {nome}")

    return LugarExtraido(
        id=_extrair_id(url),
        nome=nome,
        categoria=categoria,
        endereco=endereco,
        telefone=telefone,
        site=site,
        nota=nota,
        avaliacoes=avaliacoes,
        latitude=latitude,
        longitude=longitude,
        url_referencia=page.url,
    )


def extrair_lugares(
    consulta: str,
    local: str,
    limite: int = 10,
    visivel: bool = False,
    callback: LogCallback | None = None,
    on_lugar: LugarCallback | None = None,
    urls_ignorar: set[str] | None = None,
    ja_existe_webrp: Callable[[LugarExtraido], bool] | None = None,
    ja_existe_url: Callable[[str], bool] | None = None,
    usar_perfil_google: bool = True,
    deve_cancelar: CancelCallback | None = None,
) -> ResultadoExtracao:
    inicio = time.time()
    limite = max(1, min(limite, LIMITE_MAXIMO_RESULTADOS))
    ignorar = urls_ignorar or set()
    url_busca = _montar_url_busca(consulta, local)

    _log(callback, f"Abrindo Google Maps para: {unquote(urlparse(url_busca).path.split('/')[-1])}")
    if ignorar:
        _log(callback, f"Continuando busca — {len(ignorar)} lugar(es) já processado(s) serão pulados.")
    if usar_perfil_google:
        _log(callback, "Usando perfil Google salvo neste computador.")
        if not visivel:
            _log(callback, "Com sessão Google o navegador precisa abrir (headless não mantém o login).")
    if visivel:
        _log(callback, "Modo visível ativo — a janela do navegador será exibida.")
    elif not usar_perfil_google:
        _log(callback, "Modo silencioso — extração em segundo plano.")

    lugares: list[LugarExtraido] = []
    ignorados_webrp = 0
    ignorados_continuacao = 0
    urls_vistas: set[str] = set()

    with sync_playwright() as playwright:
        context, page, browser = _abrir_contexto(playwright, visivel, usar_perfil_google)

        try:
            _levantar_se_cancelado(deve_cancelar, inicio, lugares, urls_vistas, ignorados_webrp, ignorados_continuacao)

            page.goto(url_busca, wait_until="domcontentloaded", timeout=45000)
            _aceitar_cookies(page)
            page.wait_for_timeout(1200)
            _verificar_captcha(page, visivel, callback)
            _levantar_se_cancelado(deve_cancelar, inicio, lugares, urls_vistas, ignorados_webrp, ignorados_continuacao)
            if usar_perfil_google:
                if esta_logado_google(page):
                    marcar_sessao_ativa()
                    _log(callback, "Sessão Google ativa no Maps.")
                else:
                    limpar_marcador_sessao()
                    _log(
                        callback,
                        "Sem login Google neste perfil — use «Entrar no Google» "
                        "(com o navegador em modo «Visível») se o Maps limitar buscas.",
                    )

            _log(callback, "Aguardando resultados da busca…")

            links, urls_vistas, ignorados_continuacao = _coletar_links(
                page, limite, ignorar, callback, visivel, deve_cancelar
            )
            _levantar_se_cancelado(deve_cancelar, inicio, lugares, urls_vistas, ignorados_webrp, ignorados_continuacao)
            if not links:
                if detectar_captcha(page):
                    _verificar_captcha(page, visivel, callback)
                if ignorados_continuacao:
                    _log(callback, "Não há mais lugares novos nesta busca. Tente uma busca variada.")
                else:
                    _log(callback, "Nenhum lugar encontrado nesta busca.")
                return ResultadoExtracao(
                    lugares=[],
                    duracao_segundos=time.time() - inicio,
                    urls_processadas=sorted(urls_vistas),
                    ignorados_webrp=0,
                    ignorados_continuacao=ignorados_continuacao,
                )

            _log(callback, f"Iniciando extração de {len(links)} lugares…")
            for indice, link in enumerate(links, start=1):
                _levantar_se_cancelado(deve_cancelar, inicio, lugares, urls_vistas, ignorados_webrp, ignorados_continuacao)
                _log(callback, f"Extraindo {indice}/{len(links)}…")
                url_norm = _normalizar_url_lugar(link)
                if ja_existe_url and ja_existe_url(url_norm):
                    ignorados_webrp += 1
                    urls_vistas.add(url_norm)
                    _log(callback, "Ignorado (já no WebRP) — link conhecido.")
                    continue
                try:
                    lugar = _extrair_detalhes(page, link, callback, visivel)
                    urls_vistas.add(_normalizar_url_lugar(link))
                    if ja_existe_webrp and ja_existe_webrp(lugar):
                        ignorados_webrp += 1
                        _log(callback, f"Ignorado (já no WebRP): {lugar.nome}")
                        continue
                    lugares.append(lugar)
                    if on_lugar:
                        on_lugar(lugar)
                except CaptchaDetectado:
                    raise
                except ExtracaoCancelada:
                    raise
                except Exception as erro:
                    _log(callback, f"Falha ao extrair um item: {erro}")
                page.wait_for_timeout(600)

            _levantar_se_cancelado(deve_cancelar, inicio, lugares, urls_vistas, ignorados_webrp, ignorados_continuacao)
            _log(callback, f"Extração concluída: {len(lugares)} lugares.")
            if ignorados_webrp:
                _log(callback, f"{ignorados_webrp} ignorado(s) por já existirem no WebRP.")
        finally:
            _fechar_contexto(context, browser)

    return ResultadoExtracao(
        lugares=lugares,
        duracao_segundos=round(time.time() - inicio, 1),
        urls_processadas=sorted(urls_vistas),
        ignorados_webrp=ignorados_webrp,
        ignorados_continuacao=ignorados_continuacao,
    )


def desconectar_google() -> None:
    limpar_sessao()
