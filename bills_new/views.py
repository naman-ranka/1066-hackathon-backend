from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import render, get_object_or_404
from .serializers import BillSerializer, GroupSerializer, PersonSerializer, SettlementPaymentSerializer
from .services import BillService
from .models import Bill, BillParticipant, BillItem, ItemShare, Payment, Group, Person
from django.db.models import Sum, Q
from decimal import Decimal
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User




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



def person_balance_dashboard(request, person_id=None):
    """
    View to display a person's balance dashboard showing all their transactions,
    both in bill-wise and item-wise views, along with all payments.
    
    If person_id is not provided, uses the logged-in user's person.
    """
    # Determine which person to show
    if person_id:
        person = get_object_or_404(Person, id=person_id)
        # Check if the current user has permission to view this person's data
        # if person.user != request.user and not request.user.is_staff:
        #     return render(request, '403.html', {'message': 'You do not have permission to view this data.'}, status=403)
    else:
        # Use the logged-in user's person profile
        person = request.user.profile
    
    # Get all bill participations
    bill_participations = BillParticipant.objects.filter(person=person)
    
    # For each participation, get the items and payments
    for participation in bill_participations:
        # Get all items shared by this person in this bill
        participation.bill_items = ItemShare.objects.filter(
            person=person,
            item__bill=participation.bill
        ).select_related('item')
        
        # Calculate total share units for each item
        for share in participation.bill_items:
            if share.split_type == 'SHARES':
                share.item.shares_total_units = ItemShare.objects.filter(
                    item=share.item,
                    split_type='SHARES'
                ).aggregate(Sum('share_units'))['share_units__sum'] or 0
        
        # Get all payments by this person for this bill
        participation.payments = Payment.objects.filter(
            payment_type='BILL',
            person=person,
            bill=participation.bill
        ).order_by('-date')
    
    # Get all item shares for detailed item view
    item_shares = ItemShare.objects.filter(
        person=person
    ).select_related('item', 'item__bill').order_by('-item__bill__date')
    
    # Get all bill payments
    bill_payments = Payment.objects.filter(
        person=person,
        # payment_type='BILL'
    )
    
    # Calculate person balances for settlements
    # Find all people that the current person has transactions with
    related_people = Person.objects.filter(
        Q(payments__other_person=person) | Q(involved_payments__person=person)
    ).distinct().exclude(id=person.id)
    
    person_balances = []
    for other_person in related_people:
        # Get balance between current person and other person
        balance = Payment.get_balance_between(person, other_person)
        
        # Get all settlements between these two people
        settlements = Payment.objects.filter(
            payment_type='SETTLEMENT',
            person=person,
            other_person=other_person
        ).order_by('-date')
        
        person_balances.append({
            'person': other_person,
            'balance': balance,
            'settlements': settlements
        })
    
    # Sort by balance (people who owe the current person first)
    person_balances = sorted(person_balances, key=lambda x: x['balance'])
    
    # Calculate overall balance
    total_paid = bill_payments.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    total_owed = sum(p.owed_amount for p in bill_participations)
    settlement_balance = sum(b['balance'] for b in person_balances)
    overall_balance = total_paid - total_owed + settlement_balance
    
    context = {
        'person': person,
        'bill_participations': bill_participations,
        'item_shares': item_shares,
        'bill_payments': bill_payments,
        'person_balances': person_balances,
        'total_paid': total_paid,
        'total_owed': total_owed,
        'overall_balance': overall_balance
    }
    
    return render(request, 'bills_new/person_balance_dashboard.html', context)


@api_view(['POST'])
def save_settlement_api(request):
    """
    API endpoint to save a settlement type payment using a serializer for validation.
    """
    serializer = SettlementPaymentSerializer(data=request.data)
    if serializer.is_valid():
        validated_data = serializer.validated_data
        try:
            from_person = Person.objects.get(id=validated_data['from_person_id'])
            to_person = Person.objects.get(id=validated_data['to_person_id'])
            amount = validated_data['amount']
            date = validated_data['date']
            description = validated_data.get('description', '')
            
            # Create the settlement using the Payment model's helper method
            settlement_payment = Payment.create_settlement(from_person, to_person, amount, date, description)
            
            return Response({
                'success': True,
                'message': 'Settlement payment created successfully',
                'settlement_payment_id': settlement_payment.id
            })
        except Person.DoesNotExist as e:
            return Response({'success': False, 'error': str(e)}, status=400)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=400)
    else:
        return Response({'success': False, 'errors': serializer.errors}, status=400)


def settlement_form_view(request):
    """
    Temporary HTML view to render a form for creating settlement payments.
    This view shows a simple form (e.g., with dropdowns populated from Person objects)
    and processes POST requests to create a settlement.
    """
    if request.method == 'POST':
        from_person_id = request.POST.get('from_person_id')
        to_person_id = request.POST.get('to_person_id')
        amount = request.POST.get('amount')
        date = request.POST.get('date')
        description = request.POST.get('description', '')
        
        try:
            from_person = Person.objects.get(id=from_person_id)
            to_person = Person.objects.get(id=to_person_id)
            settlement_payment = Payment.create_settlement(from_person, to_person, Decimal(amount), date, description)
            message = f"Settlement created successfully, payment ID: {settlement_payment.id}"
            persons = Person.objects.all()
            return render(request, 'bills_new/settlement_form.html', {'persons': persons, 'message': message})
        except Exception as e:
            persons = Person.objects.all()
            return render(request, 'bills_new/settlement_form.html', {'persons': persons, 'error': str(e)})
    else:
        persons = Person.objects.all()
        return render(request, 'bills_new/settlement_form.html', {'persons': persons})


def settlement_payments_view(request, person_id=None):
    """
    Temporary view to display settlement payments for a person.
    If person_id is not provided, uses the logged-in user's profile.
    """
    if person_id:
        person = get_object_or_404(Person, id=person_id)
    else:
        # Assumes the user is logged in and has a related profile.
        person = request.user.profile

    # Filter settlement payments (payment_type='SETTLEMENT') for the person.
    settlement_payments = Payment.objects.filter(
        payment_type='SETTLEMENT',
        person=person
    ).order_by('-date')

    context = {
        'person': person,
        'settlement_payments': settlement_payments
    }
    return render(request, 'bills_new/settlement_payments.html', context)