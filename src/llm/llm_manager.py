import json
import os
import ollama
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LLMManager:
    def __init__(self):
        self.model = os.getenv("OLLAMA_MODEL", "llama3")
        self.api_url = os.getenv("LLM_API_URL")
        
        if self.api_url:
            self.client = ollama.Client(host=self.api_url)
        else:
            self.client = ollama

    def get_tool_definitions(self):
        return [
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
            }
        ]

    def process_prompt(self, prompt):
        """Send prompt to LLM and get tool calls."""
        response = self.client.chat(
            model=self.model,
            messages=[{'role': 'user', 'content': prompt}],
            tools=self.get_tool_definitions(),
        )
        return response['message'].get('tool_calls', [])

if __name__ == "__main__":
    manager = LLMManager()
    calls = manager.process_prompt("Draw a line from 0,0 to 10,10 and a circle at 5,5 with radius 2")
    print(json.dumps(calls, indent=2))
