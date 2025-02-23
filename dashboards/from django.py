from django.shortcuts import render
from django.db.models import Sum
from bills.models import Bill, Participant

def home(request):
    # Calculate total spent
    total_spent = Bill.objects.aggregate(total=Sum('total_amount'))['total'] or 0

    # Calculate total owed by the user
    total_owed_by_user = Participant.objects.aggregate(total=Sum('amount_owed'))['total'] or 0

    # Calculate total owed to the user
    total_owed_to_user = Participant.objects.aggregate(total=Sum('amount_paid'))['total'] or 0

    # Group-wise balances
    group_balances = Bill.objects.values('name').annotate(total=Sum('total_amount'))

    # Person-wise balances
    person_balances = Participant.objects.values('name').annotate(
        total_paid=Sum('amount_paid'),
        total_owed=Sum('amount_owed')
    )

    context = {
        'total_spent': total_spent,
        'total_owed_by_user': total_owed_by_user,
        'total_owed_to_user': total_owed_to_user,
        'group_balances': group_balances,
        'person_balances': person_balances,
    }

    return render(request, 'dashboards/home.html', context)