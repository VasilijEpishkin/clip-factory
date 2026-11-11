# Новые инструменты ComfyUI и агентные навыки: что делают и как подключать

**Срез:** 11.11.2026. Проверены 7 открытых upstream репозиториев и их README. Ни один инструмент здесь не устанавливался, не запускался и не проверялся на совместимость с Clip Factory. Это **исследовательский каталог**, не список обязательных зависимостей.

[Карточки для агентов (JSON)](../studio-addons/research-comfyui-extensions-2026.json) · [Конкурс Open Source Higgsfield — 16 проектов](open-source-higgsfield-lab.md) · [Общая карта для агентов](AGENT_HANDBOOK.md)

## Решение о включении

Все **7** подтверждённых проектов **добавлены в каталог**, потому что закрывают отдельные задачи. **Ни один не добавлен в автоматическую базовую установку**. Nuke и After Effects — специализированные мосты, не нужны без этих программ.

| Инструмент | Для какой задачи нужен | Решение |
| --- | --- | --- |
| [ComfyUI Readable Node](https://github.com/nomadoor/comfyui-readable-node) | AI-агент объясняет и пересобирает непонятный граф нод, создаёт читабельный workflow | Изучать первым как **agent skill** |
| [ComfyUI-PhotoDeblur](https://github.com/porfeng/ComfyUI-PhotoDeblur) | Убирать смаз от дрожания/движения на фотографии до последующей обработки | Практичный фотоинструмент |
| [Director's Console](https://github.com/NickPittas/DirectorsConsole) | Вести раскадровку, кадры, промпты и ComfyUI-рендеры в «режиссёрском» интерфейсе с AI-агентом | Изучать архитектуру и UX |
| [NukeToComfyUI](https://github.com/NickPittas/NukeToComfyUI) | Передавать кадры, маски и видео между Nuke и ComfyUI | Хранить как **условный профессиональный мост** |
| [AE2ComfyUI](https://github.com/NickPittas/AE2ComfyUI) | Передавать композиции After Effects в ComfyUI и возвращать результат на таймлайн | Хранить как **условный профессиональный мост** |
| [Comfyui_Media](https://github.com/NickPittas/Comfyui_Media) | Загружать и экспортировать изображения/видео/EXR/ProRes в графе ComfyUI | Кандидат в media I/O; сравнить с VideoHelperSuite |
| [Camera Angle Selector](https://github.com/NickPittas/ComfyUI_CameraAngleSelector) | Выбирать ракурс, высоту и крупность плана для Qwen-Image-Edit Multiple-Angles-LoRA | Учебный модуль для постановки камеры |

## 1. ComfyUI Readable Node — навык для агента

**Задача:** получаешь большой запутанный ComfyUI workflow; просишь агента привести к понятной структуре. Навык может разбить многоцелевой граф на отдельные процессы, сделать явными скрытые связи, уменьшить количество custom nodes и пояснить логику.

**Вход:** `workflow.json` и запущенный ComfyUI с данными об установленных нодах. **Выход:** новый `*_readable.json` и интерактивный отчёт `report.html`. Оригинал не перезаписывается.

**Установка — выбрать один способ, НЕ несколько сразу:**

Для Claude Code (см. [upstream](https://github.com/nomadoor/comfyui-readable-node#install)):

```bash
claude plugin install comfyui-readable-node --marketplace nomadoor/comfyui-readable-node
```

Для Codex CLI:

```bash
codex plugin marketplace add nomadoor/comfyui-readable-node
codex plugin add comfyui-readable-node@comfyui-readable-node
```

Для других совместимых агентов (Node.js ≥22.20):

```bash
npx skills add nomadoor/comfyui-readable-node -g
```

Навык использует Python 3 (стандартная библиотека). Вызовить его можно через `/comfyui-readable-node` в поддерживаемых клиентах или запросом: «Сделай workflow.json читаемым, сохрани отдельный JSON и отчёт».

**Ограничения:** автор указывает около 10 минут для 25 нод, 20–40 минут для больших графов. Agent-generated изменения могут изменить поведение: обязательно сравнить исходный и новый workflow на одном входе. **Не добавлен** в `agent-stack/sources.json` без отдельного теста и закрепления ревизии.

## 2. ComfyUI-PhotoDeblur — восстановление фотографий со смазом

**Задача:** уменьшить шлейфы от рук/движущегося объекта. Две разные модели **HI-Diff** и **MISCFilter**; разбивка фото на перекрывающиеся тайлы без уменьшения разрешения, необязательная тоновая коррекция.

**Подходит:** вывески, архитектура, ночные огни, умеренный смаз. **Не рассчитан:** восстановить пересветы, расфокус и детали сильно размытых мелких лиц.

**Установка** (в `custom_nodes` **отдельной среды ComfyUI**, не в корневом `.venv` Clip Factory):

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/porfeng/ComfyUI-PhotoDeblur.git
cd ComfyUI-PhotoDeblur
# Выполняйте pip через Python, которым запускается именно ComfyUI:
python -m pip install -r requirements.txt
python -m pip install -r requirements-download.txt
# Для MISCFilter на NVIDIA CUDA 12 — дополнительно:
python -m pip install -r requirements-misc-cu12.txt
```

`python` здесь **не универсальная команда**: у ComfyUI Desktop/Portable может быть другой Python. После установки перезапустить ComfyUI, открыть `example_workflows/ComfyUI-PhotoDeblur.json`, выбрать фото и скачать нужные веса через ноду с проверкой SHA256.

**Первый тест:** RealBlur_J, tile=768, overlap=96, TTA=false. Сравнить обе модели на том же фото; TTA ~8× вычислений. Сохранять исходный файл и сравнение, не подменять оригинал.

**Связь с другими:** PhotoDeblur убирает **смаз**, Upscayl/Real-ESRGAN повышают **разрешение** — инструменты дополняют, а не заменяют друг друга.

## 3. Director's Console — режиссёрский пульт

**Задача:** составить художественный бриф с камерой, светом, движением, разложить сцены на карточки, запустить ComfyUI workflow по шотам, сравнить результаты в галерее. Есть встроенная работа с **Pi или Codex** как агентом. Поддержка других агентов не гарантирована.

**Установка** в отдельную папку (Python 3.11+, Node.js 22.13+ или 24+, Git):

```bash
git clone https://github.com/NickPittas/DirectorsConsole.git
cd DirectorsConsole
python start.py --setup
python start.py
```

Открыть `http://localhost:5173`. Для промптов ComfyUI не обязателен; **для генерации** должен быть настроен доступный ComfyUI с подходящими workflow и моделями.

**Исследовать:** чему учит управление режиссёрскими параметрами и shot-based workflow; сравнить с ComfyArt (свободный холст), Sonder Editor (таймлайн) и Imagination Studio (вся съёмочная группа).

## 4. KENT: мосты с профессиональными редакторами

### NukeToComfyUI

**Когда нужен:** профессиональный композитинг в **Foundry Nuke**: передача изображения/маски или диапазона кадров в ComfyUI; возврат PNG8/EXR16 и MOV/MP4. Нужны **установленные Nuke и ComfyUI**. Наличие Clip Factory недостаточно.

```bash
git clone https://github.com/NickPittas/NukeToComfyUI.git
cd NukeToComfyUI
python tools/install.py --dry-run --yes
# После проверки плана изменений:
python tools/install.py --yes
```

Установщик может изменять настройки Nuke и симлинки; сначала показать план `--dry-run`. Для видео нужны FFmpeg/ffprobe. Не публиковать unauthenticated bridge в интернет.

### AE2ComfyUI

**Когда нужен:** делать compositing/motion в **Adobe After Effects**, но отдельные кадры или клипы прогонять через ComfyUI. AE-панель отправляет полную композицию и маску и размещает результат над слоем на соответствующем времени. Для видео задействован Adobe Media Encoder.

```bash
git clone https://github.com/NickPittas/AE2ComfyUI.git
cd AE2ComfyUI
python3 tools/install.py --comfyui /path/to/ComfyUI --dry-run
# После изучения действия установщика:
python3 tools/install.py --comfyui /path/to/ComfyUI
```

Требует отдельного лицензируемого Adobe ПО, совместимого CEP-плагина и рестарта AE/ComfyUI. Результат зависит от формата (ProRes/PNG), альфы, FPS и цветового пространства.

**Оценка:** оба полезны как примеры правильного **двустороннего моста** между AI и профессиональными редакторами. Но они не нужны всем и **не заменяют** Remotion, FFmpeg или Kdenlive.

## 5. Comfyui_Media — вход/выход медиа

**Задача:** читать MOV/MP4, EXR/PNG/TIFF последовательности и аудио, просматривать, сравнивать и сохранять результаты (MP4 H.264, WebM VP9, ProRes, PNG/EXR, GIF/WebP). Поддерживает выравнивание количества кадров под WAN (4n+1), LTX 2.3 (8n+1), H3 (17n+5).

**Установка** (FFmpeg и ffprobe в PATH ComfyUI):

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/NickPittas/Comfyui_Media.git
```

Перезапустить ComfyUI и найти **Load Video/Sequence** и **Video Viewer/Saver**. **Пересечение:** уже изученный VideoHelperSuite выполняет часть этих задач. Испытать один и тот же MP4/EXR, сравнить поддержку альфы, звука, таймкодов и памяти до принятия решения.

## 6. ComfyUI Camera Angle Selector — выбор точки съёмки

**Задача:** выбрать из **96** комбинаций направления (8), высоты (4) и крупности (3) через интерактивную 3D-схему. Возвращает prompt-строки под **Qwen-Image-Edit-2511 Multiple-Angles-LoRA**.

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/NickPittas/ComfyUI_CameraAngleSelector.git
```

Перезапустить ComfyUI, добавить ноду **Camera Angle Selector**, выбрать ракурс. LoRA и совместимая модель устанавливаются отдельно.

**Не путать:** Camera Angle Selector формирует **подсказку на новый ракурс изображения**; Reshoot 4D действительно пытается переснимать сцену с новой виртуальной камеры. Это различные уровни управления.

## Идеи сочетаний

| Задача | Возможная цепочка | Что проверить |
| --- | --- | --- |
| Разобраться с чужим workflow | Readable Node → сравнение исходного/нового → ComfyUI | Исходный эффект и модели сохранились? |
| Постановка кадра | Director's Console + Camera Angle Selector → ComfyUI → Remotion | Совпадает ли угол/свет с заданием? |
| Улучшение размытого фото | PhotoDeblur → фото-редактор → Upscayl по необходимости | Выигрыш по чёткости без ложных деталей? |
| VFX с сохранением качества | Nuke → NukeToComfyUI → ComfyUI → Nuke | Alpha/EXR/FPS/colourspace не теряются? |
| Motion-дизайн | After Effects → AE2ComfyUI → ComfyUI → AE | Соответствие маски и тайминга? |
| Экспорт анимации | ComfyUI → Comfyui_Media → FFmpeg/Remotion | Цвет/альфа/аудио/кадровый формат? |

Все цепочки — **исследовательские гипотезы**: наличие интерфейсов ещё не доказывает их сквозную совместимость.

## Правила пополнения каталога для агента

1. Сначала проверить, существует ли upstream и что написано **в его README**, а не только в рекламном описании.
2. Определить уникальную **задачу**, вход и выход. Если инструмент уже полностью перекрыт существующим, записать как **альтернативу**, а не устанавливать вторую копию.
3. Присвоить решение: **принять как полезный**, **условно для узкой задачи**, **отложить до подтверждения** или **не добавлять**.
4. Для принятого инструмента заполнить русскую карточку в JSON: ссылка, назначение, вход, выход, установка, зависимости, ограничения, пересечения, решение и статус теста.
5. Добавить ссылку в этот справочник и [AGENT_HANDBOOK.md](AGENT_HANDBOOK.md). Предыдущие 16 инструментов остаются в [Open Source Higgsfield](open-source-higgsfield-lab.md).
6. Не менять `pyproject.toml`, npm lock, `agent-stack/sources.json` и ComfyUI custom nodes без отдельной задачи. **Каталог ≠ установленный инструмент.**
7. Для любого installed/working статуса требуется запуск и воспроизводимый результат, а не только изучение README.

## Что дальше изучать

**Первый сравнительный эксперимент:** взять один неизвестный workflow с ~20–25 нодами, дать Readable Node объяснить/пересобрать граф и оценить читаемость, соответствие выхода и время. **Второй:** два фото со смазом прогнать HI-Diff и MISCFilter. **Третий:** сравнить интерфейс Director's Console с ComfyArt и Sonder. Это даст реальные знания без обязательной установки всех 7 инструментов.
