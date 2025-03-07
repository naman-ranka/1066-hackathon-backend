from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import render, get_object_or_404
from .serializers import BillSerializer, GroupSerializer, PersonSerializer
from .services import BillService
from .models import Bill, BillParticipant, BillItem, ItemShare, Payment, Group, Person


@api_view(['POST'])
# @permission_classes([IsAuthenticated])
def save_bill(request):
    """
    API endpoint to save a new bill with all related data.
    """
    print(request.data)
    serializer = BillSerializer(data=request.data)
    
    
    if serializer.is_valid():
        try:
            # Get current user's profile
            # created_by = request.user.profile
            # For now, use the first person as the creator
            created_by = Person.objects.first()

            # Create bill using service
            bill = BillService.create_bill(serializer.validated_data, created_by)
            
            return Response({
                'success': True,
                'bill_id': bill.id,
                'message': 'Bill saved successfully'
            })
        except Exception as e:
            # All database operations will be rolled back due to @transaction.atomic
            return Response({
                'success': False,
                'error': str(e)
            }, status=400)
    else:
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=400)

def bill_list(request):
    """View to display all bills in a list"""
    bills = Bill.objects.all().order_by('-date')
    return render(request, 'bills_new/bill_list.html', {'bills': bills})

def bill_detail(request, bill_id):
    """View to display detailed information about a specific bill"""
    bill = Bill.objects.get(id=bill_id)
    participants = BillParticipant.objects.filter(bill=bill)
    items = BillItem.objects.select_related('bill').prefetch_related('shares__person').filter(bill=bill)
    payments = Payment.objects.filter(bill=bill)
    
    # Calculate total bill amount
    total_amount = sum(item.price for item in items)
    
    # Calculate total paid amount
    total_paid = sum(payment.amount for payment in payments)
    
    # Calculate shares by type for each item and total shares
    for item in items:
        shares = item.shares.all()
        item.shares_by_type = {
            'SHARES': {
                'count': sum(1 for s in shares if s.split_type == 'SHARES'),
                'total_units': sum(s.share_units or 0 for s in shares if s.split_type == 'SHARES')
            },
            'EQUAL': sum(1 for s in shares if s.split_type == 'EQUAL'),
            'PERCENTAGE': sum(1 for s in shares if s.split_type == 'PERCENTAGE'),
            'EXACT': sum(1 for s in shares if s.split_type == 'EXACT')
        }
    
    context = {
        'bill': bill,
        'participants': participants,
        'items': items,
        'payments': payments,
        'total_amount': total_amount,
        'total_paid': total_paid,
        'remaining_amount': total_amount - total_paid
    }
    return render(request, 'bills_new/bill_detail.html', context)

@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def get_groups(request):
    """
    API endpoint to fetch all groups.
    Optionally filter by groups created by the authenticated user or groups where user is a member.
    """
    # Get query parameters
    created_by_me = request.query_params.get('created_by_me', 'false').lower() == 'true'
    member_of = request.query_params.get('member_of', 'false').lower() == 'true'
    
    groups = Group.objects.all()
    
    # Apply filters if the user is authenticated
    if request.user.is_authenticated:
        person = request.user.profile
        if created_by_me:
            groups = groups.filter(created_by=person)
        if member_of:
            groups = groups.filter(members=person)
    
    # Order by most recently created
    groups = groups.order_by('-created_at')
    
    serializer = GroupSerializer(groups, many=True)
    return Response({
        'success': True,
        'groups': serializer.data
    })

@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def get_group_detail(request, group_id):
    """
    API endpoint to fetch details of a specific group including its members.
    """
    group = get_object_or_404(Group, id=group_id)
    
    # Serialize the group
    group_serializer = GroupSerializer(group)
    
    # Serialize the group members
    members = group.members.all()
    members_serializer = PersonSerializer(members, many=True)
    
    return Response({
        'success': True,
        'group': group_serializer.data,
        'members': members_serializer.data
    })

@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def get_group_participants(request, group_id):
    """
    API endpoint to fetch participants (members) of a specific group.
    """
    group = get_object_or_404(Group, id=group_id)
    
    # Get all members of the group
    members = group.members.all()
    
    # Serialize the members
    serializer = PersonSerializer(members, many=True)
    
    return Response({
        'success': True,
        'participants': serializer.data
    })



