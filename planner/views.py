from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import FarmPlan
from .ai_engine import generate_farm_plan
import json


def index(request):
    recent_plans = FarmPlan.objects.order_by('-created_at')[:6]
    return render(request, 'planner/index.html', {'recent_plans': recent_plans})


def new_plan(request):
    if request.method == 'POST':
        farm_data = {
            'farmer_name': request.POST.get('farmer_name'),
            'location': request.POST.get('location'),
            'land_size': request.POST.get('land_size'),
            'crop': request.POST.get('crop'),
            'soil_type': request.POST.get('soil_type'),
            'season': request.POST.get('season'),
            'budget': request.POST.get('budget'),
            'additional_notes': request.POST.get('additional_notes', ''),
        }

        # Generate AI plan
        ai_result = generate_farm_plan(farm_data)

        # Save to DB
        plan = FarmPlan.objects.create(
            farmer_name=farm_data['farmer_name'],
            location=farm_data['location'],
            land_size=farm_data['land_size'],
            crop=farm_data['crop'],
            soil_type=farm_data['soil_type'],
            season=farm_data['season'],
            budget=farm_data['budget'],
            additional_notes=farm_data['additional_notes'],
            planting_schedule=json.dumps(ai_result.get('planting_schedule', [])),
            input_requirements=json.dumps(ai_result.get('input_requirements', [])),
            weather_risks=json.dumps(ai_result.get('weather_risks', [])),
            purchase_orders=json.dumps(ai_result.get('purchase_orders', [])),
            ai_summary=ai_result.get('ai_summary', ''),
        )
        return redirect('plan_detail', pk=plan.pk)

    return render(request, 'planner/new_plan.html', {
        'crop_choices': FarmPlan.CROP_CHOICES,
        'soil_choices': FarmPlan.SOIL_CHOICES,
        'season_choices': FarmPlan.SEASON_CHOICES,
    })


def plan_detail(request, pk):
    plan = get_object_or_404(FarmPlan, pk=pk)
    
    planting_schedule = json.loads(plan.planting_schedule) if plan.planting_schedule else []
    input_requirements = json.loads(plan.input_requirements) if plan.input_requirements else []
    weather_risks = json.loads(plan.weather_risks) if plan.weather_risks else []
    purchase_orders = json.loads(plan.purchase_orders) if plan.purchase_orders else []

    total_cost = sum(item.get('cost_kes', 0) for item in planting_schedule)
    total_inputs = sum(item.get('cost_kes', 0) for item in input_requirements)

    return render(request, 'planner/plan_detail.html', {
        'plan': plan,
        'planting_schedule': planting_schedule,
        'input_requirements': input_requirements,
        'weather_risks': weather_risks,
        'purchase_orders': purchase_orders,
        'total_cost': total_cost,
        'total_inputs': total_inputs,
    })


def all_plans(request):
    plans = FarmPlan.objects.order_by('-created_at')
    return render(request, 'planner/all_plans.html', {'plans': plans})
