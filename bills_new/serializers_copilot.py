from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Person, Group, Bill, BillParticipant, BillItem, ItemShare, Payment


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']
        extra_kwargs = {'password': {'write_only': True}}


class PersonSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)

    class Meta:
        model = Person
        fields = ['id', 'user', 'username', 'first_name', 'last_name', 'email', 'phone_number', 'profile_picture']


class GroupSerializer(serializers.ModelSerializer):
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ['id', 'name', 'description', 'created_at', 'created_by', 'members', 'members_count']
    
    def get_members_count(self, obj):
        return obj.members.count()


class BillItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillItem
        fields = ['id', 'bill', 'name', 'price']


class ItemShareSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemShare
        fields = ['id', 'item', 'person', 'split_type', 'percentage', 'exact_amount', 
                 'share_units', 'share_amount']
        read_only_fields = ['share_amount']


class BillParticipantSerializer(serializers.ModelSerializer):
    paid_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = BillParticipant
        fields = ['id', 'bill', 'person', 'owed_amount', 'paid_amount', 'balance']
    
    def create(self, validated_data):
        participant = super().create(validated_data)
        # Calculate and set the owed amount when creating a participant
        participant.calculate_owed_amount()
        return participant


class BillSerializer(serializers.ModelSerializer):
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    items = BillItemSerializer(many=True, read_only=True)
    bill_participants = BillParticipantSerializer(many=True, read_only=True)

    class Meta:
        model = Bill
        fields = ['id', 'title', 'description', 'date', 'created_at', 'created_by', 
                 'group', 'participants', 'total_amount', 'items', 'bill_participants']


class PaymentSerializer(serializers.ModelSerializer):
    paired_payment_id = serializers.PrimaryKeyRelatedField(source='paired_payment', read_only=True)
    
    class Meta:
        model = Payment
        fields = ['id', 'payment_type', 'person', 'other_person', 'bill', 'amount', 
                 'date', 'description', 'paired_payment_id']
        read_only_fields = ['paired_payment_id']
    
    def create(self, validated_data):
        """
        Override create method to use the appropriate class method based on payment_type
        """
        payment_type = validated_data.get('payment_type')
        person = validated_data.get('person')
        date = validated_data.get('date')
        description = validated_data.get('description', '')
        
        if payment_type == 'SETTLEMENT':
            other_person = validated_data.get('other_person')
            amount = validated_data.get('amount')
            if not other_person:
                raise serializers.ValidationError({"other_person": "Required for settlements"})
                
            payment = Payment.create_settlement(
                from_person=person,
                to_person=other_person,
                amount=amount,
                date=date,
                description=description
            )
            return payment
            
        elif payment_type == 'BILL':
            bill = validated_data.get('bill')
            amount = validated_data.get('amount')
            if not bill:
                raise serializers.ValidationError({"bill": "Required for bill payments"})
                
            payment = Payment.create_bill_payment(
                person=person,
                bill=bill,
                amount=amount,
                date=date,
                description=description
            )
            return payment
            
        return super().create(validated_data)