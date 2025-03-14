from django.urls import path
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    path('process-receipt/', views.ProcessReceiptView.as_view(), name='process_receipt'),
    path('process-simple/', views.process_bill_images_simple, name='process-simple'),
    path('process-enhanced/', views.process_bill_images_enhanced, name='process-enhanced'),
    path('test-upload/', TemplateView.as_view(template_name='test_bill_upload.html'), name='test-upload')
]
