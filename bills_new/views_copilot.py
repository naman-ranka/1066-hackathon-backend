from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.models import User, AnonymousUser
from .models import Person, Group, Bill, BillParticipant, BillItem, ItemShare, Payment
from .serializers import (
    PersonSerializer, UserSerializer, GroupSerializer, BillSerializer, 
    BillParticipantSerializer, BillItemSerializer, 
    ItemShareSerializer, PaymentSerializer
)


class PersonViewSet(viewsets.ModelViewSet):
    queryset = Person.objects.all()
    serializer_class = PersonSerializer
    permission_classes = [permissions.AllowAny]  # Temporarily allow any access for testing
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Return the current authenticated user's information"""
        if isinstance(request.user, AnonymousUser):
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
            
        try:
            person = Person.objects.get(user=request.user)
            serializer = self.get_serializer(person)
            return Response(serializer.data)
        except Person.DoesNotExist:
            # Create a person profile for this user if it doesn't exist
            person = Person.objects.create(user=request.user)
            serializer = self.get_serializer(person)
            return Response(serializer.data)


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.AllowAny]  # Temporarily allow any access for testing
    
    def get_queryset(self):
        """Filter groups to show only those the user is a member of"""
        user = self.request.user
        
        # For anonymous users or during testing, return all groups
        if isinstance(user, AnonymousUser):
            return Group.objects.all()
            
        try:
            person = Person.objects.get(user=user)
            return person.member_groups.all()
        except Person.DoesNotExist:
            return Group.objects.none()
    
    def perform_create(self, serializer):
        """Set the current user as the creator and add them as a member"""
        if isinstance(self.request.user, AnonymousUser):
            # For testing purposes, use the first person in the database
            person = Person.objects.first()
            if not person:
                raise ValueError("Cannot create group: no Person objects in database and user is anonymous")
        else:
            person, created = Person.objects.get_or_create(user=self.request.user)
            
        group = serializer.save(created_by=person)
        group.members.add(person)
    
    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        """Add a member to the group"""
        group = self.get_object()
        user_id = request.data.get('user_id')
        
        try:
            person = Person.objects.get(pk=user_id)
            group.members.add(person)
            return Response({'status': 'Member added'}, status=status.HTTP_200_OK)
        except Person.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def remove_member(self, request, pk=None):
        """Remove a member from the group"""
        group = self.get_object()
        user_id = request.data.get('user_id')
        
        try:
            person = Person.objects.get(pk=user_id)
            # Don't allow removing the creator
            if person == group.created_by:
                return Response({'error': 'Cannot remove the group creator'}, status=status.HTTP_400_BAD_REQUEST)
            
            group.members.remove(person)
            return Response({'status': 'Member removed'}, status=status.HTTP_200_OK)
        except Person.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


class BillViewSet(viewsets.ModelViewSet):
    queryset = Bill.objects.all()
    serializer_class = BillSerializer
    permission_classes = [permissions.AllowAny]  # Temporarily allow any access for testing
    
    def get_queryset(self):
        """Filter bills to show only those the user is involved with"""
        user = self.request.user
        
        # For anonymous users or during testing, return all bills
        if isinstance(user, AnonymousUser):
            return Bill.objects.all()
            
        try:
            person = Person.objects.get(user=user)
            return Bill.objects.filter(participants=person)
        except Person.DoesNotExist:
            return Bill.objects.none()
    
    def perform_create(self, serializer):
        """Set the current user as the creator and add them as a participant"""
        if isinstance(self.request.user, AnonymousUser):
            # For testing purposes, use the first person in the database
            person = Person.objects.first()
            if not person:
                raise ValueError("Cannot create bill: no Person objects in database and user is anonymous")
        else:
            person, created = Person.objects.get_or_create(user=self.request.user)
            
        bill = serializer.save(created_by=person)
        
        # Create a participant record for the creator with zero owed_amount
        # The owed_amount will be calculated when items are added and shared
        participant = BillParticipant.objects.create(bill=bill, person=person)
        participant.calculate_owed_amount()  # Calculate the initial owed amount
    
    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        """Get detailed information about a bill including items and participants"""
        bill = self.get_object()
        bill_data = BillSerializer(bill).data
        items_data = BillItemSerializer(bill.items.all(), many=True).data
        participants_data = BillParticipantSerializer(bill.bill_participants.all(), many=True).data
        
        return Response({
            'bill': bill_data,
            'items': items_data,
            'participants': participants_data
        })
    
    @action(detail=True, methods=['post'])
    def recalculate_shares(self, request, pk=None):
        """Recalculate all participants' owed amounts for this bill"""
        bill = self.get_object()
        
        for participant in bill.bill_participants.all():
            participant.calculate_owed_amount()
        
        return Response({'status': 'Bill shares recalculated'}, status=status.HTTP_200_OK)


class BillParticipantViewSet(viewsets.ModelViewSet):
    queryset = BillParticipant.objects.all()
    serializer_class = BillParticipantSerializer
    permission_classes = [permissions.AllowAny]  # Temporarily allow any access for testing
    
    @action(detail=True, methods=['post'])
    def calculate_owed(self, request, pk=None):
        """Calculate and update the owed amount for this participant"""
        participant = self.get_object()
        owed_amount = participant.calculate_owed_amount()
        
        return Response({
            'person_id': participant.person.id,
            'bill_id': participant.bill.id,
            'owed_amount': owed_amount
        })


