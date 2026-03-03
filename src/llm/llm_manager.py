"""
Менеджер LLM для AutoCAD AI Assistant.
✅ Чётко определённые инструменты с JSON Schema
✅ Поддержка всех типов запросов включая filtered
✅ Комплексная обработка ошибок и логирование
✅ Авто-подсказки при пустых результатах
"""
import json
import os
import ollama
import logging
from dotenv import load_dotenv
from typing import List, Dict, Any, Tuple, Optional
from ..cad.drawing_cache import DrawingCache
from ..cad.dataclasses import EntityCache

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('llm_manager.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()


class LLMManager:
    """
    Менеджер LLM с чётко определёнными инструментами.
    ✅ JSON Schema для всех инструментов
    ✅ Комплексная обработка ошибок
    ✅ Поддержка filtered запросов + авто-подсказки
    """

    def __init__(self):
        self.model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
        self.api_url = os.getenv("LLM_API_URL", 'http://localhost:11434/')

        if self.api_url:
            self.api_url = self.api_url.strip().rstrip('/')
            for suffix in ['/api/generate', '/api/chat', '/api']:
                if self.api_url.endswith(suffix):
                    self.api_url = self.api_url[:-len(suffix)]
            self.client = ollama.Client(host=self.api_url)
        else:
            self.client = ollama

        logger.info(f"LLM Manager initialized with model: {self.model}")
        logger.info(f"API URL: {self.api_url or 'Ollama Default'}")

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Получение определений всех инструментов с JSON Schema."""
        return [
            # ===== РИСОВАНИЕ =====
            {
                'type': 'function',
                'function': {
                    'name': 'draw_line',
                    'description': 'Нарисовать линию в AutoCAD между двумя 3D точками',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'start': {'type': 'array', 'items': {'type': 'number'}, 'minItems': 3, 'maxItems': 3, 'description': 'Начальная точка [x, y, z]'},
                            'end': {'type': 'array', 'items': {'type': 'number'}, 'minItems': 3, 'maxItems': 3, 'description': 'Конечная точка [x, y, z]'},
                            'layer': {'type': 'string', 'description': 'Слой для размещения объекта'}
                        },
                        'required': ['start', 'end'],
                        'additionalProperties': False
                    },
                },
            },
            {
                'type': 'function',
                'function': {
                    'name': 'draw_circle',
                    'description': 'Нарисовать круг в AutoCAD с центром и радиусом',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'center': {'type': 'array', 'items': {'type': 'number'}, 'minItems': 3, 'maxItems': 3, 'description': 'Центр круга [x, y, z]'},
                            'radius': {'type': 'number', 'minimum': 0, 'description': 'Радиус круга'},
                            'layer': {'type': 'string', 'description': 'Слой для размещения объекта'}
                        },
                        'required': ['center', 'radius'],
                        'additionalProperties': False
                    },
                },
            },
            {
                'type': 'function',
                'function': {
                    'name': 'draw_point',
                    'description': 'Поставить точку в AutoCAD в указанных 3D координатах',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'point': {'type': 'array', 'items': {'type': 'number'}, 'minItems': 3, 'maxItems': 3, 'description': 'Координаты точки [x, y, z]'},
                            'layer': {'type': 'string', 'description': 'Слой для размещения объекта'}
                        },
                        'required': ['point'],
                        'additionalProperties': False
                    },
                },
            },
            {
                'type': 'function',
                'function': {
                    'name': 'draw_arc',
                    'description': 'Нарисовать дугу в AutoCAD с центром, радиусом и углами',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'center': {'type': 'array', 'items': {'type': 'number'}, 'minItems': 3, 'maxItems': 3},
                            'radius': {'type': 'number', 'minimum': 0},
                            'start_angle': {'type': 'number', 'description': 'Начальный угол в радианах'},
                            'end_angle': {'type': 'number', 'description': 'Конечный угол в радианах'},
                            'layer': {'type': 'string'}
                        },
                        'required': ['center', 'radius', 'start_angle', 'end_angle'],
                        'additionalProperties': False
                    },
                },
            },
            {
                'type': 'function',
                'function': {
                    'name': 'draw_spline',
                    'description': 'Нарисовать сплайн через несколько контрольных точек',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'points': {
                                'type': 'array',
                                'items': {'type': 'array', 'items': {'type': 'number'}, 'minItems': 3, 'maxItems': 3},
                                'minItems': 2,
                                'description': 'Список контрольных точек [[x,y,z], ...]'
                            },
                            'layer': {'type': 'string'}
                        },
                        'required': ['points'],
                        'additionalProperties': False
                    },
                },
            },

            # ===== СЛОИ =====
            {
                'type': 'function',
                'function': {
                    'name': 'list_layers',
                    'description': 'Получить информацию обо всех слоях в чертеже',
                    'parameters': {'type': 'object', 'properties': {}, 'additionalProperties': False},
                },
            },
            {
                'type': 'function',
                'function': {
                    'name': 'set_layer_status',
                    'description': 'Включить или выключить указанный слой',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'layer_name': {'type': 'string', 'description': 'Имя слоя'},
                            'is_on': {'type': 'boolean', 'description': 'True для включения, False для выключения'}
                        },
                        'required': ['layer_name', 'is_on'],
                        'additionalProperties': False
                    },
                },
            },
            {
                'type': 'function',
                'function': {
                    'name': 'create_layer',
                    'description': 'Создать новый слой с именем и опциональным цветом',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'layer_name': {'type': 'string', 'description': 'Имя нового слоя'},
                            'color': {'type': 'integer', 'minimum': 1, 'maximum': 255, 'default': 7}
                        },
                        'required': ['layer_name'],
                        'additionalProperties': False
                    },
                },
            },
            {
                'type': 'function',
                'function': {
                    'name': 'rename_layer',
                    'description': 'Переименовать существующий слой',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'old_name': {'type': 'string'},
                            'new_name': {'type': 'string'}
                        },
                        'required': ['old_name', 'new_name'],
                        'additionalProperties': False
                    },
                },
            },
            {
                'type': 'function',
                'function': {
                    'name': 'change_layer_color',
                    'description': 'Изменить цвет существующего слоя',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'layer_name': {'type': 'string'},
                            'color': {'type': 'integer', 'minimum': 1, 'maximum': 255}
                        },
                        'required': ['layer_name', 'color'],
                        'additionalProperties': False
                    },
                },
            },

            # ===== ЗАПРОС К КЭШУ =====
            {
                'type': 'function',
                'function': {
                    'name': 'get_drawing_info',
                    'description': '''
                    Получить информацию из ПОЛНОГО кэша чертежа AutoCAD.
                    
                    ПРАВИЛА:
                    - Отвечай на естественном языке, НЕ возвращай сырой JSON
                    - Группируй результаты, показывай первые 10 + общее количество
                    - Для поиска по слою/типу используй query_type="filtered"
                    
                    query_type значения:
                    - summary: Общая статистика
                    - entities/blocks/texts/dimensions: Списки объектов
                    - layers: Информация о слоях
                    - filtered: Фильтрованные объекты (layer/entity_type/property_filter)
                    - aggregate: Статистика (sum/avg/min/max/count)
                    - by_handle: Поиск по handle
                    
                    Пример filtered:
                    - query_type="filtered", layer="ОБЩ_Д_разметка"
                    - query_type="filtered", entity_type="AcDbBlockReference", property_filter={"field":"area","operator":">","value":100}
                    ''',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'query_type': {
                                'type': 'string',
                                'enum': ["summary", "entities", "blocks", "texts", "dimensions", "layers", "filtered", "aggregate", "by_handle"],
                                'description': 'Тип запроса'
                            },
                            'entity_type': {'type': 'string', 'description': 'Фильтр по ObjectName'},
                            'layer': {'type': 'string', 'description': 'Фильтр по имени слоя'},
                            'handle': {'type': 'string', 'description': 'Handle объекта'},
                            'block_name': {'type': 'string', 'description': 'Фильтр по имени блока'},
                            'property_filter': {
                                'type': 'object',
                                'properties': {
                                    'field': {'type': 'string'},
                                    'operator': {'type': 'string', 'enum': ['==', '>', '<', '>=', '<=', 'contains']},
                                    'value': {'type': ['number', 'string', 'boolean']}
                                },
                                'required': ['field', 'operator', 'value']
                            },
                            'include_details': {'type': 'boolean', 'default': False},
                            'aggregate': {
                                'type': 'object',
                                'properties': {
                                    'field': {'type': 'string'},
                                    'function': {'type': 'string', 'enum': ['sum', 'avg', 'min', 'max', 'count']}
                                },
                                'required': ['field', 'function']
                            },
                            'limit': {'type': 'integer', 'minimum': 1, 'maximum': 500, 'default': 100}
                        },
                        'required': ['query_type'],
                        'additionalProperties': False
                    }
                }
            }
        ]

    @staticmethod
    def get_drawing_info(
        query_type: str = "summary",
        entity_type: Optional[str] = None,
        layer: Optional[str] = None,
        handle: Optional[str] = None,
        block_name: Optional[str] = None,
        property_filter: Optional[dict] = None,
        include_details: bool = False,
        aggregate: Optional[dict] = None,
        limit: int = 100
    ) -> str:
        """Получить информацию из кэша чертежа с полной поддержкой filtered."""
        try:
            cache = DrawingCache.load_cache()
            if cache is None:
                return json.dumps({"error": True, "message": "Кэш не найден. Выполните 'full_cache'."}, indent=2, ensure_ascii=False)

            # ===== SUMMARY =====
            if query_type == "summary":
                entities = cache.get("entities", [])
                type_counts = {}
                layer_counts = {}
                for e in entities:
                    t = e.get("object_name", "Unknown")
                    type_counts[t] = type_counts.get(t, 0) + 1
                    l = e.get("layer", "Unknown")
                    layer_counts[l] = layer_counts.get(l, 0) + 1

                return json.dumps({
                    "total_entities": len(entities),
                    "total_blocks": len(cache.get("blocks", [])),
                    "total_texts": len(cache.get("texts", [])),
                    "total_dimensions": len(cache.get("dimensions", [])),
                    "total_layers": len(cache.get("layers", [])),
                    "by_type": type_counts,
                    "by_layer": layer_counts,
                    "metadata": cache.get("metadata", {}),
                    "last_updated": cache.get("last_updated")
                }, indent=2, ensure_ascii=False, default=str)

            # ===== LAYERS =====
            if query_type == "layers":
                data = cache.get("layers", [])
                simplified = [{"name": l.get("name"), "on": l.get("on"), "frozen": l.get("frozen"), "color": l.get("color")} for l in data[:limit]]
                return json.dumps({"count": len(data), "layers": simplified}, indent=2, ensure_ascii=False)

            # ===== ENTITIES =====
            if query_type == "entities":
                data = cache.get("entities", [])
                if entity_type:
                    data = [e for e in data if e.get("object_name") == entity_type]
                if layer:
                    data = [e for e in data if e.get("layer") == layer]

                simplified = [{"handle": e.get("handle"), "type": e.get("object_name"), "layer": e.get("layer"), "center": e.get("bounding_box", {}).get("center") if e.get("bounding_box") else None} for e in data[:limit]]
                return json.dumps({"count": len(data), "showing": len(simplified), "entities": simplified}, indent=2, ensure_ascii=False)

            # ===== FILTERED (ПОЛНАЯ РЕАЛИЗАЦИЯ) =====
            if query_type == "filtered":
                data = cache.get("entities", [])

                if entity_type:
                    data = [e for e in data if e.get("object_name") == entity_type]
                if layer:
                    data = [e for e in data if e.get("layer") == layer]
                if block_name:
                    data = [e for e in data if e.get("type_properties", {}).get("block_name") == block_name or e.get("type_properties", {}).get("effective_name") == block_name]

                if property_filter:
                    field = property_filter.get("field")
                    operator = property_filter.get("operator")
                    value = property_filter.get("value")
                    if field and operator:
                        filtered = []
                        for e in data:
                            prop_value = e.get(field) or e.get("type_properties", {}).get(field) or e.get("coordinates", {}).get(field)
                            if prop_value is None:
                                continue
                            try:
                                match = False
                                if operator == "==": match = str(prop_value) == str(value)
                                elif operator == ">": match = float(prop_value) > float(value)
                                elif operator == "<": match = float(prop_value) < float(value)
                                elif operator == ">=": match = float(prop_value) >= float(value)
                                elif operator == "<=": match = float(prop_value) <= float(value)
                                elif operator == "contains": match = str(value).lower() in str(prop_value).lower()
                                if match:
                                    filtered.append(e)
                            except (ValueError, TypeError):
                                continue
                        data = filtered

                # Авто-подсказки при 0 результатах
                if not data:
                    available_layers = list(set(e.get("layer") for e in cache.get("entities", []) if e.get("layer")))[:10]
                    available_types = list(set(e.get("object_name") for e in cache.get("entities", []) if e.get("object_name")))[:10]
                    return json.dumps({
                        "count": 0,
                        "message": "Объекты не найдены. Доступные варианты:",
                        "suggested_layers": available_layers,
                        "suggested_types": available_types,
                        "filters_applied": {"layer": layer, "entity_type": entity_type, "block_name": block_name}
                    }, indent=2, ensure_ascii=False)

                if include_details:
                    return json.dumps({"count": len(data), "showing": min(len(data), limit), "filters_applied": {"layer": layer, "entity_type": entity_type}, "entities": data[:limit]}, indent=2, ensure_ascii=False, default=str)
                else:
                    simplified = [{"handle": e.get("handle"), "type": e.get("object_name"), "layer": e.get("layer"), "center": e.get("bounding_box", {}).get("center") if e.get("bounding_box") else None} for e in data[:limit]]
                    return json.dumps({"count": len(data), "showing": len(simplified), "filters_applied": {"layer": layer, "entity_type": entity_type}, "entities": simplified}, indent=2, ensure_ascii=False)

            # ===== BLOCKS / TEXTS / DIMENSIONS =====
            if query_type == "blocks":
                data = cache.get("blocks", [])
                if layer: data = [b for b in data if b.get("layer") == layer]
                return json.dumps({"count": len(data), "showing": min(len(data), limit), "blocks": data[:limit]}, indent=2, ensure_ascii=False, default=str)

            if query_type == "texts":
                data = cache.get("texts", [])
                if layer: data = [t for t in data if t.get("layer") == layer]
                simplified = [{"handle": t.get("handle"), "text": t.get("text", "")[:50], "layer": t.get("layer")} for t in data[:limit]]
                return json.dumps({"count": len(data), "texts": simplified}, indent=2, ensure_ascii=False)

            if query_type == "dimensions":
                data = cache.get("dimensions", [])
                if layer: data = [d for d in data if d.get("layer") == layer]
                return json.dumps({"count": len(data), "dimensions": data[:limit]}, indent=2, ensure_ascii=False, default=str)

            # ===== AGGREGATE =====
            if query_type == "aggregate" and aggregate:
                data = cache.get("entities", [])
                if entity_type: data = [e for e in data if e.get("object_name") == entity_type]
                if layer: data = [e for e in data if e.get("layer") == layer]

                values = []
                for e in data:
                    val = e.get(aggregate["field"]) or e.get("type_properties", {}).get(aggregate["field"])
                    if isinstance(val, (int, float)):
                        values.append(float(val))

                if not values:
                    return json.dumps({"field": aggregate["field"], "result": None, "count": 0}, indent=2, ensure_ascii=False)

                func = aggregate["function"]
                result = {"sum": sum, "avg": lambda v: sum(v)/len(v), "min": min, "max": max, "count": len}.get(func, lambda v: None)(values)
                return json.dumps({"field": aggregate["field"], "function": func, "result": result, "count": len(values)}, indent=2, ensure_ascii=False)

            # ===== BY_HANDLE =====
            if query_type == "by_handle" and handle:
                for cat in ["entities", "blocks", "texts", "dimensions"]:
                    for item in cache.get(cat, []):
                        if item.get("handle") == handle:
                            return json.dumps({"found": True, "category": cat, "data": item}, indent=2, ensure_ascii=False, default=str)
                return json.dumps({"found": False, "handle": handle}, indent=2, ensure_ascii=False)

            # ===== DEFAULT =====
            return json.dumps({"warning": True, "message": f"Запрос '{query_type}' требует реализации", "available": ["summary", "entities", "blocks", "texts", "dimensions", "layers", "filtered", "aggregate", "by_handle"]}, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Error in get_drawing_info: {e}", exc_info=True)
            return json.dumps({"error": True, "message": f"Ошибка: {str(e)}"}, indent=2, ensure_ascii=False)

    def process_prompt(self, prompt: str) -> Tuple[List[Dict], str]:
        """Отправляет запрос в LLM и возвращает tool_calls и текст."""
        try:
            messages = [
                {'role': 'system', 'content': 'Ты — экспертный ассистент AutoCAD. ПРАВИЛА: 1) НЕ возвращай сырой JSON пользователю 2) Отвечай на естественном языке 3) Группируй результаты, показывай первые 10 + общее количество 4) Для поиска используй query_type="filtered" 5) Если данных нет — скажи об этом'},
                {'role': 'user', 'content': prompt}
            ]

            response = self.client.chat(model=self.model, messages=messages, tools=self.get_tool_definitions())
            message = response.get('message', {})
            content = message.get('content', '')
            tool_calls = message.get('tool_calls', [])

            logger.info(f"LLM response: {len(tool_calls)} tool calls")
            if not tool_calls and content:
                tool_calls = self._parse_fallback_tool_calls(content)

            return tool_calls, content
        except Exception as e:
            logger.error(f"Error processing prompt: {e}", exc_info=True)
            return [], f"❌ Ошибка: {str(e)}"

    def _parse_fallback_tool_calls(self, content: str) -> List[Dict]:
        """Fallback парсинг tool calls."""
        try:
            stripped = content.strip()
            if stripped.startswith('{') and stripped.endswith('}'):
                data = json.loads(stripped)
                if 'name' in data and 'arguments' in data:
                    return [{'function': data}]
        except Exception:
            pass
        return []