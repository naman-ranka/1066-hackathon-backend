# llm/utils.py
import os
import requests

def upload_to_gemini(file_path, mime_type):
    """
    Upload the file to Gemini using their REST API.
    Replace the upload URL and payload according to Gemini documentation.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in environment variables.")

    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    # Replace with the actual Gemini file upload endpoint.
    upload_url = "https://gemini.googleapis.com/v1/upload"
    with open(file_path, "rb") as f:
        files = {
            "file": (os.path.basename(file_path), f, mime_type)
        }
        data = {
            "displayName": os.path.basename(file_path),
            "mimeType": mime_type
        }
        # For testing only: disable SSL verification (do not use in production)
        response = requests.post(upload_url, headers=headers, files=files, data=data, verify=False)
        response.raise_for_status()
        file_info = response.json().get("file")
        if not file_info:
            raise ValueError("Invalid response from Gemini file upload.")
        return file_info

def call_gemini_chat(file_data, prompt):
    """
    Starts a chat session with Gemini by sending the image reference and prompt.
    Replace the chat URL and payload according to Gemini documentation.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in environment variables.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    # Replace with the actual Gemini chat endpoint.
    chat_url = "https://gemini.googleapis.com/v1/chat"
    history = [
        {
            "role": "user",
            "parts": [
                {
                    "fileData": {
                        "mimeType": file_data.get("mimeType"),
                        "fileUri": file_data.get("uri")
                    }
                },
                {
                    "text": prompt
                }
            ]
        }
    ]
    payload = {
        "model": "gemini-2.0-flash-thinking-exp-01-21",
        "generationConfig": {
            "temperature": 0.7,
            "topP": 0.95,
            "topK": 64,
            "maxOutputTokens": 65536,
            "responseMimeType": "text/plain"
        },
        "history": history,
        "message": "Generate response based on the provided prompt and image."
    }
    # For testing only: disable SSL verification (do not use in production)
    response = requests.post(chat_url, headers=headers, json=payload, verify=False)
    response.raise_for_status()
    return response.json()
