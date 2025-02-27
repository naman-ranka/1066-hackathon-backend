import os
import base64
import logging
from typing import Optional, List, Dict, Any, Union
from django.conf import settings
import openai
import google.generativeai as genai
import traceback
import pytesseract
from PIL import Image
import io

# Configure logging
logger = logging.getLogger(__name__)

# Model constants
OPENAI_MODEL = "gpt-4o-mini"
GEMINI_MODEL = "gemini-2.0-flash-exp"

def encode_image_to_base64(image_data: bytes) -> str:
    """
    Convert image data to base64 encoded string.
    
    Args:
        image_data: Raw image bytes
        
    Returns:
        Base64 encoded image string with data URL prefix
        
    Raises:
        ValueError: If image encoding fails
    """
    try:
        base64_image = base64.b64encode(image_data).decode("utf-8")
        return f"data:image/jpeg;base64,{base64_image}"
    except Exception as e:
        logger.error(f"Error encoding image: {str(e)}")
        raise ValueError(f"Error encoding image: {str(e)}")

def read_prompt_file() -> str:
    """
    Read and return the content of the prompt file.
    
    Returns:
        String content of prompt file
        
    Raises:
        FileNotFoundError: If prompt file doesn't exist
        IOError: If prompt file can't be read
    """
    prompt_file_path = os.path.join(settings.BASE_DIR, "llm", "prompts", "prompt.txt")
    try:
        with open(prompt_file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.error(f"Prompt file not found at {prompt_file_path}")
        # Fallback to the root prompt file
        root_prompt_path = os.path.join(settings.BASE_DIR, "prompt.txt")
        try:
            with open(root_prompt_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Failed to read root prompt file: {str(e)}")
            raise FileNotFoundError(f"Failed to read prompt file: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to read prompt file: {str(e)}")
        raise IOError(f"Failed to read prompt file: {str(e)}")

def process_receipt_with_openai(image_data: bytes) -> str:
    """
    Process receipt using OpenAI's vision model.
    
    Args:
        image_data: Raw image bytes to process
        
    Returns:
        String response from OpenAI containing structured receipt data
        
    Raises:
        ValueError: If API key is not set
        RuntimeError: If OpenAI API call fails
    """
    # Get API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY is not set in environment variables")
        raise ValueError("OPENAI_API_KEY is not set.")
    
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
        logger.error(f"OpenAI API error: {str(e)}")
        raise RuntimeError(f"OpenAI API error: {str(e)}")
    
def process_receipt_with_gemini(image_bytes: bytes) -> str:
    """
    Process a receipt image using Google's Gemini vision model.
    
    Args:
        image_bytes: Raw image bytes to process
        
    Returns:
        String response from Gemini containing structured receipt data
        
    Raises:
        ValueError: If image data is invalid or API key is not set
        RuntimeError: If Gemini API call fails
    """
    if not image_bytes:
        logger.error("No image data provided")
        raise ValueError("No image data provided. 'image_bytes' is empty or None.")

    # 1. Retrieve the Gemini API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is not set in environment variables")
        raise ValueError("GEMINI_API_KEY is not set in environment variables.")

    # 2. Read prompt from prompt.txt
    try:
        prompt_text = read_prompt_file()
    except Exception as e:
        logger.error(f"Error reading prompt file: {str(e)}")
        raise ValueError(f"Error reading prompt file: {str(e)}")

    # 3. Configure Gemini
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        logger.error(f"Error configuring Gemini: {str(e)}")
        raise RuntimeError(f"Error configuring Gemini: {str(e)}")

    # 4. Create a GenerativeModel with desired settings
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }
    
    try:
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            generation_config=generation_config,
        )
    except Exception as e:
        logger.error(f"Error creating Gemini model: {str(e)}")
        raise RuntimeError(f"Error creating Gemini model: {str(e)}")

    # 5. Prepare a dictionary for the binary image data
    image_dict = {
        "mime_type": "image/jpeg",
        "data": image_bytes,
    }

    # 6. Call the model with both text prompt and the image dict
    try:
        response = model.generate_content(
            contents=[
                prompt_text,
                image_dict
            ]
        )
    except Exception as e:
        logger.error(f"Gemini API error: {str(e)}")
        traceback.print_exc()
        raise RuntimeError(f"Gemini API error during generate_content call: {str(e)}")

    # 7. Validate the response
    if not response:
        logger.error("Gemini call returned no response")
        raise RuntimeError("Gemini call returned no response at all.")
    if not response.text:
        logger.error("Gemini call returned an empty text response")
        raise RuntimeError("Gemini call returned an empty text response.")

    return response.text

def process_multiple_images_ocr(image_list: List[bytes]) -> str:
    """
    Performs OCR on a list of image data and combines the extracted text.
    
    Args:
        image_list: A list of image data in bytes format
    
    Returns:
        A string containing the combined OCR text from all images
        
    Raises:
        ValueError: If image list is empty
        RuntimeError: If OCR processing fails
    """
    if not image_list:
        logger.error("Empty image list provided")
        raise ValueError("Empty image list provided for OCR processing")
    
    combined_text = ""
    for idx, image_data in enumerate(image_list):
        try:
            # Convert bytes to PIL Image using BytesIO
            img = Image.open(io.BytesIO(image_data))
            text = pytesseract.image_to_string(img)
            combined_text += f"\n--- OCR Result for Image {idx + 1} ---\n{text}"
        except Exception as e:
            logger.error(f"Error processing image {idx + 1}: {str(e)}")
            raise RuntimeError(f"Error processing image {idx + 1}: {str(e)}")
    
    return combined_text

"""
Command-line Testing Instructions:

# 1. Install required packages (if not already installed)
pip install pytesseract Pillow openai google-generativeai

# 2. Set up Tesseract (example for Ubuntu)
sudo apt-get update
sudo apt-get install tesseract-ocr
# For Windows, download from: https://github.com/UB-Mannheim/tesseract/wiki

# 3. Run Python shell with Django environment
python manage.py shell

# 4. Test encode_image_to_base64
from llm.utils import encode_image_to_base64
with open('path/to/test_image.jpg', 'rb') as f:
    image_data = f.read()
base64_string = encode_image_to_base64(image_data)
print(base64_string[:100])  # Print first 100 chars

# 5. Test read_prompt_file
from llm.utils import read_prompt_file
prompt = read_prompt_file()
print(prompt)

# 6. Test process_receipt_with_openai
from llm.utils import process_receipt_with_openai
import os
os.environ["OPENAI_API_KEY"] = "your-api-key"  # Set API key
with open('path/to/receipt.jpg', 'rb') as f:
    image_data = f.read()
result = process_receipt_with_openai(image_data)
print(result)

# 7. Test process_receipt_with_gemini
from llm.utils import process_receipt_with_gemini
import os
os.environ["GEMINI_API_KEY"] = "your-api-key"  # Set API key
with open('path/to/receipt.jpg', 'rb') as f:
    image_data = f.read()
result = process_receipt_with_gemini(image_data)
print(result)

# 8. Test process_multiple_images_ocr
from llm.utils import process_multiple_images_ocr
image_paths = ['path/to/receipt1.jpg', 'path/to/receipt2.jpg']
image_list = []
for path in image_paths:
    with open(path, 'rb') as f:
        image_list.append(f.read())
result = process_multiple_images_ocr(image_list)
print(result)
"""