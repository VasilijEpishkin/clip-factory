# Clip Factory — стек медиастудии

Здесь собраны переносимые инструменты для исследования, подготовки,
производства и публикации видео. Git хранит исходники, lock-файлы, manifests и
инструкции. Авторизация и локальная конфигурация остаются на каждом устройстве.

## Установка на новой машине

1. Клонировать приватный `clip-factory`.
2. Установить Python 3.11+, `uv`, Node.js 22+, npm, Git, FFmpeg 6.1+ с
   `ffprobe` и libass. На Windows запускать проект внутри WSL2.
3. В корне выполнить `uv sync`, затем `npm ci` в `remotion/` и `hyperframes/`.
4. Скачать BlazeFace модель командой из корневого README в локальную папку
   `tools/`.
5. Запустить `python3 agent-stack/install.py .`. Скрипт скачает источники на
   закреплённых ревизиях и установит ссылки скиллов в `.agents/skills/`.
6. Для Claude Code создать `.claude/skills -> ../.agents/skills`. Codex читает
   `.agents/skills/` и корневой `AGENTS.md`.
7. Подключить нужные MCP-серверы и плагины отдельно для используемых агентов.

`.venv/`, `node_modules/`, `tools/`, `.agent-stack/`, `vendor/`, `work/`,
`out/` и медиаматериалы намеренно не входят в Git. Точные источники и ревизии
скиллов перечислены в [`agent-stack/sources.json`](../agent-stack/sources.json).

## Инструменты проекта

| Область | Инструмент | Установка / роль |
|---|---|---|
| Монтаж | FFmpeg + ffprobe | Системные пакеты; нужны libass и кодек H.264 |
| Python-пайплайн | `uv` + `uv.lock` | faster-whisper, MediaPipe, PySceneDetect, PyTorch/CUDA и экспорт таймлайнов; `uv sync` |
| Источники | yt-dlp | Установить в пользовательское окружение отдельно; соблюдать права площадок и авторов |
| Сборка видео | Remotion 4.0.484 | Исходники и npm lock в `remotion/`; `npm ci` |
| HTML-видео | Hyperframes 0.8.x | npm lock в `hyperframes/`; `npm ci`, проверка `npx hyperframes doctor` |
| Генератор | MoneyPrinterTurbo | Опционально; pinned upstream revision описан в README. Секретный `config.toml` создавать локально |

### Проектные скиллы

Источник — `agent-stack/sources.json`; установщик — `agent-stack/install.py`.

- Монтаж и звук: ffmpeg-skill, Video Shotcraft, Anything2Explainer, Earshot.
- YouTube: аудит, сценарии, монтаж, удержание, упаковка, метаданные и Shorts.
- Исследования и промпты: last30days, Prompt Master, Seedance prompt search.
- Контент: Marketing Skills, Brag, No AI Slop.
- Создание материалов: YouMind image, slides, video и workspace skills.

Лицензии upstream различаются. Перед коммерческим применением проверяйте
лицензию конкретного проекта и скилла, особенно Anything2Explainer.

## Подключение к агентам

### Codex

- Открыть корень репозитория как проект; инструкции находятся в `AGENTS.md`.
- Выполнить установщик скиллов; Codex читает `.agents/skills/`.
- MCP-серверы настраивать через MCP settings используемой версии Codex.

### Claude Code

- Проектные инструкции находятся в `CLAUDE.md`.
- После установки скиллов создать `.claude/skills -> ../.agents/skills`.
- MCP-серверы и плагины подключать через поддерживаемые настройки и plugin
  marketplace Claude Code. Авторизационные значения хранить вне репозитория.

### Другие агенты

Использовать Markdown скиллы из `.agents/skills/`. Если агент не обнаруживает
этот каталог, добавить ссылку или копию в его документированный skills path.
Формат MCP-конфига брать из документации именно этого клиента.

## MCP и локальные интеграции

Установка и авторизация делаются отдельно на каждой машине:

- **video-analyzer**: `npx -y mcp-video-analyzer@latest`. Для OCR всегда
  передавать `ocrLanguage: "rus+eng"`. Whisper, GPU, `WHISPER_BIN` и источник
  cookies/browser задаются локально.
- **YouTube Studio MCP**: пакет `youtube-studio-mcp`; требует пользовательский
  OAuth. Токены не коммитить.
- **Blender MCP**: `blender-mcp --transport stdio`; также нужен установленный
  и запущенный Blender.
- **Gemini + Google Drive bridge**: rclone и локальная авторизация Google;
  протокол описан в `docs/gemini-bridge.md`.

Настройки Codex, Claude Code и других клиентов различаются. Готовый рабочий
`.mcp.json`, `config.toml`, токены, OAuth-файлы, cookies и абсолютные пути сюда
не входят.

## Плагины и внешние приложения

Подключать в каталоге приложений или плагинов своего агента. Доступность зависит
от платформы, аккаунта и тарифа; эти интеграции не устанавливаются `uv sync`.

| Приложение / плагин | Использование |
|---|---|
| Canva | Дизайн и графика |
| Higgsfield | Генерация изображений и видео |
| HeyGen | Видео с ведущим и аватарами |
| YouTube, vidIQ | Канал, публикация, аналитика и идеи |
| Metricool | Планирование публикаций в соцсетях |
| YouMind | Исследование и создание image/slides/video |
| Claude Code: claude-seo, openseo | SEO и видимость контента |
| Claude Code: Superpowers, ECC | Дополнительные агентские и media workflows; опционально |

Устанавливайте только необходимые расширения и выдавайте минимальные scopes.
Проверяйте стоимость внешней генерации и публикаций отдельно.

## Не хранить в Git

Не добавлять `.env` с реальными значениями, `cookies*.txt`, OAuth или client
secret файлы, ключи API, локальные профили MCP/агентов, модели, кэши,
материалы с Drive, исходные видео и готовые рендеры. При утечке ключ отозвать у
провайдера: удаления из последнего коммита недостаточно.
