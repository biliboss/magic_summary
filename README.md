# Magic Summary

Magic Summary é um aplicativo desktop que **transcreve vídeos de feedback** (ex.: reuniões, entrevistas, apresentações) e gera **resumos estruturados com tópicos e destaques**, permitindo navegação direta pelo vídeo.

---

## ✨ Funcionalidades

* Upload de vídeos locais (`.mp4`, `.mkv`, `.mov`).
* Transcrição automática com **Whisper** (OpenAI ou local via `faster-whisper`).
* Geração de resumos estruturados usando **OpenAI GPT + Instructor**.
* Player integrado com navegação por tópicos.
* Exportação da transcrição completa em `.txt`.
* Cache automático de transcrições e resumos para reuso rápido.

---

## 📂 Estrutura do Projeto

```
magic-summary/
├── core/               # Serviços principais
│   ├── config.py       # Configuração e env
│   ├── models.py       # Domain models (Transcript, Summary, Metadata)
│   ├── storage.py      # Cache local de transcrições e resumos
│   ├── summarization.py# Serviço de resumo com OpenAI + Instructor
│   └── transcription.py# Serviço de transcrição (OpenAI Whisper ou local)
├── ui/                 # Interface desktop (PySide6)
│   ├── controller.py   # Orquestra serviços e UI
│   └── main_window.py  # Janela principal
├── docs/               # Documentação (PRD, UX/UI mockups)
├── main.py             # Entry point da aplicação
└── pyproject.toml      # Configuração do Poetry/uv
```

---

## 🚀 Instalação e Uso

### Pré-requisitos

* **Python 3.11+**
* **ffmpeg** instalado no sistema
* Chave da API da OpenAI (se usar backend OpenAI)

### Setup

```bash
# Clonar repositório
git clone https://github.com/seu-usuario/magic-summary.git
cd magic-summary

# Criar e ativar ambiente
uv venv
source .venv/bin/activate

# Instalar dependências
uv pip install -r pyproject.toml
```

### Configuração

Crie um arquivo `.env` na raiz com:

```
OPENAI_API_KEY=sk-xxxxxx
OPENAI_SUMMARY_MODEL=gpt-5-mini
OPENAI_WHISPER_MODEL=gpt-4o-mini-transcribe
TRANSCRIPTION_BACKEND=openai   # ou "local"
```

### Executar

```bash
python main.py
```

---

## 🖥️ Fluxo de Uso

1. Importar vídeo pela tela inicial (ou arrastar o arquivo).
2. Acompanhar progresso de transcrição e resumo.
3. Navegar pelos tópicos → clicar leva ao timestamp no player.
4. Exportar transcrição completa.

---

## 🔧 Tecnologias

* **Transcrição:** OpenAI Whisper API ou `faster-whisper` local
* **Resumo:** OpenAI GPT + `instructor` + Pydantic models
* **UI:** PySide6 (Qt)
* **Player:** VLC (`python-vlc`)
* **Cache:** JSON local em `data/transcripts/`

---

## 📖 Documentação

* [PRD](docs/prd.md) → escopo e requisitos da V1
* [UI](docs/ui.md) → protótipos ASCII das telas

---

## 🚧 Limitações da V1

* Exportação apenas `.txt`
* Interface básica, sem customização de temas
* Idiomas: português/inglês (dependente do Whisper)
* Sem edição manual de tópicos

---

## 📌 Roadmap Futuro

* Exportação em PDF/Word
* Edição manual dos tópicos
* Multi-idiomas automáticos
* Integração com Notion, Slack, Jira

---

## 📜 Licença

Este projeto é licenciado sob a [MIT License](LICENSE).
