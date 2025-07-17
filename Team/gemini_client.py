import os
import google.generativeai as genai
from dotenv import load_dotenv

def configure_api():
    """Loads API key from .env and configures the Gemini API."""
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in .env file.")
    genai.configure(api_key=api_key)

def invoke_persona(prompt: str) -> str:
    """
    Sends a prompt to the Gemini Pro model and returns the text response.
    
    Args:
        prompt: The complete prompt for the persona.
        
    Returns:
        The generated text from the model.
    """
    try:
        model = genai.GenerativeModel('models/gemini-1.5-pro-latest')
        response = model.generate_content(prompt)
        # A simple way to clean up the response, removing markdown backticks for code blocks
        cleaned_text = response.text.replace("```python", "").replace("```", "").strip()
        return cleaned_text
    except Exception as e:
        print(f"An error occurred while calling the Gemini API: {e}")
        return "" # Return empty string on failure 