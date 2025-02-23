import os
import base64
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import openai

class ProcessReceiptView(APIView):
    """
    Accepts an image upload, encodes the image in Base64, and calls OpenAI's Chat API.
    """

    def post(self, request, format=None):
        # Check if an image file is provided
        if "file" not in request.FILES:
            return Response({"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)
        
        image_file = request.FILES["file"]
        
        try:
            # Read image data from the uploaded file
            image_data = image_file.read()
            # Encode the image to Base64
            base64_image = base64.b64encode(image_data).decode("utf-8")
            # Construct the data URL for the image
            data_url = f"data:image/jpeg;base64,{base64_image}"
        except Exception as e:
            return Response({"error": f"Error encoding image: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Read the prompt from prompt.txt (placed at your project root)
        prompt_file_path = os.path.join(settings.BASE_DIR, "prompt.txt")
        try:
            with open(prompt_file_path, "r", encoding="utf-8") as f:
                prompt = f.read().strip()
        except Exception as e:
            return Response({"error": f"Failed to read prompt file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Initialize the OpenAI client using the API key from environment variables
        openai.api_key = os.environ.get("OPENAI_API_KEY")
        if not openai.api_key:
            return Response({"error": "OPENAI_API_KEY is not set."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        try:
            # Call the OpenAI Chat API using your provided code
            response = openai.chat.completions.create(
                model="gpt-4o-mini",  # Adjust the model as needed
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
        except Exception as e:
            return Response({"error": f"OpenAI API error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Return only the bill content extracted from the LLM response.
        bill_content = response.choices[0].message.content
        print(bill_content)
        return Response({"bill": bill_content}, status=status.HTTP_200_OK)
