# WebRP-Extrator

Aplicativo **desktop** (Windows e Linux) para extrair empresas no **Google Maps** com **Playwright** e importar leads diretamente no painel **WebRP**.

Distribuído via `extrator.webriopreto.com` (instalador). Não roda na Hostinger — executa no computador do usuário.

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

## Variáveis de ambiente (`.env`)

| Variável | Descrição |
|---|---|
| `WEBRP_URL` | URL do WebRP (padrão `https://webriopreto.com`) |
| `WEBRP_EMAIL` | Pré-preenche login (opcional, dev) |
| `WEBRP_SENHA` | Pré-preenche login (opcional, dev) |
| `GEMINI_API_KEY` | Sugestões via Gemini (opcional) |
| `GEMINI_MODEL` | Modelo Gemini (padrão `gemini-2.0-flash`) |

## Build do instalável

### Automático (GitHub Actions — recomendado)

O repositório gera builds **Windows** e **Linux** na nuvem (sem precisar de Windows local).

**Download manual (teste):**

1. GitHub → **Actions** → workflow **Build releases** → **Run workflow**
2. Ao terminar, baixe os artefatos `WebRP-Extrator-windows` e `WebRP-Extrator-linux`

**Release oficial (link para usuários):**

```bash
git tag v1.1.0
git push origin v1.1.0
```

Isso cria um [GitHub Release](https://github.com/kaueajure/extrator/releases) com:

- `WebRP-Extrator-windows.zip` — extrair e abrir `WebRP-Extrator.bat`
- `WebRP-Extrator-linux.tar.gz` — extrair e rodar `./webrp-extrator.sh`

O Chromium do Playwright já vem na pasta `ms-playwright` dentro do pacote.

### Linux (local)

```bash
./instalar
chmod +x build/build-linux.sh
./build/build-linux.sh
```

Saída em `dist/WebRP-Extrator/`.

### Windows (local)

Só em máquina Windows, ou use o GitHub Actions acima.

```powershell
pip install -e .
pip install pyinstaller
pyinstaller build\webrp-extrator.spec --noconfirm
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

O app **não conecta ao MySQL**. Autentica via `POST /api/admin/login` e cria leads via `POST /api/admin/leads` no servidor WebRP (local ou produção).

## Aviso

O scraping do Google Maps pode violar os termos de uso do Google. Use com responsabilidade e preferencialmente para prospecção interna.
