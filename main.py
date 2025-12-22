import sys
import os
from src.cad.autocad_client import AutoCADClient
from src.llm.llm_manager import LLMManager

def main():
    print("--- AutoCAD AI Assistant ---")
    
    cad = AutoCADClient()
    if not cad.connect():
        print("Could not connect to AutoCAD. Please make sure it is open.")
        # sys.exit(1) # Uncomment for production

    llm = LLMManager()
    
    while True:
        try:
            user_input = input("\n[CAD AI] > ")
            if user_input.lower() in ['exit', 'quit']:
                break
                
            print("Processing request...")
            tool_calls = llm.process_prompt(user_input)
            
            if not tool_calls:
                print("LLM did not identify any CAD commands.")
                continue
                
            for call in tool_calls:
                func_name = call['function']['name']
                args = call['function']['arguments']
                
                print(f"Executing: {func_name}({args})")
                
                if func_name == 'draw_line':
                    cad.add_line(tuple(args['start']), tuple(args['end']))
                elif func_name == 'draw_circle':
                    cad.add_circle(tuple(args['center']), args['radius'])
                elif func_name == 'draw_point':
                    cad.add_point(tuple(args['point']))
                else:
                    print(f"Unsupported command: {func_name}")
                    
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
