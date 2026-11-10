# Clip Factory agent tool stack

Набор скиллов для медиастудии clip-factory. Эта папка входит в основной
репозиторий; установщик и закреплённые upstream-версии хранятся рядом с
инструкциями студии. Секреты, модели и медиафайлы сюда не входят.

## Быстрая установка скиллов

Нужны Git и Python 3.10+. Запускайте из корня `clip-factory`:

```bash
python3 agent-stack/install.py .
mkdir -p .claude
ln -s ../.agents/skills .claude/skills
```

Установщик клонирует указанные в `sources.json` публичные репозитории на закреплённые
ревизии в `.agent-stack/vendor/` и создаёт ссылки на скиллы в `.agents/skills/`.
Существующие файлы или ссылки не перезаписываются; при конфликте установка
останавливается с объяснением. Исходники остаются доступными в `.agent-stack/vendor/`.

Claude Code может читать те же скиллы через `.claude/skills -> ../.agents/skills`.
Создайте эту ссылку, если её нет:

```bash
ln -s ../.agents/skills .claude/skills
```

## Состав

- Монтаж: `ffmpeg-skill`, `video-shotcraft`, `anything2explainer`, `earshot`.
- YouTube: `youtube-agent-skill`.
- Исследования и промпты: `last30days-skill`, `prompt-master`, `seedance-2-prompts-search-skill`.
- Контент и рост: `brag`, `marketingskills`, `no-ai-slop`.
- Создание материалов: YouMind `create-image`, `create-slides`, `create-video`, `use-youmind-workspace`.

Версии источников и пути скиллов заданы в `sources.json`. Обновляйте ревизии
осознанно и проверяйте upstream-лицензии перед коммерческим использованием.

## Системные зависимости

Устанавливаются отдельно под ОС агента; этот репозиторий их не меняет:

- FFmpeg 6.1+ с `ffprobe` и libass для субтитров.
- Python 3.10+.
- Node.js 22 и npm для Remotion/Hyperframes.
- `uv` для Python-проектов.

Примеры проверки: `ffmpeg -version`, `ffprobe -version`, `node --version`,
`uv --version`. В WSL ставьте системные пакеты в WSL, где запускается агент.

## Рецепты для дополнительных инструментов

- Remotion: скопировать нужный проектный шаблон, затем `cd remotion && npm ci`.
- Hyperframes: `cd hyperframes && npm ci`, проверка `npx hyperframes doctor`.
- Локальная обработка и анализ в исходном clip-factory: `uv sync`; модели и
  GPU/CUDA настраиваются отдельно для конкретной машины.
- `video-analyzer`, YouTube MCP и Blender MCP требуют MCP-клиента и отдельной
  настройки. Не копируйте `.mcp.json` из исходного проекта: там локальные пути,
  включая путь к cookies. Подключайте инструменты в конфиге своего агента и
  храните авторизацию в его штатном секретном хранилище.

## Границы репозитория

Не включайте в этот репозиторий `cookies.txt`, `.env`, конфиги с ключами,
OAuth-токены, локальные модели, кэши, рендеры и исходные видеоматериалы.
Каталог инструментов, MCP, плагинов и способы интеграции с агентами описаны в
`docs/studio-stack.md`. Не добавляйте сюда `.env`, `cookies.txt`, OAuth,
ключи, `vendor` целиком, папки `work/`, `out/`, `video/`, локальные модели или
кэши.
