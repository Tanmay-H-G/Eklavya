import ollama
import os

# Default model: llama3.2:1b (Fastest and light)
OLLAMA_MODEL = os.environ.get('OllamaModel', 'llama3.2:1b')

def OllamaChat(query, history):
    """
    Generate a response using the local Ollama instance.
    history: list of dicts with 'role' and 'content'
    """
    try:
        # Prepend system prompt for consistency with Gemini
        system_prompt = {
            'role': 'system',
            'content': "You are Eklavya, an advanced AI assistant. Keep responses concise and natural for TTS. No markdown."
        }
        
        input_history = [system_prompt] + history
        input_history.append({'role': 'user', 'content': query})
        
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=input_history,
            options={
                'temperature': 0.7,
                'num_predict': 512,
            }
        )
        
        return response['message']['content'].strip()
    except Exception as e:
        print(f"[Ollama] Error: {e}")
        return "I'm having trouble connecting to my local offline brain. Please ensure Ollama is running."
