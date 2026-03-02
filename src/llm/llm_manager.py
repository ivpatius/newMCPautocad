import json
import os
import ollama
from dotenv import load_dotenv
from ..cad.drawing_cache import DrawingCache

# Load environment variables
load_dotenv()


class LLMManager:
    def __init__(self):
        self.model = os.getenv("OLLAMA_MODEL", "qwen3:latest")
        self.api_url = os.getenv("LLM_API_URL", 'http://localhost:11434/')

        if self.api_url:
            self.api_url = self.api_url.strip().rstrip('/')
            for suffix in ['/api/generate', '/api/chat', '/api']:
                if self.api_url.endswith(suffix):
                    self.api_url = self.api_url[:-len(suffix)]
            self.client = ollama.Client(host=self.api_url)
        else:
            self.client = ollama

    def get_tool_definitions(self):
        return [
            # ----- ИНСТРУМЕНТЫ РИСОВАНИЯ И РЕДАКТИРОВАНИЯ -----
            {
                'type': 'function',
                'function': {
                    'name': 'draw_line',
                    'description': 'Draw a line in AutoCAD',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'start': {'type': 'array', 'items': {'type': 'number'}, 'description': '[x, y, z]'},
                            'end': {'type': 'array', 'items': {'type': 'number'}, 'description': '[x, y, z]'},
                        },
                        'required': ['start', 'end'],
                    },
                },
            },
            {
                'type': 'function',
                'function': {
                    'name': 'draw_circle',
                    'description': 'Draw a circle in AutoCAD',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'center': {'type': 'array', 'items': {'type': 'number'}, 'description': '[x, y, z]'},
                            'radius': {'type': 'number'},
                        },
                        'required': ['center', 'radius'],
                    },
                },
            },
            {
                'type': 'function',
                'function': {
                    'name': 'draw_point',
                    'description': 'Draw a point in AutoCAD',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'point': {'type': 'array', 'items': {'type': 'number'}, 'description': '[x, y, z]'},
                        },
                        'required': ['point'],
                    },
                },
            },
            {
                'type': 'function',
                'function': {
                    'name': 'draw_arc',
                    'description': 'Draw an arc in AutoCAD',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'center': {'type': 'array', 'items': {'type': 'number'}, 'description': '[x, y, z]'},
                            'radius': {'type': 'number'},
                            'start_angle': {'type': 'number', 'description': 'Start angle in radians'},
                            'end_angle': {'type': 'number', 'description': 'End angle in radians'},
                        },
                        'required': ['center', 'radius', 'start_angle', 'end_angle'],
                    },
                },
            },
            {
                'type': 'function',
                'function': {
                    'name': 'draw_spline',
                    'description': 'Draw a spline line in AutoCAD with optional start/end tangent angles.',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'points': {
                                'type': 'array',
                                'items': {'type': 'array', 'items': {'type': 'number'}},
                                'description': 'List of points [[x,y,z], [x,y,z], ...]'
                            },
                            'start_angle': {
                                'type': 'number',
                                'description': 'Start tangent angle in degrees. Default is 15.',
                                'default': 15.0
                            },
                            'end_angle': {
                                'type': 'number',
                                'description': 'End tangent angle in degrees. Default is 15.',
                                'default': 15.0
                            },
                        },
                        'required': ['points'],
                    },
                },
            },
            {
                'type': 'function',
                'function': {
                    'name': 'trim_entities',
                    'description': 'Invoke the TRIM command in AutoCAD to clean up lines.',
                    'parameters': {
                        'type': 'object',
                        'properties': {},
                    },
                },
            },
            # ----- ИНСТРУМЕНТЫ УПРАВЛЕНИЯ СЛОЯМИ -----
            {
                'type': 'function',
                'function': {
                    'name': 'list_layers',
                    'description': 'Get information about all layers in the drawing, including name, color, and status (on/off, frozen, locked).',
                    'parameters': {
                        'type': 'object',
                        'properties': {},
                    },
                },
            },
            {
                'type': 'function',
                'function': {
                    'name': 'set_layer_status',
                    'description': 'Enable or disable a specific layer by name.',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'layer_name': {'type': 'string', 'description': 'The name of the layer to modify'},
                            'is_on': {'type': 'boolean', 'description': 'True to turn ON, False to turn OFF'},
                        },
                        'required': ['layer_name', 'is_on'],
                    },
                },
            },
            {
                'type': 'function',
                'function': {
                    'name': 'create_layer',
                    'description': 'Create a new layer with a specific name and optional color.',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'layer_name': {'type': 'string', 'description': 'The name of the new layer'},
                            'color': {
                                'type': 'integer',
                                'description': 'AutoCAD Color Index (ACI). 1=Red, 2=Yellow, 3=Green, 4=Cyan, 5=Blue, 6=Magenta, 7=White/Black.',
                                'default': 7
                            },
                        },
                        'required': ['layer_name'],
                    },
                },
            },
            {
                'type': 'function',
                'function': {
                    'name': 'rename_layer',
                    'description': 'Rename an existing AutoCAD layer.',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'old_name': {'type': 'string', 'description': 'The current name of the layer'},
                            'new_name': {'type': 'string', 'description': 'The new name for the layer'},
                        },
                        'required': ['old_name', 'new_name'],
                    },
                },
            },
            {
                'type': 'function',
                'function': {
                    'name': 'change_layer_color',
                    'description': 'Change the color of an existing AutoCAD layer.',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'layer_name': {'type': 'string', 'description': 'The name of the layer'},
                            'color': {
                                'type': 'integer',
                                'description': 'AutoCAD Color Index (ACI). 1=Red, 2=Yellow, 3=Green, 4=Cyan, 5=Blue, 6=Magenta, 7=White/Black.'
                            },
                        },
                        'required': ['layer_name', 'color'],
                    },
                },
            },
            # ----- СПЕЦИАЛЬНЫЕ ИНСТРУМЕНТЫ -----
            {
                'type': 'function',
                'function': {
                    'name': 'draw_radials',
                    'description': 'Draw a circle and a series of radial lines clockwise starting from the top.',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'center': {'type': 'array', 'items': {'type': 'number'}, 'description': '[x, y, z]'},
                            'radius': {'type': 'number'},
                            'angle_increment': {'type': 'number',
                                                'description': 'Angle in degrees between each radial line'},
                        },
                        'required': ['center', 'radius', 'angle_increment'],
                    },
                },
            },
            {
                'type': 'function',
                'function': {
                    'name': 'draw_cloud_radials',
                    'description': 'Draw a series of radial lines with different lengths clockwise starting from the top.',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'center': {'type': 'array', 'items': {'type': 'number'}, 'description': '[x, y, z]'},
                            'radii': {'type': 'array', 'items': {'type': 'number'},
                                      'description': 'List of lengths for each radial line'},
                            'angle_increment': {
                                'type': 'number',
                                'description': 'Angle in degrees between each radial line',
                                'default': 20.0
                            },
                        },
                        'required': ['center', 'radii'],
                    },
                },
            },
            # ----- ИНСТРУМЕНТ ЗАПРОСА КЭША (С АГРЕГАЦИЕЙ) -----
            {
                "type": "function",
                "function": {
                    "name": "get_drawing_info",
                    "description": "Получить информацию из ПОЛНОГО кэша чертежа AutoCAD (без подключения к CAD). Позволяет получить сводку, список объектов, блоков, текста, размеров, слоёв, системных переменных, выполнять фильтрацию, а также вычислять статистику (сумма, среднее, минимум, максимум) по числовым полям.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query_type": {
                                "type": "string",
                                "enum": [
                                    "summary",
                                    "entities",
                                    "blocks",
                                    "texts",
                                    "dimensions",
                                    "layers",
                                    "linetypes",
                                    "text_styles",
                                    "dim_styles",
                                    "block_definitions",
                                    "system_vars",
                                    "by_handle",
                                    "filtered",
                                    "aggregate"
                                ],
                                "description": "Тип запроса: summary (сводка), entities (все объекты), blocks (вхождения блоков), texts (текст), dimensions (размеры), layers (слои), linetypes (типы линий), text_styles (текстовые стили), dim_styles (размерные стили), block_definitions (определения блоков), system_vars (системные переменные), by_handle (поиск по handle), filtered (фильтрация объектов), aggregate (статистика по числовому полю)."
                            },
                            "entity_type": {
                                "type": "string",
                                "description": "Фильтр по ObjectName (например 'AcDbLine', 'AcDbCircle', 'AcDbBlockReference'). Используется с query_type='entities', 'filtered' или 'aggregate'."
                            },
                            "layer": {
                                "type": "string",
                                "description": "Фильтр по имени слоя."
                            },
                            "handle": {
                                "type": "string",
                                "description": "Конкретный handle объекта. Используется с query_type='by_handle'."
                            },
                            "block_name": {
                                "type": "string",
                                "description": "Фильтр по имени блока (содержит подстроку). Используется с query_type='blocks'."
                            },
                            "property_filter": {
                                "type": "object",
                                "description": "Сложный фильтр по свойствам. Пример: {'field': 'length', 'operator': '>', 'value': 100}. Поддерживаемые операторы: '==', '>', '<', '>=', '<=', 'contains' (для строк).",
                                "properties": {
                                    "field": {"type": "string"},
                                    "operator": {
                                        "type": "string",
                                        "enum": ["==", ">", "<", ">=", "<=", "contains"]
                                    },
                                    "value": {"type": ["number", "string", "boolean"]}
                                }
                            },
                            "include_details": {
                                "type": "boolean",
                                "description": "Если True, возвращает полные свойства объектов. Если False (по умолчанию) — краткую информацию (handle, тип, слой)."
                            },
                            "aggregate": {
                                "type": "object",
                                "description": "Параметры для агрегации (использовать с query_type='aggregate'). Пример: {'field': 'length', 'function': 'avg'}. Поддерживаемые функции: 'sum', 'avg', 'min', 'max', 'count'.",
                                "properties": {
                                    "field": {"type": "string",
                                              "description": "Числовое поле для агрегации (например 'length', 'radius', 'area')."},
                                    "function": {
                                        "type": "string",
                                        "enum": ["sum", "avg", "min", "max", "count"],
                                        "description": "Агрегатная функция."
                                    }
                                },
                                "required": ["field", "function"]
                            }
                        },
                        "required": ["query_type"]
                    }
                }
            }
        ]

    @staticmethod
    def get_drawing_info(
            query_type: str = "summary",
            entity_type: str = None,
            layer: str = None,
            handle: str = None,
            block_name: str = None,
            property_filter: dict = None,
            include_details: bool = False,
            aggregate: dict = None
    ) -> str:
        """
        Получить информацию из ПОЛНОГО кэша чертежа AutoCAD (без подключения к CAD).
        """
        cache = DrawingCache.load_cache()
        if cache is None:
            return "❌ Кэш чертежа не найден. Сначала выполните команду 'full_cache'."

        # ----- СВОДКА -----
        if query_type == "summary":
            return json.dumps(cache["summary"], indent=2, ensure_ascii=False)

        # ----- СИСТЕМНЫЕ ПЕРЕМЕННЫЕ -----
        if query_type == "system_vars":
            return json.dumps(cache["system_variables"], indent=2, ensure_ascii=False)

        # ----- СЛОИ -----
        if query_type == "layers":
            data = cache["layers"]
            if include_details:
                return json.dumps(data[:100], indent=2, ensure_ascii=False, default=str)
            else:
                simplified = [
                    {"name": l["name"], "on": l["on"], "frozen": l["frozen"], "locked": l["locked"]}
                    for l in data[:100]
                ]
                return json.dumps(simplified, indent=2, ensure_ascii=False)

        # ----- ТИПЫ ЛИНИЙ -----
        if query_type == "linetypes":
            data = cache["linetypes"]
            return json.dumps(data[:100], indent=2, ensure_ascii=False, default=str)

        # ----- ТЕКСТОВЫЕ СТИЛИ -----
        if query_type == "text_styles":
            data = cache["text_styles"]
            return json.dumps(data[:100], indent=2, ensure_ascii=False, default=str)

        # ----- РАЗМЕРНЫЕ СТИЛИ -----
        if query_type == "dim_styles":
            data = cache["dim_styles"]
            return json.dumps(data[:100], indent=2, ensure_ascii=False, default=str)

        # ----- ОПРЕДЕЛЕНИЯ БЛОКОВ -----
        if query_type == "block_definitions":
            data = cache["blocks"]
            return json.dumps(data[:100], indent=2, ensure_ascii=False, default=str)

        # ----- ВХОЖДЕНИЯ БЛОКОВ -----
        if query_type == "blocks":
            data = cache["block_references"]
            if block_name:
                data = [b for b in data if block_name.lower() in b["name"].lower()]
            if layer:
                data = [b for b in data if b["layer"] == layer]
            if include_details:
                return json.dumps(data[:50], indent=2, ensure_ascii=False, default=str)
            else:
                simplified = []
                for b in data[:100]:
                    simp = {"handle": b["handle"], "name": b["name"], "layer": b["layer"]}
                    if b.get("attributes"):
                        simp["attributes"] = [{"tag": a["tag"], "text": a["text"][:30]} for a in b["attributes"][:3]]
                    simplified.append(simp)
                return json.dumps(simplified, indent=2, ensure_ascii=False)

        # ----- ТЕКСТЫ -----
        if query_type == "texts":
            data = cache["texts"]
            if layer:
                data = [t for t in data if t["layer"] == layer]
            if property_filter and property_filter.get("field") == "text" and property_filter.get(
                    "operator") == "contains":
                val = property_filter["value"].lower()
                data = [t for t in data if val in t["text"].lower()]
            if not include_details:
                simplified = [
                    {"handle": t["handle"], "text": t["text"][:50], "layer": t["layer"]}
                    for t in data[:100]
                ]
                return json.dumps(simplified, indent=2, ensure_ascii=False)
            else:
                return json.dumps(data[:50], indent=2, ensure_ascii=False, default=str)

        # ----- РАЗМЕРЫ -----
        if query_type == "dimensions":
            data = cache["dimensions"]
            if layer:
                data = [d for d in data if d["layer"] == layer]
            if not include_details:
                simplified = [
                    {"handle": d["handle"], "measurement": d["measurement"], "layer": d["layer"]}
                    for d in data[:100]
                ]
                return json.dumps(simplified, indent=2, ensure_ascii=False)
            else:
                return json.dumps(data[:50], indent=2, ensure_ascii=False, default=str)

        # ----- ОБЪЕКТЫ (ENTITY) -----
        if query_type in ["entities", "filtered"]:
            data = cache["entities"]
            if entity_type:
                data = [e for e in data if e["object_name"] == entity_type]
            if layer:
                data = [e for e in data if e["layer"] == layer]
            if property_filter:
                field = property_filter.get("field")
                op = property_filter.get("operator", "==")
                val = property_filter.get("value")
                if field and val is not None:
                    if op == "==":
                        data = [e for e in data if e.get(field) == val]
                    elif op == ">":
                        data = [e for e in data if e.get(field) is not None and e[field] > val]
                    elif op == "<":
                        data = [e for e in data if e.get(field) is not None and e[field] < val]
                    elif op == ">=":
                        data = [e for e in data if e.get(field) is not None and e[field] >= val]
                    elif op == "<=":
                        data = [e for e in data if e.get(field) is not None and e[field] <= val]
                    elif op == "contains" and isinstance(val, str):
                        data = [e for e in data if e.get(field) and val.lower() in str(e[field]).lower()]
            if not include_details:
                simplified = [
                    {"handle": e["handle"], "type": e["object_name"], "layer": e["layer"]}
                    for e in data[:100]
                ]
                return json.dumps(simplified, indent=2, ensure_ascii=False)
            else:
                return json.dumps(data[:50], indent=2, ensure_ascii=False, default=str)

        # ----- АГРЕГАЦИЯ (СТАТИСТИКА) -----
        if query_type == "aggregate":
            if not aggregate or "field" not in aggregate or "function" not in aggregate:
                return "❌ Для query_type='aggregate' необходимо указать aggregate.field и aggregate.function."

            # Получаем данные так же, как для entities
            data = cache["entities"]
            if entity_type:
                data = [e for e in data if e["object_name"] == entity_type]
            if layer:
                data = [e for e in data if e["layer"] == layer]
            if property_filter:
                # (повторяем логику фильтрации)
                field = property_filter.get("field")
                op = property_filter.get("operator", "==")
                val = property_filter.get("value")
                if field and val is not None:
                    if op == "==":
                        data = [e for e in data if e.get(field) == val]
                    elif op == ">":
                        data = [e for e in data if e.get(field) is not None and e[field] > val]
                    elif op == "<":
                        data = [e for e in data if e.get(field) is not None and e[field] < val]
                    elif op == ">=":
                        data = [e for e in data if e.get(field) is not None and e[field] >= val]
                    elif op == "<=":
                        data = [e for e in data if e.get(field) is not None and e[field] <= val]
                    elif op == "contains" and isinstance(val, str):
                        data = [e for e in data if e.get(field) and val.lower() in str(e[field]).lower()]

            # Извлекаем значения поля
            values = []
            for e in data:
                val = e.get(aggregate["field"])
                if isinstance(val, (int, float)):
                    values.append(val)

            if not values:
                return f"❌ Нет числовых значений для поля '{aggregate['field']}' после фильтрации."

            func = aggregate["function"]
            if func == "sum":
                result = sum(values)
            elif func == "avg":
                result = sum(values) / len(values)
            elif func == "min":
                result = min(values)
            elif func == "max":
                result = max(values)
            elif func == "count":
                result = len(values)
            else:
                return f"❌ Неизвестная функция агрегации: {func}"

            return json.dumps({
                "field": aggregate["field"],
                "function": func,
                "result": result,
                "count": len(values)
            }, indent=2, ensure_ascii=False)

        # ----- ПОИСК ПО HANDLE -----
        if query_type == "by_handle" and handle:
            for category in ["entities", "block_references", "texts", "dimensions"]:
                for item in cache.get(category, []):
                    if item["handle"] == handle:
                        return json.dumps(item, indent=2, ensure_ascii=False, default=str)
            return f"❌ Объект с handle {handle} не найден."

        return "❌ Неверный query_type или параметры."

    def process_prompt(self, prompt):
        """Отправляет запрос в LLM и возвращает tool_calls и текстовый ответ."""
        messages = [
            {
                'role': 'system',
                'content': (
                    'You are an expert AutoCAD assistant. Use the provided tools to fulfill the user request.\n'
                    'IMPORTANT INSTRUCTIONS:\n'
                    '1. For queries about the drawing content (objects, blocks, layers, etc.), ALWAYS use the "get_drawing_info" tool.\n'
                    '2. If the user asks for **analytical/statistical** information (average, sum, minimum, maximum, total count, etc.), '
                    'you MUST use query_type="aggregate" with the appropriate field and function. Do NOT just list objects.\n'
                    '   Example: "average length of lines" → aggregate={"field": "length", "function": "avg"}, entity_type="AcDbLine".\n'
                    '   Example: "total area of circles" → aggregate={"field": "area", "function": "sum"}, entity_type="AcDbCircle".\n'
                    '3. If the user asks to list/find objects, use query_type="entities" or "filtered" with appropriate filters.\n'
                    '4. If the user asks in Russian, answer in Russian; if in English, answer in English.\n'
                    '5. Do not guess or make up data – rely on the cache.'
                )
            },
            {'role': 'user', 'content': prompt}
        ]

        response = self.client.chat(
            model=self.model,
            messages=messages,
            tools=self.get_tool_definitions(),
        )

        message = response.get('message', {})
        content = message.get('content', '')
        tool_calls = message.get('tool_calls', [])

        # Fallback для старых моделей
        if not tool_calls and content:
            stripped = content.strip()
            if stripped.startswith('{') and stripped.endswith('}'):
                try:
                    data = json.loads(stripped)
                    if 'name' in data and 'arguments' in data:
                        tool_calls = [{'function': data}]
                        content = ""
                except:
                    pass
            elif stripped.startswith('[') and stripped.endswith(']'):
                try:
                    data = json.loads(stripped)
                    if isinstance(data, list) and len(data) > 0:
                        calls = []
                        for item in data:
                            if isinstance(item, dict) and 'name' in item and 'arguments' in item:
                                calls.append({'function': item})
                        if calls:
                            tool_calls = calls
                            content = ""
                except:
                    pass

        return tool_calls, content


if __name__ == "__main__":
    manager = LLMManager()
    calls, content = manager.process_prompt("Сколько линий в чертеже?")
    print("Tool calls:", json.dumps(calls, indent=2))
    print("Content:", content)