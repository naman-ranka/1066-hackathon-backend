from django.urls import path
from .views import ProcessReceiptView
from . import views

urlpatterns = [
    path('process-receipt/', ProcessReceiptView.as_view(), name='process_receipt'),
    path('process-bill-images/', views.process_bill_images, name='process-bill-images'),
]
