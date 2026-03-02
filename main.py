#!/usr/bin/env python3
"""
Main entry point for AutoCAD AI Assistant.
Режим работы: полный кэш чертежа создаётся при старте или по команде,
далее все запросы обрабатываются ТОЛЬКО по данным кэша, без AutoCAD.
"""
import sys
import os
import json
import shutil

# ИМПОРТЫ
from src.cad.autocad_client import AutoCADClient
from src.cad.drawing_cache import DrawingCache
from src.llm.llm_manager import LLMManager

def ensure_com_initialized():
    """Гарантирует, что COM инициализирован в текущем потоке."""
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except:
        pass  # уже инициализирован или нет библиотеки

def main():
    # Ensure .env exists
    if not os.path.exists(".env") and os.path.exists(".env.example"):
        print("[*] .env file not found. Creating from .env.example...")
        shutil.copy(".env.example", ".env")

    # Пытаемся импортировать win32com
    try:
        import win32com.client
        import pythoncom
    except ImportError as e:
        print(f"[!] Warning: {e}")
        print("    AutoCAD COM libraries not available. Cache mode only.")

    print("--- AutoCAD AI Assistant (Cache Mode) ---")

    # Подключение к AutoCAD
    try:
        cad = AutoCADClient()
        if not cad.connect():
            print("⚠️  Не удалось подключиться к AutoCAD.")
            print("   Работа возможна только если есть существующий кэш.")
            cad = None
        else:
            print("✅ Подключение к AutoCAD установлено.")
            ensure_com_initialized()  # инициализируем COM для главного потока
    except Exception as e:
        print(f"⚠️  Ошибка подключения к AutoCAD: {e}")
        cad = None

    # Инициализация кэша и LLM
    drawing_cache = DrawingCache(cad) if cad else None
    llm = LLMManager()

    # --- Загрузка кэша и проверка актуальности ---
    cache = DrawingCache.load_cache()
    if cache is None:
        print("🆕 Кэш чертежа не найден или устарел.")
        if cad and drawing_cache:
            print("Создаём полный кэш чертежа...")
            ensure_com_initialized()  # на всякий случай
            drawing_cache.full_cache_update()
            cache = DrawingCache.load_cache()  # перезагружаем свежий кэш
        else:
            print("❌ Нет подключения к AutoCAD и нет актуального кэша. Выход.")
            return
    else:
        print(f"📁 Кэш загружен: {cache['metadata']['drawing_name']}, "
              f"обновлён {cache['metadata']['last_update']}")

    print("\n[*] Configuration Loaded:")
    print(f"    - Model: {llm.model}")
    print(f"    - API URL: {llm.api_url or 'Ollama Default (localhost:11434)'}")
    print("    - Режим: ответы на основе кэша (AutoCAD не требуется)")
    print("\nКоманды: 'full_cache' - полное обновление кэша, 'exit' - выход")

    while True:
        try:
            user_input = input("\n[CAD AI] > ")
            if user_input.lower() in ['exit', 'quit']:
                break

            # ----- ПОЛНОЕ ОБНОВЛЕНИЕ КЭША -----
            if user_input.lower() in ['full_cache', 'обнови всё', 'update cache']:
                if cad and drawing_cache:
                    print("🔄 Запуск полного обновления кэша...")
                    ensure_com_initialized()
                    drawing_cache.full_cache_update()
                    cache = DrawingCache.load_cache()
                else:
                    print("❌ Нет подключения к AutoCAD для обновления кэша.")
                continue

            # ----- ОБЫЧНЫЙ ЗАПРОС К LLM -----
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
                func_name = call['function']['name']
                args = call['function']['arguments']
                print(f"[Шаг {i}] Выполняется: {func_name}")

                try:
                    # --- ИНСТРУМЕНТ ЗАПРОСА КЭША ---
                    if func_name == 'get_drawing_info':
                        result = LLMManager.get_drawing_info(**args)
                        print("\n📊 Результат запроса к кэшу:")
                        print(result)
                        # Краткий ответ от LLM
                        if len(result) < 2000:
                            summary_prompt = f"Пользователь спросил: '{user_input}'. Вот данные из чертежа: {result}. Ответь пользователю понятным языком."
                            summary_response = llm.client.chat(
                                model=llm.model,
                                messages=[{'role': 'user', 'content': summary_prompt}]
                            )
                            print(f"\n💬 Ответ AI: {summary_response['message']['content']}")

                    # --- Команды рисования (требуют CAD) ---
                    elif func_name in ['draw_line', 'draw_circle', 'draw_point', 'draw_arc',
                                       'draw_spline', 'trim_entities', 'list_layers',
                                       'set_layer_status', 'create_layer', 'rename_layer',
                                       'change_layer_color', 'draw_radials', 'draw_cloud_radials']:
                        if cad:
                            # Здесь должны быть вызовы методов AutoCADClient
                            # Пример для draw_line:
                            if func_name == 'draw_line':
                                cad.add_line(tuple(args['start']), tuple(args['end']))
                                print(f"   Линия нарисована: {args['start']} -> {args['end']}")
                            elif func_name == 'draw_circle':
                                cad.add_circle(tuple(args['center']), args['radius'])
                                print(f"   Окружность нарисована: центр {args['center']}, радиус {args['radius']}")
                            # ... добавьте остальные команды по аналогии ...
                            else:
                                print(f"   ⚠️  Инструмент {func_name} требует реализации в AutoCADClient")
                        else:
                            print("⚠️  Для выполнения этой команды нужно подключение к AutoCAD.")

                    else:
                        print(f"⚠️  Неизвестный инструмент: {func_name}")

                except Exception as e:
                    print(f"❌ Ошибка при выполнении шага {i}: {e}")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Ошибка: {e}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print("\n" + "="*50)
        print("CRITICAL ERROR DURING EXECUTION:")
        traceback.print_exc()
        print("="*50)
        input("\nPress Enter to exit...")