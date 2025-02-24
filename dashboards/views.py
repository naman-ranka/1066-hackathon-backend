from django.shortcuts import render
from django.db.models import Sum
from django.db.models.functions import TruncMonth, TruncWeek, TruncYear
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from plotly.utils import PlotlyJSONEncoder
import plotly.graph_objs as go
import json
from bills.models import Bill, Participant, Item

@login_required
def dashboard(request):
    """
    A dashboard view that displays:
    - Monthly, weekly, yearly spending (line charts)
    - Top items by spending (pie chart)
    - Category/Store spending (bar or donut chart, as an example)
    - Some summary cards for quick stats
    """

    # -----------------------------
    # 1. GET & AGGREGATE THE DATA
    # -----------------------------

    # Monthly Spending
    monthly_spending = (
        Bill.objects
        .annotate(period=TruncMonth('date'))
        .values('period')
        .annotate(total=Sum('total_amount'))
        .order_by('period')
    )

    # Weekly Spending
    weekly_spending = (
        Bill.objects
        .annotate(period=TruncWeek('date'))
        .values('period')
        .annotate(total=Sum('total_amount'))
        .order_by('period')
    )

    # Yearly Spending
    yearly_spending = (
        Bill.objects
        .annotate(period=TruncYear('date'))
        .values('period')
        .annotate(total=Sum('total_amount'))
        .order_by('period')
    )

    # Item-level spending (Top 10)
    item_spending = (
        Item.objects
        .values('name')
        .annotate(total=Sum('price'))
        .order_by('-total')[:10]
    )

    # Category-level or store-level spending (example).
    # Adjust field names to match your models (e.g., "name" or "store_name").
    # If you don’t have categories, you can skip or adapt this part.
    category_spending = (
        Item.objects
        .values('name')  # or 'store_name'
        .annotate(total=Sum('price'))
        .order_by('-total')[:5]  # top 5 categories or stores
    )

    # Calculate totals
    total_spent_monthly = monthly_spending.aggregate(total=Sum('total'))['total'] or 0
    total_spent_weekly = weekly_spending.aggregate(total=Sum('total'))['total'] or 0
    total_spent_yearly = yearly_spending.aggregate(total=Sum('total'))['total'] or 0

    # For the "top spent item" or "most expensive item"
    top_spent_item_monthly = item_spending.first()  # Just reusing the same top 10 list for demo
    top_spent_item_weekly = item_spending.first()   # Typically you'd filter by date range
    top_spent_item_yearly = item_spending.first()

    # ---------------------------------------
    # 2. CREATE PLOTLY CHARTS (as JSON)
    # ---------------------------------------

    # A. Monthly line chart
    monthly_series_plot = json.dumps({
        'data': [
            go.Scatter(
                x=[entry['period'] for entry in monthly_spending],
                y=[float(entry['total']) for entry in monthly_spending],
                mode='lines+markers',
                line=dict(color='blue'),
                marker=dict(size=6)
            )
        ],
        'layout': go.Layout(
            title='Monthly Spending',
            xaxis={'title': 'Month'},
            yaxis={'title': 'Total ($)'},
            paper_bgcolor='rgba(0,0,0,0)',  # Transparent for a modern look
            plot_bgcolor='rgba(0,0,0,0)'
        )
    }, cls=PlotlyJSONEncoder)

    # B. Weekly line chart
    weekly_series_plot = json.dumps({
        'data': [
            go.Scatter(
                x=[entry['period'] for entry in weekly_spending],
                y=[float(entry['total']) for entry in weekly_spending],
                mode='lines+markers',
                line=dict(color='green'),
                marker=dict(size=6)
            )
        ],
        'layout': go.Layout(
            title='Weekly Spending',
            xaxis={'title': 'Week'},
            yaxis={'title': 'Total ($)'},
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
    }, cls=PlotlyJSONEncoder)

    # C. Yearly line chart
    yearly_series_plot = json.dumps({
        'data': [
            go.Scatter(
                x=[entry['period'] for entry in yearly_spending],
                y=[float(entry['total']) for entry in yearly_spending],
                mode='lines+markers',
                line=dict(color='purple'),
                marker=dict(size=6)
            )
        ],
        'layout': go.Layout(
            title='Yearly Spending',
            xaxis={'title': 'Year'},
            yaxis={'title': 'Total ($)'},
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
    }, cls=PlotlyJSONEncoder)

    # D. Top 10 Items (Pie Chart)
    item_pie_plot = json.dumps({
        'data': [
            go.Pie(
                labels=[item['name'] for item in item_spending],
                values=[float(item['total']) for item in item_spending],
                hole=0.3,  # donut chart style
                textinfo='value+percent',
                marker=dict(line=dict(color='#000000', width=2))
            )
        ],
        'layout': go.Layout(
            title='Top 10 Items by Spending',
            paper_bgcolor='rgba(0,0,0,0)'
        )
    }, cls=PlotlyJSONEncoder)

    # E. Category/Store Spending (Bar or Donut)
    category_bar_plot = json.dumps({
        'data': [
            go.Bar(
                x=[cat['name'] for cat in category_spending],
                y=[float(cat['total']) for cat in category_spending],
                marker=dict(color='rgba(222,45,38,0.8)')
            )
        ],
        'layout': go.Layout(
            title='Top 5 Categories (or Stores)',
            xaxis={'title': 'Category'},
            yaxis={'title': 'Total ($)'},
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
    }, cls=PlotlyJSONEncoder)

    # ---------------------------------------
    # 3. PASS EVERYTHING TO THE TEMPLATE
    # ---------------------------------------
    context = {
        'monthly_series_plot': monthly_series_plot,
        'weekly_series_plot': weekly_series_plot,
        'yearly_series_plot': yearly_series_plot,
        'item_pie_plot': item_pie_plot,
        'category_bar_plot': category_bar_plot,
        
        'total_spent_monthly': total_spent_monthly,
        'total_spent_weekly': total_spent_weekly,
        'total_spent_yearly': total_spent_yearly,
        
        'top_spent_item_monthly': top_spent_item_monthly,
        'top_spent_item_weekly': top_spent_item_weekly,
        'top_spent_item_yearly': top_spent_item_yearly
    }

    return render(request, 'dashboards/dashboard.html', context)

@login_required
def home(request):
    user = request.user
    # User-specific balances
    total_owed_by_user = (
        Participant.objects.filter(name=user.username)
        .aggregate(total=Sum('amount_owed'))['total'] or 0
    )
    
    total_owed_to_user = (
        Participant.objects.filter(name=user.username)
        .aggregate(total=Sum('amount_paid'))['total'] or 0
    )

    # Person balances
    person_balances = (
        Participant.objects
        .values('name')
        .annotate(
            total_paid=Sum('amount_paid'),
            total_owed=Sum('amount_owed')
        )
    )

    # Calculate total spent by the user
    total_spent = (
        Bill.objects.filter(participants__name=user.username)
        .aggregate(total=Sum('total_amount'))['total'] or 0
    )

    context = {
        'total_spent': total_spent,
        'total_owed_by_user': total_owed_by_user,
        'total_owed_to_user': total_owed_to_user,
        'person_balances': person_balances,
    }

    return render(request, 'dashboards/home.html', context)