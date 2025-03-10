import os
import base64
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .utils import process_receipt_with_openai, process_receipt_with_gemini
from .multipleimageocr import get_ocr_text_from_multiple_images
import json
import tempfile
from PIL import Image
import io
from django.http import JsonResponse
from rest_framework.decorators import api_view
from .utils import process_images, OCRProvider, save_ocr_results
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

@method_decorator(csrf_exempt, name='dispatch')
class ProcessReceiptView(APIView):
    """
    Accepts image upload(s) and processes them using OCR and/or LLM based on the flag.
    """
    def post(self, request, format=None):
        # Check for files in both standard file upload and multipart form data
        files = request.FILES.getlist('files[]') or request.FILES.getlist('file') or request.FILES.getlist('images')
        
        if not files:
            return Response(
                {"error": "No files uploaded. Please send image files with field name 'files[]', 'file', or 'images'."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get processing flag from request
        use_ocr = request.POST.get('use_ocr', 'false').lower() == 'true'
        
        try:
            # Store file contents first
            file_contents = []
            for file in files:
                if not file.content_type.startswith('image/'):
                    return Response(
                        {"error": f"Invalid file type: {file.content_type}. Please upload only image files."}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                file_contents.append(file.read())
            
            # Create temporary files for OCR processing if needed
            temp_files = []
            ocr_text = None
            
            if use_ocr:
                for content in file_contents:
                    # Create a temporary file
                    temp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                    # Save the file content
                    image = Image.open(io.BytesIO(content))
                    image.save(temp.name)
                    temp_files.append(temp.name)
                
                # Process with OCR
                ocr_text = get_ocr_text_from_multiple_images(temp_files)
                
                # Clean up temporary files
                for temp_file in temp_files:
                    os.unlink(temp_file)
                
                if not ocr_text:
                    return Response(
                        {"error": "OCR processing failed"}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            
            # Process with LLM (using the first image)
            bill_content = process_receipt_with_gemini(file_contents[0])
            
            # Prepare response based on processing type
            response_data = {"bill": bill_content}
            if ocr_text:
                response_data["ocr_text"] = ocr_text
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"Error processing receipt: {str(e)}"}, 
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

        # Convert uploaded files to base64
        images_base64 = []
        temp_files = []

        for file in files:
            if not file.content_type.startswith('image/'):
                return Response(
                    {"error": f"Invalid file type: {file.content_type}. Please upload only image files."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create temporary file
            temp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            # Save the file content
            image = Image.open(io.BytesIO(file.read()))
            image.save(temp.name)
            temp_files.append(temp.name)

        # Process images
        results = process_images(temp_files, provider)

        # Clean up temporary files
        for temp_file in temp_files:
            os.unlink(temp_file)
        
        # Save results to file
        output_path = os.path.join(settings.BASE_DIR, 'ocr-result.json')
        save_ocr_results(results, output_path)
        
        return Response(results, status=status.HTTP_200_OK)
        
    except Exception as e:
        # Clean up any remaining temporary files
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@method_decorator(csrf_exempt, name='dispatch')
class TestUploadView(TemplateView):
    template_name = 'test_upload.html'
