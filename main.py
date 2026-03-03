#!/usr/bin/env python3
"""
Main entry point for AutoCAD AI Assistant.
✅ Полный кэш чертежа с быстрым доступом по handle
✅ Обработка ошибок и логирование
✅ Работа в режиме кэша без AutoCAD
"""
import sys
import os
import json
import shutil
import logging
from typing import Optional

# Импорт модулей
from src.cad.autocad_client import AutoCADClient
from src.cad.drawing_cache import DrawingCache
from src.llm.llm_manager import LLMManager
from src.cad.dataclasses import EntityCache, BoundingBox

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cad_ai_assistant.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def ensure_com_initialized():
    """Гарантирует инициализацию COM в текущем потоке."""
    try:
        import pythoncom
        pythoncom.CoInitialize()
        logger.debug("COM initialized")
    except Exception as e:
        logger.debug(f"COM already initialized or not available: {e}")


def main():
    """Основная функция запуска ассистента."""
    logger.info("=" * 50)
    logger.info("AutoCAD AI Assistant Starting...")
    logger.info("=" * 50)

    # Создание .env если нет
    if not os.path.exists(".env") and os.path.exists(".env.example"):
        logger.info("Creating .env from .env.example...")
        shutil.copy(".env.example", ".env")

    # Проверка COM библиотек
    cad: Optional[AutoCADClient] = None
    drawing_cache: Optional[DrawingCache] = None

    try:
        import win32com.client
        import pythoncom
        logger.info("AutoCAD COM libraries available")
    except ImportError as e:
        logger.warning(f"AutoCAD COM libraries not available: {e}")
        logger.info("Running in cache-only mode")

    # Подключение к AutoCAD
    try:
        cad = AutoCADClient()
        if cad.connect():
            logger.info("✅ Connected to AutoCAD")
            ensure_com_initialized()
        else:
            logger.warning("⚠️ Could not connect to AutoCAD")
            cad = None
    except Exception as e:
        logger.error(f"AutoCAD connection error: {e}", exc_info=True)
        cad = None

    # Инициализация кэша и LLM
    if cad:
        drawing_cache = DrawingCache(cad)

    llm = LLMManager()

    # Загрузка кэша
    cache_data = DrawingCache.load_cache()

    if cache_data is None:
        logger.info("🆕 Cache not found or outdated")
        if cad and drawing_cache:
            logger.info("Creating full drawing cache...")
            ensure_com_initialized()
            drawing_cache.full_cache_update()
            cache_data = DrawingCache.load_cache()
        else:
            logger.error("❌ No AutoCAD connection and no cache. Exiting.")
            return
    else:
        meta = cache_data.get('metadata', {})
        logger.info(
            f"📁 Cache loaded: {meta.get('drawing_name', 'Unknown')}, "
            f"updated {meta.get('last_updated', 'Unknown')}"
        )

    # Информация о конфигурации
    logger.info("\n" + "=" * 50)
    logger.info("Configuration:")
    logger.info(f"  Model: {llm.model}")
    logger.info(f"  API URL: {llm.api_url or 'Ollama Default'}")
    logger.info("  Mode: Cache-based (AutoCAD not required for queries)")
    logger.info("=" * 50)
    logger.info("Commands: 'full_cache' - update cache, 'exit' - quit")
    logger.info("=" * 50)

    # Главный цикл
    while True:
        try:
            user_input = input("\n[CAD AI] > ").strip()

            if user_input.lower() in ['exit', 'quit', 'выход']:
                logger.info("User requested exit")
                break

            # Обновление кэша
            if user_input.lower() in ['full_cache', 'обнови всё', 'update cache']:
                if cad and drawing_cache:
                    logger.info("🔄 Starting full cache update...")
                    ensure_com_initialized()
                    drawing_cache.full_cache_update()
                    cache_data = DrawingCache.load_cache()
                    logger.info("✅ Cache updated successfully")
                else:
                    logger.warning("❌ No AutoCAD connection for cache update")
                continue

            # Обработка запроса
            if not user_input:
                continue

            logger.info(f"Processing query: {user_input[:100]}...")
            print("Обработка запроса (по данным кэша)...")

            tool_calls, ai_content = llm.process_prompt(user_input)

            if not tool_calls:
                if ai_content:
                    print(f"\n🤖 AI: {ai_content}")
                else:
                    print("LLM не определил команды.")
                continue

            # Выполнение инструментов
            for i, call in enumerate(tool_calls, 1):
                func_name = call.get('function', {}).get('name', '')
                args = call.get('function', {}).get('arguments', {})

                logger.info(f"[Step {i}] Executing: {func_name}")
                print(f"[Шаг {i}] Выполняется: {func_name}")

                try:
                    # ===== ЗАПРОСЫ К КЭШУ =====
                    if func_name == 'get_drawing_info':
                        result = LLMManager.get_drawing_info(**args)
                        print("\n📊 Результат запроса к кэшу:")
                        # Красивый вывод JSON
                        try:
                            parsed = json.loads(result)
                            if "entities" in parsed and isinstance(parsed["entities"], list):
                                print(f"Найдено объектов: {parsed.get('count', 0)}")
                                print(f"Показано: {parsed.get('showing', 0)}")
                                if "filters_applied" in parsed:
                                    print(f"Фильтры: {parsed['filters_applied']}")
                                # Показываем первые 10 объектов кратко
                                for e in parsed["entities"][:10]:
                                    handle = e.get("handle", "N/A")
                                    etype = e.get("type", e.get("object_name", "N/A"))
                                    layer = e.get("layer", "N/A")
                                    center = e.get("center") or (
                                        e.get("bounding_box", {}).get("center") if isinstance(e.get("bounding_box"),
                                                                                              dict) else None)
                                    print(f"  • {handle} | {etype} | {layer}" + (f" @ {center}" if center else ""))
                                if parsed.get("count", 0) > 10:
                                    print(f"  ... и ещё {parsed['count'] - 10}")
                            else:
                                print(json.dumps(parsed, indent=2, ensure_ascii=False)[:1000])
                        except json.JSONDecodeError:
                            print(result[:1000])

                    # ===== РИСОВАНИЕ =====
                    elif func_name in ['draw_line', 'draw_circle', 'draw_point', 'draw_arc', 'draw_spline']:
                        if cad:
                            layer = args.get('layer')
                            if layer:
                                try:
                                    cad.doc.ActiveLayer = cad.doc.Layers.Item(layer)
                                except Exception:
                                    pass

                            if func_name == 'draw_line':
                                cad.add_line(
                                    tuple(args.get('start', [0, 0, 0])),
                                    tuple(args.get('end', [0, 0, 0]))
                                )
                                print(f" ✅ Линия: {args.get('start')} → {args.get('end')}")
                            elif func_name == 'draw_circle':
                                cad.add_circle(
                                    tuple(args.get('center', [0, 0, 0])),
                                    args.get('radius', 1)
                                )
                                print(f" ✅ Круг: центр={args.get('center')}, R={args.get('radius')}")
                            elif func_name == 'draw_point':
                                cad.add_point(tuple(args.get('point', [0, 0, 0])))
                                print(f" ✅ Точка: {args.get('point')}")
                            elif func_name == 'draw_arc':
                                cad.add_arc(
                                    tuple(args.get('center', [0, 0, 0])),
                                    args.get('radius', 1),
                                    args.get('start_angle', 0),
                                    args.get('end_angle', 3.14159)
                                )
                                print(f" ✅ Дуга создана")
                            elif func_name == 'draw_spline':
                                cad.add_spline(args.get('points', []))
                                print(f" ✅ Сплайн создан")
                        else:
                            print("⚠️ Требуется подключение к AutoCAD")

                    # ===== УПРАВЛЕНИЕ СЛОЯМИ =====
                    elif func_name == 'list_layers':
                        if cad:
                            layers = cad.get_layers_info()
                            print(f"📋 Слои ({len(layers)}):")
                            for l in layers[:50]:
                                print(f"  • {l.name} (color:{l.color}, on:{l.is_on}, frozen:{l.is_frozen})")
                            if len(layers) > 50:
                                print(f"  ... и ещё {len(layers) - 50}")
                        else:
                            # Fallback: читаем из кэша
                            cache_data = DrawingCache.load_cache()
                            if cache_data:
                                layers = cache_data.get('layers', [])
                                print(f"📋 Слои из кэша ({len(layers)}):")
                                for l in layers[:50]:
                                    print(f"  • {l.get('name')} (color:{l.get('color')}, on:{l.get('on')})")
                                if len(layers) > 50:
                                    print(f"  ... и ещё {len(layers) - 50}")
                            else:
                                print("⚠️ Нет подключения к AutoCAD и кэш не найден")

                    elif func_name == 'set_layer_status':
                        if cad:
                            result = cad.set_layer_status(
                                args.get('layer_name', ''),
                                args.get('is_on', True)
                            )
                            status = "Включён" if args.get('is_on') else "Выключен"
                            print(f"✅ {status} слой: {args.get('layer_name')}")
                        else:
                            print("⚠️ Требуется подключение к AutoCAD")

                    elif func_name == 'create_layer':
                        if cad:
                            cad.create_layer(
                                args.get('layer_name', ''),
                                args.get('color', 7)
                            )
                            print(f"✅ Создан слой: {args.get('layer_name')}")
                        else:
                            print("⚠️ Требуется подключение к AutoCAD")

                    elif func_name == 'rename_layer':
                        if cad:
                            result = cad.rename_layer(
                                args.get('old_name', ''),
                                args.get('new_name', '')
                            )
                            print(f"✅ Слой переименован: {args.get('old_name')} → {args.get('new_name')}")
                        else:
                            print("⚠️ Требуется подключение к AutoCAD")

                    elif func_name == 'change_layer_color':
                        if cad:
                            result = cad.change_layer_color(
                                args.get('layer_name', ''),
                                args.get('color', 7)
                            )
                            print(f"✅ Цвет слоя '{args.get('layer_name')}' изменён на ACI {args.get('color')}")
                        else:
                            print("⚠️ Требуется подключение к AutoCAD")

                    else:
                        logger.warning(f"Unknown tool: {func_name}")
                        print(f"⚠️ Неизвестный инструмент: {func_name}")

                except Exception as e:
                    logger.error(f"Error executing {func_name}: {e}", exc_info=True)
                    print(f"❌ Ошибка: {e}")

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            print(f"Ошибка: {e}")

    logger.info("AutoCAD AI Assistant stopped")
    print("\n👋 До свидания!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"CRITICAL ERROR: {e}", exc_info=True)
        print("\n" + "=" * 50)
        print("CRITICAL ERROR DURING EXECUTION:")
        print(f"{e}")
        print("=" * 50)
        input("\nPress Enter to exit...")