class BillItemViewSet(viewsets.ModelViewSet):
    queryset = BillItem.objects.all()
    serializer_class = BillItemSerializer
    permission_classes = [permissions.AllowAny]  # Temporarily allow any access for testing
    
    def perform_create(self, serializer):
        """After creating a bill item, recalculate shares if there are any"""
        item = serializer.save()
        
        # After creating an item, recalculate all participants' owed amounts
        for participant in item.bill.bill_participants.all():
            participant.calculate_owed_amount()


class ItemShareViewSet(viewsets.ModelViewSet):
    queryset = ItemShare.objects.all()
    serializer_class = ItemShareSerializer
    permission_classes = [permissions.AllowAny]  # Temporarily allow any access for testing
    
    def perform_create(self, serializer):
        """After creating an item share, recalculate the participant's owed amount"""
        share = serializer.save()
        
        # Get the bill participant for this person and bill
        bill = share.item.bill
        person = share.person
        
        try:
            participant = BillParticipant.objects.get(bill=bill, person=person)
        except BillParticipant.DoesNotExist:
            # If the person is not yet a participant in the bill, create a participant record
            participant = BillParticipant.objects.create(bill=bill, person=person)
        
        # Update the owed amount
        participant.calculate_owed_amount()


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.AllowAny]  # Temporarily allow any access for testing
    
    def get_queryset(self):
        """Filter payments to show only those the user is involved with"""
        user = self.request.user
        
        # For anonymous users or during testing, return all payments
        if isinstance(user, AnonymousUser):
            return Payment.objects.all()
            
        try:
            person = Person.objects.get(user=user)
            # Show both payments made by this person and payments involving this person
            return Payment.objects.filter(person=person) | Payment.objects.filter(other_person=person)
        except Person.DoesNotExist:
            return Payment.objects.none()
    
    @action(detail=False, methods=['get'])
    def settlements(self, request):
        """Get only settlement payments"""
        base_queryset = self.get_queryset()
        settlements = base_queryset.filter(payment_type='SETTLEMENT')
        serializer = self.get_serializer(settlements, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def bill_payments(self, request):
        """Get only bill payments"""
        base_queryset = self.get_queryset()
        bill_payments = base_queryset.filter(payment_type='BILL')
        serializer = self.get_serializer(bill_payments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_bill(self, request):
        """Get all payments for a specific bill"""
        bill_id = request.query_params.get('bill_id')
        if not bill_id:
            return Response({"error": "bill_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            bill = Bill.objects.get(pk=bill_id)
            payments = Payment.objects.filter(bill=bill)
            serializer = self.get_serializer(payments, many=True)
            return Response(serializer.data)
        except Bill.DoesNotExist:
            return Response({"error": "Bill not found"}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'])
    def create_settlement(self, request):
        """Create a settlement payment between two users"""
        from_person_id = request.data.get('from_person')
        to_person_id = request.data.get('to_person')
        amount = request.data.get('amount')
        date = request.data.get('date')
        description = request.data.get('description', '')
        
        # Validate required fields
        if not all([from_person_id, to_person_id, amount, date]):
            return Response(
                {"error": "from_person, to_person, amount, and date are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            from_person = Person.objects.get(pk=from_person_id)
            to_person = Person.objects.get(pk=to_person_id)
            
            payment = Payment.create_settlement(
                from_person=from_person,
                to_person=to_person,
                amount=float(amount),
                date=date,
                description=description
            )
            
            serializer = self.get_serializer(payment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Person.DoesNotExist:
            return Response({"error": "One or both persons not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def create_bill_payment(self, request):
        """Create a payment toward a bill"""
        person_id = request.data.get('person')
        bill_id = request.data.get('bill')
        amount = request.data.get('amount')
        date = request.data.get('date')
        description = request.data.get('description', '')
        
        # Validate required fields
        if not all([person_id, bill_id, amount, date]):
            return Response(
                {"error": "person, bill, amount, and date are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            person = Person.objects.get(pk=person_id)
            bill = Bill.objects.get(pk=bill_id)
            
            payment = Payment.create_bill_payment(
                person=person,
                bill=bill,
                amount=float(amount),
                date=date,
                description=description
            )
            
            serializer = self.get_serializer(payment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Person.DoesNotExist:
            return Response({"error": "Person not found"}, status=status.HTTP_404_NOT_FOUND)
        except Bill.DoesNotExist:
            return Response({"error": "Bill not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def balance(self, request):
        """Get a person's overall balance across all settlements"""
        person_id = request.query_params.get('person_id')
        
        if not person_id:
            return Response({"error": "person_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            person = Person.objects.get(pk=person_id)
            balance = Payment.get_balance(person)
            
            return Response({
                "person_id": person_id,
                "balance": balance,
                "status": "positive" if balance >= 0 else "negative"
            })
        except Person.DoesNotExist:
            return Response({"error": "Person not found"}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'])
    def balance_between(self, request):
        """Get the balance between two people"""
        person1_id = request.query_params.get('person1_id')
        person2_id = request.query_params.get('person2_id')
        
        if not all([person1_id, person2_id]):
            return Response({"error": "person1_id and person2_id are required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            person1 = Person.objects.get(pk=person1_id)
            person2 = Person.objects.get(pk=person2_id)
            
            balance = Payment.get_balance_between(person1, person2)
            
            return Response({
                "person1_id": person1_id,
                "person2_id": person2_id,
                "balance": balance,
                "status": "owes" if balance < 0 else "is owed" if balance > 0 else "settled"
            })
        except Person.DoesNotExist:
            return Response({"error": "One or both persons not found"}, status=status.HTTP_404_NOT_FOUND)
