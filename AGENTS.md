# clip-factory

Репозиторий включает код медиастудии, каталог инструментов и установщик
проектных скиллов. Для новой машины следуй README.md и docs/studio-stack.md.
Установка скиллов: `python3 agent-stack/install.py .`.

## Анализ рилсов / видео по ссылке (MCP `video-analyzer`)

Пользователь кидает ссылки на Instagram Reels (и YouTube), нужно вытащить из них информацию. Инструмент: MCP-сервер `video-analyzer` (mcp-video-analyzer), настроен в `.mcp.json`: Whisper `medium` на GPU через `tools/whisper-cli`, куки Instagram в `cookies.txt` (секрет, в git не класть), куки YouTube читаются из Chrome.

- **OCR: всегда передавать `ocrLanguage: "rus+eng"`.** По умолчанию стоит `eng+por`, и кириллица превращается в мусор. В CLI тот же параметр: `--ocr-language rus+eng`.
- **Не доверять OCR на графиках и стилизованном тексте.** Анализатор сохраняет кадры: открывай их через Read как картинки и читай уровни, цены, подписи, названия инструментов, ники и ссылки напрямую. OCR — только как подсказка.
- Речь берётся из транскрипта Whisper (русский распознаётся хорошо). Предупреждение «video may be DRM-protected» ложное: просто убран чёрный кадр.
- Ссылки чистить от трекинговых параметров: `https://www.instagram.com/reel/<id>/`.
- Если MCP недоступен, тот же анализ через CLI: `npx -y mcp-video-analyzer@latest analyze <url> --ocr-language rus+eng > work/reels/<id>.json` (env из `.mcp.json`). Длинные ролики идут дольше 5 минут, ставь таймаут побольше.
- Результаты кладутся в `work/reels/<id>.json`.
- Выжимка по каждому рилсу: о чём, ключевые шаги или правила, цифры, упомянутые инструменты и ссылки, реклама и призывы. Заявленные результаты (доходность, винрейт) не проверены: помечай это.

## Видео-инструменты в проекте
- `remotion/`: Remotion 4.0.484 (перенесён из ai-design-studio).
- `hyperframes/`: `npx hyperframes` (HTML в MP4), проверка: `npx hyperframes doctor`.
- `.venv`: faster-whisper, whisper-ctranslate2, scenedetect, mediapipe (`uv sync`).

## Окружение
- WSLg нестабилен: `weston` падает, окна из WSL не открываются. Вход в аккаунты делать в браузере Windows, куки экспортировать в `cookies.txt` (Netscape).

## Gemini <-> агенты через Google Drive
Протокол обмена (папка ClipFactory на Диске, Gemini Tasks генерирует фото/видео, агент монтирует): `docs/gemini-bridge.md`. Текст задачи для Gemini: `docs/gemini-task-prompt.md`.

Интеграции MCP, плагины и внешние генераторы подключай по `docs/studio-stack.md`.
Не коммить ключи, OAuth, cookies, локальные конфиги агентов, модели, кэши,
рабочие видео и рендеры.
