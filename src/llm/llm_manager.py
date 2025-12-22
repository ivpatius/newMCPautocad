import json
import ollama

class LLMManager:
    def __init__(self, model="llama3"):
        self.model = model

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
        response = ollama.chat(
            model=self.model,
            messages=[{'role': 'user', 'content': prompt}],
            tools=self.get_tool_definitions(),
        )
        return response['message'].get('tool_calls', [])

if __name__ == "__main__":
    manager = LLMManager()
    calls = manager.process_prompt("Draw a line from 0,0 to 10,10 and a circle at 5,5 with radius 2")
    print(json.dumps(calls, indent=2))
