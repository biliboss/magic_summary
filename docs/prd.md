# PRD – Video Feedback Summarizer (Desktop App)

## 1. Objetivo
Permitir que usuários importem vídeos de feedback (reuniões, apresentações, entrevistas), tenham a transcrição automática, um sumário com tópicos clicáveis e navegação direta no vídeo.

---

## 2. Público-alvo
- Times de produto/UX que recebem feedback em vídeo.
- Pequenas equipes que precisam consumir feedback de forma rápida.

---

## 3. Escopo da V1
- **Input:** upload/drag&drop de arquivos de vídeo locais (MP4, MKV, MOV).
- **Processamento:**
  - Transcrição automática via Whisper (OpenAI).
  - Geração de sumário estruturado em tópicos com timestamps.
- **Output UX:**
  - Player embutido simples (play/pause, barra de progresso).
  - Lista lateral de tópicos clicáveis → ao clicar, o player pula pro ponto do vídeo.
  - Exportar transcrição completa em `.txt`.

---

## 4. Requisitos Técnicos

### Linguagem & Framework
- **Python 3.11+**
- **Interface:** PySide6 ou PyQt6 (GUI desktop cross-platform).
- **Player de vídeo:** VLC python bindings (`python-vlc`) para estabilidade.
- **IA:**  
  - OpenAI Whisper para transcrição (`whisper` lib).  
  - OpenAI GPT para sumarização (API ou modelo local).

### Estrutura Interna
- `ui/` → componentes gráficos (janela principal, player, lista de tópicos).
- `core/` → lógica de transcrição e resumo.
- `export/` → funções de exportação (txt/json).
- `assets/` → ícones, estilo da interface.

---

## 5. UX Flow

### Tela Inicial
- Janela limpa com botão central: “Importar vídeo” + suporte a drag&drop.
- Ao selecionar vídeo → preview carregado no player.

### Processamento
- Barra de progresso + loading state (“Transcrevendo…” → “Gerando sumário…”).
- Mensagens claras (sem jargão técnico).

### Resultado
- **Lado esquerdo:** Player do vídeo.  
- **Lado direito:** Lista de tópicos (ex: “1. Problema na tela de login [00:01:23]”).  
- Clique no tópico → vídeo pula para o timestamp correspondente.  
- Botão “Exportar Transcrição” no rodapé.

---

## 6. Critérios de Aceite
- Upload de vídeos até 1h processados sem crash.
- Transcrição automática exibida corretamente.
- Sumário deve ter no mínimo 5 tópicos para vídeos >5min.
- Clicar em um tópico deve levar ao ponto exato do vídeo.
- Exportação `.txt` deve conter texto completo da transcrição.

---

## 7. Limitações da V1
- Não há edição manual dos tópicos.
- Apenas exportação `.txt` (sem PDF/Word).
- Interface simples, sem temas customizados.
- Apenas idioma **português/inglês** (dependente do Whisper).

---

## 8. Futuro (fora da V1)
- Exportação multi-formato (PDF, Word).
- Edição manual dos tópicos.
- Multi-idioma automático.
- Integração com ferramentas de time (Notion, Slack, Jira).
