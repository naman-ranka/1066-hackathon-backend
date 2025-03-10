import os
import base64
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .utils import process_receipt_with_openai, process_receipt_with_gemini
from rest_framework.decorators import api_view
from .utils import process_images, process_images_bytes
from PIL import Image
from .utils import OCRProvider
import tempfile
import io


class ProcessReceiptView(APIView):
    """
    Accepts an image upload and processes it using the configured LLM.
    """
    def post(self, request, format=None):
        if "file" not in request.FILES:
            return Response(
                {"error": "No file uploaded."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            image_data = request.FILES["file"].read()
            bill_content = process_receipt_with_gemini(image_data)
            return Response(
                {"bill": bill_content}, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['POST'])
def process_bill_images(request):
    """
    Process multiple bill images using specified OCR provider.
    Expected request format:
    Files can be sent as multipart form data with field names 'files[]', 'file', or 'images'
    Optional query parameter 'provider': 'google_cloud' or 'tesseract' (defaults to google_cloud)
    """
    # Check for files in both standard file upload and multipart form data
    files = request.FILES.getlist('files[]') or request.FILES.getlist('file') or request.FILES.getlist('images')
    
    if not files:
        return Response(
            {"error": "No files uploaded. Please send image files with field name 'files[]', 'file', or 'images'."}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    provider_name = request.POST.get('provider', 'google_cloud')

    try:
        # Validate provider
        try:
            provider = OCRProvider(provider_name)
        except ValueError:
            return Response(
                {'error': f'Invalid provider. Choose from: {[p.value for p in OCRProvider]}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Process images directly from memory
        image_bytes_list = []
        
        for file in files:
            if not file.content_type.startswith('image/'):
                return Response(
                    {"error": f"Invalid file type: {file.content_type}. Please upload only image files."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Read the file content directly
            file_bytes = file.read()
            image_bytes_list.append(file_bytes)
            
        # Process the images directly from bytes
        results = process_images_bytes(image_bytes_list, provider)
        
        return Response(results, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )