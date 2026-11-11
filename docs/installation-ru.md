# Установка Clip Factory на Linux / Xubuntu / WSL2

## 1. Установите системные программы

Для Ubuntu/Xubuntu и Debian-подобных систем:

```bash
sudo apt update
sudo apt install -y git curl python3 python3-venv ffmpeg
```

**Проверьте версию Python:** `python3 --version`. Нужна **3.11 или новее**. Если в вашей версии ОС установлен более старый Python, сначала обновите его поддерживаемым для вашего дистрибутива способом. Не заменяйте системный Python вручную.

Проверьте FFmpeg:

```bash
ffmpeg -version
ffprobe -version
ffmpeg -filters | grep subtitles
```

Для прожига субтитров нужна сборка FFmpeg с **libass**. Если фильтра `subtitles` нет, текущий пакет не подходит.

Установите **Node.js 22 или новее** и npm по [официальной инструкции Node.js](https://nodejs.org/en/download). Дистрибутивный `apt install nodejs` может поставить слишком старую версию. Проверьте `node --version` и `npm --version`.

Установите менеджер Python-пакетов `uv` по [официальной инструкции](https://docs.astral.sh/uv/getting-started/installation/), затем проверьте `uv --version`. Не выполняйте неизвестные команды установки от имени root.

## 2. Скачайте проект

```bash
git clone https://github.com/VasilijEpishkin/clip-factory.git
cd clip-factory
```

Если GitHub запросил доступ, используйте авторизацию GitHub или настроенный SSH-ключ. Не сохраняйте токены в репозитории.

## 3. Установите базовые зависимости

```bash
uv sync
(cd remotion && npm ci)
(cd hyperframes && npm ci)
mkdir -p tools
curl -fL -o tools/blaze_face_short_range.tflite \
  https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/latest/blaze_face_short_range.tflite
```

Загрузка модели BlazeFace — сетевое действие; проверьте источник и размер перед использованием в критичной среде. Для первого запуска может потребоваться дополнительная установка `yt-dlp` и LLM-клиента (Hermes/Codex/Claude). Их способ настройки зависит от конкретного аккаунта.

## 4. Проверка

```bash
python3 scripts/studio_doctor.py
.venv/bin/python -m pytest -q
```

Диагностика может отметить `yt-dlp` отсутствующим: это отдельная утилита для загрузки разрешённых источников, её можно установить через `uv tool install yt-dlp` после установки uv. Отсутствие Hermes, Claude, Codex или Blender не мешает работе Python-зависимостей, но выбор интересных фрагментов требует доступного LLM-клиента.

## 5. Как запустить видеоконвейер

Используйте **свои или разрешённые к обработке материалы**:

```bash
.venv/bin/python clip.py fetch URL --id demo
.venv/bin/python clip.py transcribe demo
.venv/bin/python clip.py highlights demo
.venv/bin/python clip.py edit demo
.venv/bin/python clip.py qa demo
```

Замените `URL` на адрес исходного видео. Для команды `highlights` настройте поддерживаемый LLM-клиент. Результат появится в `out/demo/`. Автоматической публикации нет.

## 6. Windows и macOS

- **Windows:** рекомендуемый путь — WSL2 с Ubuntu, далее инструкция выше внутри WSL2. Для GUI-редакторов (Kdenlive, ComfyUI Desktop) используйте их нативные установщики.
- **macOS:** этот проект не имеет подтверждённого end-to-end теста на macOS. Проверяйте совместимость CUDA-зависимостей и альтернативные CPU/MPS backend отдельно.

## 7. Дополнительные программы — только по задаче

ComfyUI, FreeField, Rembg, Blender, Kdenlive и остальные программы **не устанавливаются** командой `uv sync`. Для них смотрите [справочник](tools-ru.md).

**Внимание:** установка на вашем ноутбуке с 8 ГБ оперативной памяти не равнозначна возможности локально запускать тяжёлые модели генерации. Сначала оцените RAM, видеокарту, VRAM и свободное место. В отсутствие подходящего GPU лучше начать с FFmpeg, Kdenlive и лёгких CPU-инструментов.
