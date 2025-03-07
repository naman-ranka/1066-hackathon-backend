from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from .models import Person, Group, Bill, BillParticipant, BillItem, ItemShare, Payment


class ItemShareInline(admin.TabularInline):
    model = ItemShare
    extra = 0
    fields = ['person', 'split_type', 'percentage', 'exact_amount', 'share_units', 'share_amount']
    readonly_fields = ['share_amount']


class BillItemInline(admin.TabularInline):
    model = BillItem
    extra = 0
    fields = ['name', 'price']
    show_change_link = True


class BillParticipantInline(admin.TabularInline):
    model = BillParticipant
    extra = 0
    fields = ['person', 'owed_amount', 'paid_amount', 'balance']
    readonly_fields = ['paid_amount', 'balance']


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ['person', 'amount', 'date', 'description']
    fk_name = 'bill'


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ['username', 'get_full_name', 'email', 'phone_number']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'user__email', 'phone_number']
    list_filter = ['member_groups']
    
    def username(self, obj):
        return obj.user.username
    
    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or "-"
    get_full_name.short_description = "Full Name"
    
    def email(self, obj):
        return obj.user.email


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'created_at', 'member_count']
    search_fields = ['name', 'description', 'created_by__user__username']
    list_filter = ['created_at']
    filter_horizontal = ['members']
    
    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = "Members"


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ['title', 'date', 'created_by', 'group', 'total_amount', 'total_paid', 'remaining_balance']
    list_filter = ['date', 'created_by', 'group']
    search_fields = ['title', 'description', 'created_by__user__username']
    date_hierarchy = 'date'
    inlines = [BillItemInline, BillParticipantInline, PaymentInline]
    
    def total_paid(self, obj):
        total = obj.payments.aggregate(Sum('amount'))['amount__sum'] or 0
        return f"${total:.2f}"
    total_paid.short_description = "Paid Amount"
    
    def remaining_balance(self, obj):
        total_amount = obj.total_amount
        total_paid = obj.payments.aggregate(Sum('amount'))['amount__sum'] or 0
        remaining = total_amount - total_paid
        
        # Format with color based on whether bill is fully paid
        if remaining <= 0:
            return format_html('<span style="color: green;">${:.2f}</span>', remaining)
        else:
            return format_html('<span style="color: red;">${:.2f}</span>', remaining)
    remaining_balance.short_description = "Remaining"
    

@admin.register(BillParticipant)
class BillParticipantAdmin(admin.ModelAdmin):
    list_display = ['bill', 'person', 'owed_amount', 'paid_amount', 'balance', 'status']
    list_filter = ['bill', 'person']
    search_fields = ['bill__title', 'person__user__username']
    
    def status(self, obj):
        balance = obj.balance
        if balance > 0:
            return format_html('<span style="color: green;">Overpaid</span>')
        elif balance < 0:
            return format_html('<span style="color: red;">Owes money</span>')
        else:
            return format_html('<span style="color: blue;">Settled</span>')


@admin.register(BillItem)
class BillItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'bill', 'price']
    list_filter = ['bill']
    search_fields = ['name', 'bill__title']
    inlines = [ItemShareInline]


@admin.register(ItemShare)
class ItemShareAdmin(admin.ModelAdmin):
    list_display = ['item', 'person', 'split_type', 'display_share_details', 'share_amount']
    list_filter = ['split_type', 'person', 'item__bill']
    search_fields = ['person__user__username', 'item__name', 'item__bill__title']
    
    def display_share_details(self, obj):
        if obj.split_type == 'EQUAL':
            return "Equal Split"
        elif obj.split_type == 'PERCENTAGE':
            return f"{obj.percentage}%"
        elif obj.split_type == 'EXACT':
            return f"${obj.exact_amount}"
        elif obj.split_type == 'SHARES':
            return f"{obj.share_units} shares"
        else:
            return "Adjusted"
    display_share_details.short_description = "Share Details"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_type', 'person', 'other_person', 'amount', 'date', 'bill', 'description']
    list_filter = ['payment_type', 'date', 'person']
    search_fields = ['person__user__username', 'other_person__user__username', 'description', 'bill__title']
    date_hierarchy = 'date'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Filter to show only relevant bills in dropdown
        if db_field.name == "bill" and not kwargs.get('request'):
            kwargs['queryset'] = Bill.objects.filter(payment_type='BILL')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
