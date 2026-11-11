# Дополнения медиастудии

Каталог описывает программы, которые можно установить рядом с Clip Factory.
Он не скачивает сами программы, модели и плагины в репозиторий: upstream-код
остаётся у авторов, крупные веса скачиваются отдельно, а лицензии могут быть
разными даже у приложения и его моделей. Секреты и настройки подключения сюда
не помещать.

## Исследовательские каталоги — НЕ программы для автоматической установки

- [16 работ конкурса Open Source Higgsfield](research-open-source-higgsfield-2026.json) — [разбор по задачам](../docs/open-source-higgsfield-lab.md).
- [7 новых инструментов ComfyUI, agent skill и мостов](research-comfyui-extensions-2026.json) — [инструкции и решение о включении](../docs/comfyui-new-tools-2026.md).
- Общий поиск (4 реестра): `python3 scripts/studio_tools.py` или `python3 scripts/studio_tools.py --json`.

- [32 карточки про видеосуперразрешение, MOSS-Image и референсы](research-moss-vsr-2026.json) — [русскоязычный обзор с практическими задачами и оговорками](../docs/moss-vsr-2026.md).

**Поиск по всем пяти реестрам**: `python3 scripts/studio_tools.py`, для агентов — `python3 scripts/studio_tools.py --json`. Необязательные модели и ноды нельзя устанавливать без решения пользователя.

## Профили

| Профиль | Состав | Когда устанавливать |
|---|---|---|
| `local-generation` | ComfyUI + выбранные workflow/preset packs (первым для оценки — FreeField) | Нужна локальная генерация и есть NVIDIA GPU; запускать в отдельном окружении |
| `voice-production` | VoiceStudio | Нужны локальные TTS/дубляж; сначала проверить русский язык и права на модель/голос |
| `character-mocap` | MoCapAnything V2 | Требуется video-to-rigged-motion для 3D-персонажей |
| `host-dictation` | OpenWhispr | Нужен голосовой ввод текста в приложения на рабочем устройстве |
| `desktop-exploration` | Open Generative AI | Нужно сравнить интерфейс локальных/облачных генераторов с текущими средствами |

`AgentY` и название `ComfyUI-Agent` пока не привязаны к подтверждённым upstream
проектам. Ближайший найденный проект CrazyDashTool — `ComfyUI-AI-Assistant`;
перед установкой подтвердите, что имеется в виду он.

## Установка

### ComfyUI и FreeField

Устанавливать на отдельную Linux-машину или в отдельную папку/venv, не в `.venv`
Clip Factory. FreeField quick setup устанавливает свой ComfyUI и CUDA-зависимости,
скачивает десятки гигабайт моделей; требования конкретного workflow могут быть
выше минимальных. Перед выполнением скрипта установки прочитайте актуальный
upstream README, проверьте свободное место, GPU/VRAM и модельные лицензии.

1. Установите ComfyUI по [официальной инструкции](https://docs.comfy.org/installation/manual_install).
2. Запустите ComfyUI и убедитесь, что он работает независимо от Clip Factory.
3. Для FreeField следуйте [официальному quickstart](https://github.com/droppedmyza/freefield#quick-start).
4. Сначала скачайте только модели, нужные одному выбранному preset; не запускайте
   профиль на общей машине с ключами/чувствительными файлами без проверки кода.

### VoiceStudio

Скачайте официальный release под ОС с [GitHub Releases](https://github.com/debpalash/VoiceStudio/releases)
или используйте [инструкцию для агента](https://github.com/debpalash/VoiceStudio/blob/main/docs/install/agent.md).
Приложение и каждый загружаемый голос/модель проверяйте по своей лицензии.
Не клонируйте чей-либо голос без разрешения.

### OpenWhispr

Устанавливайте официальный desktop release из
[GitHub Releases](https://github.com/OpenWhispr/openwhispr/releases). Выберите
локальный движок распознавания, если аудио не должно уходить в облачный сервис.
Храните provider credentials только в локальном хранилище конкретного приложения.

### Open Generative AI

Скачайте установщик только с [официальных releases](https://github.com/Anil-matcha/Open-Generative-AI/releases).
До добавления в постоянную среду отдельно проверьте, какие функции идут локально,
какие вызывают внешние API и что сохраняет конкретная desktop-версия.

### MoCapAnything V2

Репозиторий [MoCapAnything V2](https://github.com/phongdaot/MocapAnything) —
чистая реимплементация метода, не исходный исследовательский код из статьи.
Следуйте его `RUN.md`, используйте отдельное Python/GPU окружение и скачивайте
weights в локальную папку проекта, не в Git. Лицензии кода и весов указаны как
MIT; отдельные сторонние assets/data имеют собственные условия. Blender для
некоторых mesh/custom-rig этапов устанавливается отдельно.

## Фиксация установленных версий

Этот каталог намеренно фиксирует upstream и метод установки, но не выбирает
движущуюся `main` за стабильный релиз и не устанавливает кандидатов автоматически.
После пилота записать проверенный release/tag или commit, ОС, GPU, версию драйвера,
команду doctor/smoke check и список моделей в отдельном профиле. Не включать в
общую установку до такого прогона. Ключи, OAuth-файлы и cookies не сохранять.
