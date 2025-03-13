from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
# router.register(r'persons', views.PersonViewSet)
# router.register(r'groups', views.GroupViewSet)
# router.register(r'bills', views.BillViewSet)
# router.register(r'bill-participants', views.BillParticipantViewSet)
# router.register(r'bill-items', views.BillItemViewSet)
# router.register(r'item-shares', views.ItemShareViewSet)
# router.register(r'payments', views.PaymentViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('save/', views.save_bill, name='save_bill'),
    path('list/', views.bill_list, name='bill_list'),
    path('detail/<int:bill_id>/', views.bill_detail, name='bill_detail'),
    path('groups/', views.get_groups, name='get_groups'),
    path('groups/<int:group_id>/', views.get_group_detail, name='get_group_detail'),
    path('groups/<int:group_id>/participants/', views.get_group_participants, name='get_group_participants'),

    path('dashboard/', views.person_balance_dashboard, name='balance_dashboard'),
    path('dashboard/<int:person_id>/', views.person_balance_dashboard, name='person_balance_dashboard'),
]