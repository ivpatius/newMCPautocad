# 🤖 AutoCAD AI Assistant

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://python.org)
[![AutoCAD](https://img.shields.io/badge/AutoCAD-2010--2025-lightgrey.svg)](https://autodesk.com)
[![Ollama](https://img.shields.io/badge/Ollama-LLM-orange.svg)](https://ollama.ai)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)

> 🇷🇺 **Интеллектуальный ассистент для работы с AutoCAD через естественный язык**  
> Полное извлечение данных, типизированные структуры, кэширование, анализ геометрии и интеграция с локальными LLM (Ollama).

---

## 📑 Содержание

1. [Возможности](#-возможности)
2. [Полный список функций по модулям](#-полный-список-функций-по-модулям)
3. [Установка](#-установка)
4. [Конфигурация](#-конфигурация)
5. [Использование](#-использование)
6. [Примеры запросов](#-примеры-запросов)
7. [Архитектура проекта](#-архитектура-проекта)
8. [Режимы работы](#-режимы-работы)
9. [Производительность](#-производительность)
10. [Troubleshooting](#-troubleshooting)
11. [Вклад в проект](#-вклад-в-проект)
12. [Лицензия](#-лицензия)

---

## ✨ Возможности

| Категория | Функции |
|-----------|---------|
| 📥 **Извлечение данных** | Полная геометрия, свойства, bounding box, XData, Extension Dictionary |
| 🗂️ **Типизация** | Dataclasses для всех структур данных |
| ⚡ **Кэширование** | O(1) поиск по handle, фильтрация, JSON-сохранение |
| 🧠 **LLM интеграция** | 12 инструментов с JSON Schema, 9 типов запросов |
| 📐 **Анализ геометрии** | Поиск связей, кластеризация, пространственные запросы |
| 🎨 **Управление CAD** | Рисование примитивов, управление слоями, команды |
| 🛡️ **Обработка ошибок** | Комплексное логирование, fallback-режимы |
| 🔌 **Режимы работы** | С AutoCAD (COM) или только кэш (без AutoCAD) |

---

## 📋 Полный список функций по модулям

### 📁 Модуль `src/cad/dataclasses.py`

#### Класс `BoundingBox`
| Метод/Свойство | Тип | Описание |
|----------------|-----|----------|
| `min_x, min_y, min_z` | `float` | Минимальные координаты |
| `max_x, max_y, max_z` | `float` | Максимальные координаты |
| `center` | `property` | Центр bounding box (tuple) |
| `size` | `property` | Размеры по осям (tuple) |
| `to_dict()` | `method` | Конвертация в словарь |
| `from_dict()` | `classmethod` | Создание из словаря |

#### Класс `Coordinates`
| Атрибут | Тип | Описание |
|---------|-----|----------|
| `start` | `Optional[List[float]]` | Начальная точка (для линий) |
| `end` | `Optional[List[float]]` | Конечная точка (для линий) |
| `center` | `Optional[List[float]]` | Центр (для кругов, дуг) |
| `insertion` | `Optional[List[float]]` | Точка вставки (для блоков, текста) |
| `vertices` | `List[List[float]]` | Вершины (для полилиний) |
| `point` | `Optional[List[float]]` | Точка (для AcDbPoint) |
| `to_dict()` | `method` | Конвертация в словарь |

#### Класс `EntityProperties`
| Атрибут | Тип | Описание |
|---------|-----|----------|
| `handle` | `str` | Уникальный идентификатор объекта |
| `object_name` | `str` | Тип объекта (AcDbLine, AcDbCircle...) |
| `layer` | `str` | Имя слоя |
| `color` | `int` | ACI цвет (1-255) |
| `linetype` | `str` | Тип линии |
| `lineweight` | `Optional[int]` | Вес линии |
| `transparency` | `Optional[int]` | Прозрачность |
| `visible` | `bool` | Видимость объекта |
| `bounding_box` | `Optional[BoundingBox]` | Ограничивающий прямоугольник |
| `area` | `Optional[float]` | Площадь объекта |
| `length` | `Optional[float]` | Длина объекта |
| `volume` | `Optional[float]` | Объём объекта |
| `coordinates` | `Coordinates` | Координаты объекта |
| `xdata` | `Optional[Dict]` | Расширенные данные (XData) |
| `extension_dict` | `Optional[Dict]` | Словарь расширений |
| `type_properties` | `Dict[str, Any]` | Свойства специфичные для типа |
| `error` | `Optional[str]` | Ошибка извлечения (если была) |
| `to_dict()` | `method` | Конвертация в словарь |
| `from_dict()` | `classmethod` | Создание из словаря |

#### Класс `LayerInfo`
| Атрибут | Тип | Описание |
|---------|-----|----------|
| `name` | `str` | Имя слоя |
| `color` | `int` | ACI цвет |
| `linetype` | `str` | Тип линии |
| `lineweight` | `int` | Вес линии |
| `is_on` | `bool` | Слой включён |
| `is_frozen` | `bool` | Слой заморожен |
| `is_locked` | `bool` | Слой заблокирован |
| `viewport_frozen` | `bool` | Заморожен в видовом экране |
| `plot` | `bool` | Печатается ли слой |
| `description` | `str` | Описание слоя |
| `to_dict()` | `method` | Конвертация в словарь |

#### Класс `BlockReference`
| Атрибут | Тип | Описание |
|---------|-----|----------|
| `handle` | `str` | Уникальный идентификатор |
| `name` | `str` | Имя блока |
| `effective_name` | `str` | Эффективное имя (для динамических) |
| `layer` | `str` | Слой размещения |
| `insertion_point` | `List[float]` | Точка вставки [x, y, z] |
| `scale_x, scale_y, scale_z` | `float` | Коэффициенты масштабирования |
| `rotation` | `float` | Угол поворота (радианы) |
| `attributes` | `List[Dict]` | Атрибуты блока |
| `to_dict()` | `method` | Конвертация в словарь |

#### Класс `TextEntity`
| Атрибут | Тип | Описание |
|---------|-----|----------|
| `handle` | `str` | Уникальный идентификатор |
| `text` | `str` | Текстовое содержимое |
| `layer` | `str` | Слой размещения |
| `height` | `float` | Высота текста |
| `style` | `str` | Имя текстового стиля |
| `position` | `List[float]` | Позиция [x, y, z] |
| `alignment` | `Any` | Выравнивание |
| `rotation` | `float` | Угол поворота |
| `width` | `Optional[float]` | Ширина (для MText) |
| `attachment_point` | `Optional[int]` | Точка привязки |
| `to_dict()` | `method` | Конвертация в словарь |

#### Класс `DimensionEntity`
| Атрибут | Тип | Описание |
|---------|-----|----------|
| `handle` | `str` | Уникальный идентификатор |
| `dim_type` | `int` | Тип размера (0-6) |
| `measurement` | `float` | Измеренное значение |
| `text` | `str` | Текст размера |
| `style` | `str` | Имя размерного стиля |
| `scale_factor` | `float` | Масштабный коэффициент |
| `position` | `List[float]` | Позиция [x, y, z] |
| `rotation` | `float` | Угол поворота |
| `center` | `Optional[List[float]]` | Центр (для радиальных) |
| `radius` | `Optional[float]` | Радиус (для радиальных) |
| `to_dict()` | `method` | Конвертация в словарь |

#### Класс `DrawingMetadata`
| Атрибут | Тип | Описание |
|---------|-----|----------|
| `drawing_name` | `Optional[str]` | Имя файла чертежа |
| `drawing_path` | `Optional[str]` | Полный путь к файлу |
| `last_update` | `Optional[str]` | Дата последнего обновления |
| `acad_version` | `Optional[str]` | Версия AutoCAD |
| `created_by` | `Optional[str]` | Автор чертежа |
| `to_dict()` | `method` | Конвертация в словарь |

#### Класс `EntityCache`
| Атрибут | Тип | Описание |
|---------|-----|----------|
| `entities` | `Dict[str, EntityProperties]` | Все сущности по handle |
| `blocks` | `Dict[str, BlockReference]` | Все блоки по handle |
| `texts` | `Dict[str, TextEntity]` | Все тексты по handle |
| `dimensions` | `Dict[str, DimensionEntity]` | Все размеры по handle |
| `layers` | `Dict[str, LayerInfo]` | Все слои по имени |
| `metadata` | `DrawingMetadata` | Метаданные чертежа |
| `last_updated` | `Optional[datetime]` | Время последнего обновления |
| `get_entity_by_handle()` | `method` | Быстрый поиск по handle (O(1)) |
| `get_all_entities_by_layer()` | `method` | Все сущности на слое |
| `get_all_entities_by_type()` | `method` | Все сущности по типу |
| `find_entities_in_bbox()` | `method` | Поиск в bounding box |
| `to_dict()` | `method` | Конвертация в словарь |

---

### 📁 Модуль `src/cad/autocad_client.py`

#### Класс `AutoCADClient`

| Метод | Параметры | Возвращает | Описание |
|-------|-----------|------------|----------|
| `__init__()` | — | — | Инициализация клиента |
| `connect()` | — | `bool` | Подключение к запущенному AutoCAD |
| `is_connected` | `property` | `bool` | Статус подключения |
| `_to_variant()` | `point: Tuple` | `VARIANT` | Конвертация точки в COM-массив |
| `add_line()` | `start, end: Tuple` | `object` | Создать линию |
| `add_circle()` | `center: Tuple, radius: float` | `object` | Создать круг |
| `add_point()` | `point: Tuple` | `object` | Создать точку |
| `add_arc()` | `center, radius, start_angle, end_angle` | `object` | Создать дугу |
| `add_spline()` | `points: List, start_angle, end_angle` | `object` | Создать сплайн |
| `create_layer()` | `name: str, color: int` | `object` | Создать/обновить слой |
| `rename_layer()` | `old_name, new_name: str` | `bool` | Переименовать слой |
| `change_layer_color()` | `name: str, color: int` | `bool` | Изменить цвет слоя |
| `get_layers_info()` | — | `List[LayerInfo]` | Получить информацию о слоях |
| `set_layer_status()` | `name: str, is_on: bool` | `bool` | Включить/выключить слой |
| `get_all_entities_detailed()` | `include_xdata, include_dict: bool` | `List[EntityProperties]` | Полное извлечение всех сущностей |
| `_extract_entity_full()` | `ent, include_xdata, include_dict` | `EntityProperties` | Извлечение одного объекта |
| `_get_bounding_box()` | `ent` | `BoundingBox` | Получение bounding box |
| `_extract_coordinates()` | `ent` | `Coordinates` | Извлечение координат |
| `_extract_type_properties()` | `ent` | `Dict` | Извлечение тип-свойств |
| `_extract_xdata()` | `ent` | `Dict` | Извлечение XData |
| `_extract_extension_dict()` | `ent` | `Dict` | Извлечение Extension Dictionary |
| `trim()` | — | — | Вызов команды TRIM |
| `send_command()` | `command: str` | `bool` | Отправка команды в AutoCAD |
| `get_drawing_bounds()` | — | `Dict` | Границы чертежа (LIMMIN/LIMMAX/EXTMIN/EXTMAX) |
| `get_drawing_metadata()` | — | `DrawingMetadata` | Метаданные чертежа |

---

### 📁 Модуль `src/cad/drawing_cache.py`

#### Класс `DrawingCache`

| Метод | Параметры | Возвращает | Описание |
|-------|-----------|------------|----------|
| `__init__()` | `acad_client: AutoCADClient` | — | Инициализация кэша |
| `full_cache_update()` | — | — | Полное обновление кэша |
| `_categorize_entities()` | `entities: List` | — | Категоризация по типам |
| `_convert_to_block()` | `entity: EntityProperties` | `BlockReference` | Конвертация в блок |
| `_convert_to_text()` | `entity: EntityProperties` | `TextEntity` | Конвертация в текст |
| `_convert_to_dimension()` | `entity: EntityProperties` | `DimensionEntity` | Конвертация в размер |
| `_save_cache()` | — | — | Сохранение в JSON |
| `_generate_summary()` | — | — | Генерация статистики |
| `get_entity_by_handle()` | `handle: str` | `EntityProperties` | Поиск по handle |
| `get_entities_by_layer()` | `layer: str` | `List[EntityProperties]` | Поиск по слою |
| `get_entities_by_type()` | `object_name: str` | `List[EntityProperties]` | Поиск по типу |
| `find_in_bbox()` | `bbox: BoundingBox` | `List[EntityProperties]` | Поиск в bounding box |
| `find_connected_lines()` | `tolerance: float` | `Dict[str, List[str]]` | Поиск соединённых линий |
| `find_nearby_entities()` | `point, distance` | `List[EntityProperties]` | Поиск в радиусе |
| `load_cache()` | `static` | `Dict` | Загрузка кэша из файла |

---

### 📁 Модуль `src/cad/geometry_analysis.py`

#### Класс `GeometryAnalyzer`

| Метод | Параметры | Возвращает | Описание |
|-------|-----------|------------|----------|
| `calculate_combined_bbox()` | `entities: List` | `BoundingBox` | Объединённый bounding box |
| `find_intersecting_entities()` | `entities, target` | `List[EntityProperties]` | Пересекающиеся объекты |
| `_bbox_intersects()` | `box1, box2: BoundingBox` | `bool` | Проверка пересечения bbox |
| `find_nearby_entities()` | `entities, point, distance` | `List[EntityProperties]` | Объекты вблизи точки |
| `find_entities_by_layer()` | `entities, layer` | `List[EntityProperties]` | Фильтр по слою |
| `find_entities_by_type()` | `entities, object_name` | `List[EntityProperties]` | Фильтр по типу |
| `find_connected_lines()` | `entities, tolerance` | `Dict[str, List[str]]` | Соединённые линии |
| `_points_near()` | `p1, p2, tolerance` | `bool` | Близость точек |
| `group_entities_by_spatial_proximity()` | `entities, max_distance` | `List[List[EntityProperties]]` | Кластеризация |
| `_entities_near()` | `e1, e2, max_distance` | `bool` | Близость сущностей |
| `calculate_statistics()` | `entities` | `Dict` | Статистика по сущностям |

---

### 📁 Модуль `src/llm/llm_manager.py`

#### Класс `LLMManager`

| Метод | Параметры | Возвращает | Описание |
|-------|-----------|------------|----------|
| `__init__()` | — | — | Инициализация менеджера |
| `get_tool_definitions()` | — | `List[Dict]` | Определения 12 инструментов |
| `get_drawing_info()` | `query_type, entity_type, layer, handle, block_name, property_filter, include_details, aggregate, limit` | `str` | Запрос к кэшу (9 типов) |
| `process_prompt()` | `prompt: str` | `Tuple[List[Dict], str]` | Обработка запроса LLM |
| `_parse_fallback_tool_calls()` | `content: str` | `List[Dict]` | Fallback-парсинг tool calls |
| `execute_tool()` | `tool_call, cad_client` | `str` | Выполнение инструмента |

#### 🛠️ Инструменты LLM (12 шт.)

| Инструмент | Параметры | Описание |
|------------|-----------|----------|
| `draw_line` | `start, end, layer` | Нарисовать линию |
| `draw_circle` | `center, radius, layer` | Нарисовать круг |
| `draw_point` | `point, layer` | Поставить точку |
| `draw_arc` | `center, radius, start_angle, end_angle, layer` | Нарисовать дугу |
| `draw_spline` | `points, start_angle, end_angle, layer` | Нарисовать сплайн |
| `list_layers` | — | Список всех слоёв |
| `set_layer_status` | `layer_name, is_on` | Вкл/выкл слой |
| `create_layer` | `layer_name, color` | Создать слой |
| `rename_layer` | `old_name, new_name` | Переименовать слой |
| `change_layer_color` | `layer_name, color` | Изменить цвет слоя |
| `get_drawing_info` | `query_type, ...` | Запрос к кэшу |

#### 📊 Типы запросов `get_drawing_info` (9 шт.)

| query_type | Описание | Параметры |
|------------|----------|-----------|
| `summary` | Общая статистика чертежа | — |
| `entities` | Список геометрических объектов | `entity_type, layer, include_details, limit` |
| `blocks` | Вхождения блоков | `layer, block_name, limit` |
| `texts` | Текстовые объекты | `layer, limit` |
| `dimensions` | Размерные объекты | `layer, limit` |
| `layers` | Информация о слоях | `include_details, limit` |
| `filtered` | Гибкая фильтрация | `layer, entity_type, block_name, property_filter, limit` |
| `aggregate` | Агрегация данных | `field, function, entity_type, layer` |
| `by_handle` | Поиск по handle | `handle` |

#### 🎯 Операторы `property_filter`

| Оператор | Описание | Пример |
|----------|----------|--------|
| `==` | Равно | `{"field": "layer", "operator": "==", "value": "Walls"}` |
| `>` | Больше | `{"field": "length", "operator": ">", "value": 100}` |
| `<` | Меньше | `{"field": "area", "operator": "<", "value": 50}` |
| `>=` | Больше или равно | `{"field": "radius", "operator": ">=", "value": 10}` |
| `<=` | Меньше или равно | `{"field": "height", "operator": "<=", "value": 5}` |
| `contains` | Содержит подстроку | `{"field": "text", "operator": "contains", "value": "NOTE"}` |

#### 📈 Функции агрегации `aggregate.function`

| Функция | Описание | Пример |
|---------|----------|--------|
| `sum` | Сумма значений | `{"field": "length", "function": "sum"}` |
| `avg` | Среднее значение | `{"field": "area", "function": "avg"}` |
| `min` | Минимальное значение | `{"field": "radius", "function": "min"}` |
| `max` | Максимальное значение | `{"field": "area", "function": "max"}` |
| `count` | Количество объектов | `{"field": "handle", "function": "count"}` |

---

### 📁 Модуль `main.py`

| Функция | Параметры | Возвращает | Описание |
|---------|-----------|------------|----------|
| `ensure_com_initialized()` | — | — | Инициализация COM в потоке |
| `main()` | — | — | Главный цикл приложения |

#### Команды консольного интерфейса

| Команда | Описание |
|---------|----------|
| `full_cache` / `обнови всё` / `update cache` | Обновить кэш из AutoCAD |
| `exit` / `quit` / `выход` | Выйти из программы |
| Любой текстовый запрос | Обработка через LLM |

---


### Пошаговая установка

```powershell
# 1. Клонировать репозиторий
git clone https://github.com/ivpatius/newMCPautocad.git
cd newMCPautocad

# 2. Создать виртуальное окружение
python -m venv venv

# 3. Активировать окружение
# Windows PowerShell
.\venv\Scripts\Activate.ps1
# Windows CMD
.\venv\Scripts\activate.bat
# Linux/Mac
source venv/bin/activate

# 4. Установить зависимости
pip install -r requirements.txt

# 5. Установить Ollama (если нет)
# Скачать с https://ollama.ai

# 6. Загрузить модель
ollama pull qwen2.5-coder:7b

# 7. Создать файл конфигурации
cp .env.example .env

# 8. Запустить ассистент
python main.py