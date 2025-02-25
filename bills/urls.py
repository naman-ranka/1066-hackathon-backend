from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BillViewSet, ParticipantViewSet

router = DefaultRouter()
router.register(r'bills', BillViewSet, basename='bill')
router.register(r'global-participants', ParticipantViewSet, basename='global-participant')

urlpatterns = router.urls
