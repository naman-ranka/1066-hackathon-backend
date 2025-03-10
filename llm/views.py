import os
import base64
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .utils import process_receipt_with_openai, process_receipt_with_gemini

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
            #print(bill_content)
            print("bill_content: ", bill_content)
            return Response(
                {"bill": bill_content}, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
