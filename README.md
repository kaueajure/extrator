# WebRP-Extrator

Aplicativo **desktop** (Windows e Linux) para extrair empresas no **Google Maps** com **Playwright** e importar leads diretamente no painel **WebRP**.

Distribuído via `extrator.webriopreto.com` (página de download no site WebRP oficial). Não roda na Hostinger — executa no computador do usuário.

## O que faz

- **Login** com credenciais do painel WebRP (`/admin/login`)
- Busca lugares no Google Maps a partir de **consulta + cidade**
- Modo **visível** (acompanha o navegador) ou **silencioso** (headless)
- **Logs em tempo real** durante a extração
- **Filtros:** sem site, máx. avaliações, nota mínima, score mínimo
- **Score de lead** (0–100)
- **Sugestões de busca** para consultas genéricas (regras locais ou Gemini)
- **Continuar busca** — retoma da mesma consulta pulando lugares já extraídos
- **Cruzar com WebRP** — ignora leads que já estão no funil
- **Buscas variadas** — termos alternativos, botão “Próxima busca variada” e rotação após importar
- **Implementar ao WebRP** — envia leads para `https://webriopreto.com/api/admin/leads`

## Requisitos

- Python 3.11+ (desenvolvimento)
- Google Chrome/Chromium (instalado pelo Playwright)
- Linux: bibliotecas Qt (`libxcb-cursor0` etc. no Ubuntu)

## Instalação para desenvolvimento

```bash
cd WebRP-extrator
chmod +x instalar rodar
./instalar
```

### Pacotes do sistema (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv \
  libxcb-cursor0 libxkbcommon-x11-0 libegl1
```

## Uso

```bash
./rodar
```

1. Faça **login** com e-mail e senha do painel WebRP
2. Informe consulta e cidade; use **sugestões** se a busca for genérica
3. Ajuste **filtros** e confira o **score**
4. Selecione os leads e clique em **Implementar ao WebRP**

Credenciais podem ser salvas no cofre do sistema (“Manter conectado”).

## Variáveis de ambiente (`.env` — só desenvolvimento)

No instalador oficial **não há `.env`**. Em `./rodar` local:

| Variável | Descrição |
|---|---|
| `WEBRP_URL` | URL do WebRP (padrão produção) |
| `WEBRP_EMAIL` / `WEBRP_SENHA` | Pré-preenche login (opcional) |
| `DB_*` | Opcional: cruzamento/importação direta MySQL |
| `GEMINI_API_KEY` | Sugestões via Gemini (opcional) |

## Build do instalável

### Automático (GitHub Actions — recomendado)

Gera **instaladores** Windows e Linux (sem `.zip` / `.tar.gz` para o usuário final).

**Teste (sem release pública):**

1. GitHub → **Actions** → **Build releases** → **Run workflow**
2. Baixe os artifacts `WebRP-Extrator-windows` (Setup.exe) e `WebRP-Extrator-linux` (Setup.run)

**Release oficial:**

```bash
git tag v1.2.0
git push origin v1.2.0
```

Artefatos em [Releases](https://github.com/kaueajure/extrator/releases):

- `WebRP-Extrator-Setup.exe` — instalador Windows (próximo → concluir → abrir)
- `WebRP-Extrator-Setup.run` — instalador Linux (`chmod +x` e executar)

O Chromium do Playwright já vem embutido. **Não precisa de `.env`** — basta login de desenvolvedor no WebRP.

### Linux (local)

```bash
./instalar
pyinstaller build/webrp-extrator.spec --noconfirm
PLAYWRIGHT_BROWSERS_PATH="$PWD/dist/WebRP-Extrator/ms-playwright" python -m playwright install chromium
./build/criar-instalador-linux.sh
```

### Windows (local)

Só em máquina Windows, ou use o GitHub Actions.

```powershell
pip install -e .
pip install pyinstaller
pyinstaller build\webrp-extrator.spec --noconfirm
# Instale Inno Setup 6 e compile build\windows-setup.iss
```

## Estrutura

```
WebRP-extrator/
├── app.py                    # Entry point
├── src/
│   ├── ui/                   # App desktop (PySide6)
│   │   ├── app.py
│   │   ├── login.py
│   │   ├── principal.py
│   │   └── workers.py
│   ├── servicos/             # WebRP, sessão, sugestões
│   ├── extrator/             # Playwright + score
│   └── config.py
└── build/                    # PyInstaller
```

## Integração com o WebRP

O instalador aponta para `https://webriopreto.com`. Autentica via `POST /api/admin/login`, lista leads via `GET /api/admin/leads` (cruzamento) e cria leads via `POST /api/admin/leads`. Em desenvolvimento local, opcionalmente usa MySQL direto se `DB_*` estiver no `.env`.

## Aviso

O scraping do Google Maps pode violar os termos de uso do Google. Use com responsabilidade e preferencialmente para prospecção interna.
