import os
import base64
from django.conf import settings
import openai
import google.generativeai as genai
from google.genai import types
import traceback


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
    
def process_receipt_with_gemini(image_bytes):
    """
    Process a receipt image (in raw bytes) using Google's Gemini vision model.
    
    - Reads the text prompt from prompt.txt.
    - Passes both the prompt text (string) and the image bytes (dictionary) 
      to generate_content().
    - Returns the text from Gemini's response.
    """
    if not image_bytes:
        raise ValueError("No image data provided. 'image_bytes' is empty or None.")

    # 1. Retrieve the Gemini API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY is not set in environment variables.")

    # 2. Read prompt from prompt.txt
    try:
        prompt_text = read_prompt_file()
    except Exception as e:
        raise Exception(f"Error reading prompt file: {str(e)}")

    # 3. Configure Gemini
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        raise Exception(f"Error configuring Gemini: {str(e)}")

    # 4. Create a GenerativeModel with desired settings
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        generation_config=generation_config,
    )

    # 5. Prepare a dictionary for the binary image data
    #    The library expects either a string, a dict, or an Image object in 'contents'.
    image_dict = {
        "mime_type": "image/jpeg",
        "data": image_bytes,
    }

    # 6. Call the model with both text prompt and the image dict in a single request
    try:
        response = model.generate_content(
            contents=[
                prompt_text,
                image_dict
            ]
        )
    except Exception as e:
        traceback.print_exc()
        raise RuntimeError(f"Gemini API error during generate_content call: {str(e)}")

    # 7. Validate the response
    if not response:
        raise RuntimeError("Gemini call returned no response at all.")
    if not response.text:
        raise RuntimeError("Gemini call returned an empty text response.")

    return response.text