from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import render, get_object_or_404
from .personal_expense_serializers import PersonalExpenseSerializer
from .models import Bill, Person
from .personal_expense_services import PersonalExpenseService

@api_view(['POST'])
def save_personal_expense(request):
    """
    API endpoint to create a personal expense.
    Expects the payload to include bill data (with is_personal=True),
    items with shares for the owner, and optional payment info.
    """
    serializer = PersonalExpenseSerializer(data=request.data)
    if serializer.is_valid():
        print("Valid data received:", serializer.validated_data)  # Debugging line
        try:
            # created_by = request.user.profile  # Assuming the logged-in user is the owner
            # temp fix for created_by to avoid dependency on user auth for now
            # person with id 1 is the owner
            created_by = Person.objects.get(id=1)  # Assuming the owner has id 1 for now
            expense = PersonalExpenseService.create_expense(serializer.validated_data, created_by)
            return Response({
                'success': True,
                'expense_id': expense.id,
                'message': 'Personal expense saved successfully'
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=400)
    else:
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=400)

def personal_expense_list(request):
    """
    Render a list of personal expenses (bills with is_personal True)
    for the current user.
    """
    expenses = Bill.objects.filter(is_personal=True, created_by=request.user.profile).order_by('-date')
    return render(request, 'bills_new/personal_expense_list.html', {'expenses': expenses})

def personal_expense_detail(request, expense_id):
    """
    Render details for a specific personal expense.
    """
    expense = get_object_or_404(Bill, id=expense_id, is_personal=True)
    return render(request, 'bills_new/personal_expense_detail.html', {'expense': expense})
