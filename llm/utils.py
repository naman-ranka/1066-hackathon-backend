import os
import base64
from django.conf import settings
import openai
from google import genai
from google.genai import types

OPENAI_MODEL = "gpt-4o-mini"
GEMINI_MODEL = "gemini-2.0-flash-exp"

def encode_image_to_base64(image_data):
    """Convert image data to base64 encoded string."""
    try:
        base64_image = base64.b64encode(image_data).decode("utf-8")
        return f"data:image/jpeg;base64,{base64_image}"
    except Exception as e:
        raise Exception(f"Error encoding image: {str(e)}")

def read_prompt_file():
    """Read and return the content of the prompt file."""
    prompt_file_path = os.path.join(settings.BASE_DIR, "prompt.txt")
    try:
        with open(prompt_file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        raise Exception(f"Failed to read prompt file: {str(e)}")

def process_receipt_with_openai(image_data):
    """Process receipt using OpenAI's vision model."""
    # Get API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise Exception("OPENAI_API_KEY is not set.")
    
    # Initialize OpenAI client and prepare data
    openai.api_key = api_key
    data_url = encode_image_to_base64(image_data)
    prompt = read_prompt_file()
    
    try:
        response = openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            max_tokens=3000,
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"OpenAI API error: {str(e)}")

def process_receipt_with_gemini(image_data):
    """Process receipt using Google's Gemini vision model."""
    # Get API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise Exception("GEMINI_API_KEY is not set.")
    
    try:
        
        # model = genai.GenerativeModel(GEMINI_MODEL)
        client = genai.Client(api_key=api_key)
        
        # Get prompt
        prompt = read_prompt_file()
        
        # Create the response
        response = client.model.generate_content(
            model=GEMINI_MODEL,
            contents=[
                prompt,
                types.Part.from_bytes(image_data, mime_type="image/jpeg")
            ]
        )
        
        return response.text
    except Exception as e:
        print(e)
        raise Exception(f"Gemini API error: {str(e)}")
