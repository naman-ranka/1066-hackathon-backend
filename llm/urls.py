from django.urls import path
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    path('process-receipt/', views.ProcessReceiptView.as_view(), name='process_receipt'),
    path('process-images/', views.process_images, name='process_images'),
    path('process-bill-images/', views.process_bill_images, name='process-bill-images'),
    path('test-bill-upload/', TemplateView.as_view(template_name='test_bill_upload.html'), name='test-bill-upload')
]
