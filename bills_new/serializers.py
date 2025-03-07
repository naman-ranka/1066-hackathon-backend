from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Person, Group, Bill, BillParticipant, BillItem, ItemShare, Payment
from decimal import Decimal
from .models import SplitType



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


class ItemShareSerializer(serializers.Serializer):
    person_id = serializers.IntegerField()
    split_type = serializers.ChoiceField(choices=SplitType.choices, default=SplitType.EQUAL)
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    exact_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    share_units = serializers.IntegerField(required=False, allow_null=True)
    
    def validate(self, data):
        split_type = data.get('split_type')
        
        # Validate that appropriate fields are provided based on split type
        if split_type == SplitType.PERCENTAGE:
            if data.get('percentage') is None:
                raise serializers.ValidationError("Percentage is required for percentage split")
            if data.get('percentage') <= 0 or data.get('percentage') > 100:
                raise serializers.ValidationError("Percentage must be between 0 and 100")
                
        elif split_type == SplitType.EXACT:
            if data.get('exact_amount') is None:
                raise serializers.ValidationError("Exact amount is required for exact split")
            if data.get('exact_amount') < 0:
                raise serializers.ValidationError("Exact amount cannot be negative")
                
        elif split_type == SplitType.SHARES:
            if data.get('share_units') is None:
                raise serializers.ValidationError("Share units are required for shares split")
            if data.get('share_units') <= 0:
                raise serializers.ValidationError("Share units must be positive")
                
        return data

class BillItemSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    shares = ItemShareSerializer(many=True)
    
    def validate(self, data):
        # Verify item has a positive price
        if data.get('price', Decimal('0')) <= 0:
            raise serializers.ValidationError("Item price must be positive")
            
        # Verify item has at least one share
        if not data.get('shares'):
            raise serializers.ValidationError("Item must have at least one share")
            
        # Validate that shares are properly defined based on split type
        item_price = data.get('price', Decimal('0'))
        shares_data = data.get('shares', [])
        
        # For EXACT splits, validate sum matches item price
        exact_splits = [s for s in shares_data if s.get('split_type') == SplitType.EXACT]
        if exact_splits:
            exact_total = sum(Decimal(str(s.get('exact_amount', '0'))) for s in exact_splits)
            if len(exact_splits) == len(shares_data) and abs(exact_total - item_price) > Decimal('0.01'):
                raise serializers.ValidationError(
                    f"Sum of exact amounts ({exact_total}) doesn't match item price ({item_price})"
                )
                
        # For PERCENTAGE splits, validate percentages sum to 100
        percentage_splits = [s for s in shares_data if s.get('split_type') == SplitType.PERCENTAGE]
        if percentage_splits:
            percentage_total = sum(Decimal(str(s.get('percentage', '0'))) for s in percentage_splits)
            if len(percentage_splits) == len(shares_data) and abs(percentage_total - Decimal('100')) > Decimal('0.01'):
                raise serializers.ValidationError(
                    f"Sum of percentages ({percentage_total}) should be 100%"
                )
                
        return data

class PaymentSerializer(serializers.Serializer):
    person_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    def validate(self, data):
        if data.get('amount', Decimal('0')) <= 0:
            raise serializers.ValidationError("Payment amount must be positive")
        return data
    

class ParticipantShareSerializer(serializers.Serializer):
    person_id = serializers.IntegerField()
    owed_amount = serializers.DecimalField(max_digits=10, decimal_places=2)

# Update BillSerializer
class BillSerializer(serializers.Serializer):
    bill = serializers.DictField()
    bill_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    group_id = serializers.IntegerField(required=False, allow_null=True)
    persons = serializers.ListField(child=serializers.IntegerField(), required=False)
    items = BillItemSerializer(many=True)
    bill_paid_by = PaymentSerializer(many=True, required=False)
    bill_participants_share = ParticipantShareSerializer(many=True)
    
    def validate(self, data):
        # Existing validation...
        
        # Calculate expected participant shares
        calculated_shares = {}
        for item_data in data.get('items', []):
            item_price = Decimal(str(item_data.get('price', '0')))
            shares_data = item_data.get('shares', [])
            
            # Calculate share for each person in this item
            for share_data in shares_data:
                person_id = share_data.get('person_id')
                split_type = share_data.get('split_type')
                
                # Calculate share amount
                share_amount = self._calculate_share_amount(
                    share_data, item_price, shares_data
                )
                
                if person_id not in calculated_shares:
                    calculated_shares[person_id] = Decimal('0')
                calculated_shares[person_id] += share_amount
        
        # Get frontend's calculated shares
        frontend_shares = {
            ps.get('person_id'): Decimal(str(ps.get('owed_amount', '0')))
            for ps in data.get('bill_participants_share', [])
        }
        
        # Compare the two sets of calculations
        for person_id, amount in calculated_shares.items():
            if person_id not in frontend_shares:
                raise serializers.ValidationError(
                    f"Person {person_id} has shares in items but is missing from bill_participants_share"
                )
            
            if abs(amount - frontend_shares[person_id]) > Decimal('0.01'):
                raise serializers.ValidationError(
                    f"Calculated share for person {person_id} is {amount}, but frontend sent {frontend_shares[person_id]}"
                )
        
        # Also check if frontend sent shares for participants not in items
        for person_id in frontend_shares:
            if person_id not in calculated_shares:
                raise serializers.ValidationError(
                    f"Person {person_id} is in bill_participants_share but has no shares in any items"
                )
        
        return data
    
    def _calculate_share_amount(self, share_data, item_price, all_shares_data):
        """Helper method to calculate share amount for validation"""
        split_type = share_data.get('split_type')
        
        if split_type == SplitType.EXACT:
            return Decimal(str(share_data.get('exact_amount', '0')))
            
        elif split_type == SplitType.PERCENTAGE:
            percentage = Decimal(str(share_data.get('percentage', '0')))
            return item_price * percentage / Decimal('100')
            
        elif split_type == SplitType.SHARES:
            share_units = share_data.get('share_units', 0)
            total_shares = sum(s.get('share_units', 0) for s in all_shares_data 
                              if s.get('split_type') == SplitType.SHARES)
            if total_shares > 0:
                return item_price * Decimal(share_units) / Decimal(total_shares)
                
        else:  # Equal split
            equal_shares = sum(1 for s in all_shares_data if s.get('split_type') == SplitType.EQUAL)
            if equal_shares > 0:
                return item_price / Decimal(equal_shares)
                
        return Decimal('0')
    

