import os
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .utils import (
    process_receipt_with_openai, 
    process_receipt_with_gemini,
    process_images_bytes,
    process_ocr_text_with_llm,
    OCRProvider
)
from .image_preprocessing import enhance_image_for_ocr, batch_process_images
from rest_framework.decorators import api_view
from PIL import Image
import tempfile
import io

class ProcessReceiptView(APIView):
    def post(self, request):
        if not request.FILES.get('image'):
            return Response({"error": "No image file provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        image_file = request.FILES['image']
        if not image_file.content_type.startswith('image/'):
            return Response({"error": "File must be an image"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            image_data = image_file.read()
            # Check pipeline type from request parameters
            pipeline = request.POST.get('pipeline', 'auto')  # default to auto pipeline
            
            if pipeline == 'gemini':
                # Use only Gemini for processing
                if 'GEMINI_API_KEY' not in os.environ:
                    return Response(
                        {"error": "Gemini API key not configured"}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                result = process_receipt_with_gemini(image_data)
                return Response({"result": result, "pipeline": "gemini"}, status=status.HTTP_200_OK)
                
            else:  # auto pipeline - try OpenAI first, fallback to Gemini
                if 'OPENAI_API_KEY' in os.environ:
                    result = process_receipt_with_openai(image_data)
                elif 'GEMINI_API_KEY' in os.environ:
                    result = process_receipt_with_gemini(image_data)
                else:
                    return Response(
                        {"error": "No API keys configured for receipt processing"}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                return Response({"result": result, "pipeline": "auto"}, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def process_bill_images_simple(request):
    """
    Process multiple bill images using basic OCR + LLM pipeline.
    Expected request format:
    - Files can be sent as multipart form data with field names 'files[]', 'file', or 'images'
    - Optional query parameter 'provider': 'google_cloud' or 'tesseract' (defaults to google_cloud)
    - Optional query parameter 'custom_prompt': Custom prompt for LLM processing
    """
    files = request.FILES.getlist('files[]') or request.FILES.getlist('file') or request.FILES.getlist('images')
    
    if not files:
        return Response(
            {"error": "No files uploaded. Please send image files with field name 'files[]', 'file', or 'images'."}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    provider_name = request.POST.get('provider', 'google_cloud')
    custom_prompt = request.POST.get('custom_prompt', None)

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
            
        # Process images with OCR
        ocr_results = process_images_bytes(image_bytes_list, provider)
        
        # Extract and combine OCR text from results
        combined_ocr_text = ""
        for result in ocr_results['results']:
            if 'text' in result:
                combined_ocr_text += result['text'] + "\n\n"
            elif 'error' in result:
                return Response(
                    {'error': f"OCR Error: {result['error']}"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        # Process OCR text with LLM
        try:
            llm_response = process_ocr_text_with_llm(combined_ocr_text, custom_prompt)
            
            response_data = {
                'ocr_results': ocr_results,
                'llm_analysis': llm_response,
                'pipeline': 'simple'
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f"LLM Processing Error: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def process_bill_images_enhanced(request):
    """
    Process multiple bill images using enhanced pipeline with Canny edge detection.
    Expected request format:
    - Files can be sent as multipart form data with field names 'files[]', 'file', or 'images'
    - Optional query parameter 'provider': 'google_cloud' or 'tesseract' (defaults to google_cloud)
    - Optional query parameter 'custom_prompt': Custom prompt for LLM processing
    - Optional image processing parameters:
      - apply_edges: bool (default: True)
      - denoise: bool (default: True)
      - sharpen: bool (default: True)
      - crop_receipt: bool (default: True)
      - edge_low_threshold: int (default: 50)
      - edge_high_threshold: int (default: 150)
    """
    files = request.FILES.getlist('files[]') or request.FILES.getlist('file') or request.FILES.getlist('images')
    
    if not files:
        return Response(
            {"error": "No files uploaded. Please send image files with field name 'files[]', 'file', or 'images'."}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    # Get parameters
    provider_name = request.POST.get('provider', 'google_cloud')
    custom_prompt = request.POST.get('custom_prompt', None)
    
    # Image processing parameters
    apply_edges = request.POST.get('apply_edges', 'true').lower() == 'true'
    denoise = request.POST.get('denoise', 'true').lower() == 'true'
    sharpen = request.POST.get('sharpen', 'true').lower() == 'true'
    crop_receipt = request.POST.get('crop_receipt', 'true').lower() == 'true'
    edge_low_threshold = int(request.POST.get('edge_low_threshold', '50'))
    edge_high_threshold = int(request.POST.get('edge_high_threshold', '150'))

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
            
            file_bytes = file.read()
            image_bytes_list.append(file_bytes)
        
        # Preprocess images with edge detection and enhancement
        processed_images = [
            enhance_image_for_ocr(
                img_data,
                apply_edges=apply_edges,
                denoise=denoise,
                sharpen=sharpen,
                crop_receipt=crop_receipt,
                edge_params={
                    'low_threshold': edge_low_threshold,
                    'high_threshold': edge_high_threshold
                }
            ) for img_data in image_bytes_list
        ]
            
        # Process the preprocessed images with OCR
        ocr_results = process_images_bytes(processed_images, provider)
        
        # Extract and combine OCR text from results
        combined_ocr_text = ""
        for result in ocr_results['results']:
            if 'text' in result:
                combined_ocr_text += result['text'] + "\n\n"
            elif 'error' in result:
                return Response(
                    {'error': f"OCR Error: {result['error']}"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        # Process OCR text with LLM
        try:
            llm_response = process_ocr_text_with_llm(combined_ocr_text, custom_prompt)
            
            response_data = {
                'ocr_results': ocr_results,
                'llm_analysis': llm_response,
                'pipeline': 'enhanced',
                'preprocessing_params': {
                    'apply_edges': apply_edges,
                    'denoise': denoise,
                    'sharpen': sharpen,
                    'crop_receipt': crop_receipt,
                    'edge_low_threshold': edge_low_threshold,
                    'edge_high_threshold': edge_high_threshold
                }
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f"LLM Processing Error: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
