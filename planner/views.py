from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_GET, require_POST
from .models import FarmPlan
from .ai_engine import generate_farm_plan
import json
import threading


def _run_ai_in_background(plan_id, farm_data):
    try:
        FarmPlan.objects.filter(pk=plan_id).update(status='processing')
        ai_result = generate_farm_plan(farm_data)
        FarmPlan.objects.filter(pk=plan_id).update(
            planting_schedule=json.dumps(ai_result.get('planting_schedule', [])),
            input_requirements=json.dumps(ai_result.get('input_requirements', [])),
            weather_risks=json.dumps(ai_result.get('weather_risks', [])),
            purchase_orders=json.dumps(ai_result.get('purchase_orders', [])),
            ai_summary=ai_result.get('ai_summary', ''),
            status='complete',
        )
    except Exception as e:
        print(f"[FarmFlow] Background AI error: {e}")
        FarmPlan.objects.filter(pk=plan_id).update(status='error')


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

        plan = FarmPlan.objects.create(
            farmer_name=farm_data['farmer_name'],
            location=farm_data['location'],
            land_size=farm_data['land_size'],
            crop=farm_data['crop'],
            soil_type=farm_data['soil_type'],
            season=farm_data['season'],
            budget=farm_data['budget'],
            additional_notes=farm_data['additional_notes'],
            status='pending',
        )

        thread = threading.Thread(
            target=_run_ai_in_background,
            args=(plan.pk, farm_data),
            daemon=True
        )
        thread.start()

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


@require_POST
def delete_plan(request, pk):
    plan = get_object_or_404(FarmPlan, pk=pk)
    plan.delete()
    return redirect('all_plans')


@require_GET
def plan_status(request, pk):
    plan = get_object_or_404(FarmPlan, pk=pk)

    if plan.status == 'complete':
        planting_schedule = json.loads(plan.planting_schedule) if plan.planting_schedule else []
        input_requirements = json.loads(plan.input_requirements) if plan.input_requirements else []
        weather_risks = json.loads(plan.weather_risks) if plan.weather_risks else []
        purchase_orders = json.loads(plan.purchase_orders) if plan.purchase_orders else []
        total_cost = sum(item.get('cost_kes', 0) for item in planting_schedule)
        total_inputs = sum(item.get('cost_kes', 0) for item in input_requirements)

        response = render(request, 'planner/partials/plan_results.html', {
            'plan': plan,
            'planting_schedule': planting_schedule,
            'input_requirements': input_requirements,
            'weather_risks': weather_risks,
            'purchase_orders': purchase_orders,
            'total_cost': total_cost,
            'total_inputs': total_inputs,
        })
        response['HX-Trigger'] = 'planComplete'
        return response

    elif plan.status == 'error':
        response = HttpResponse('''
            <div style="text-align:center;padding:3rem;color:#C0392B;">
                <div style="font-size:2.5rem;margin-bottom:1rem;">⚠️</div>
                <h3>AI generation failed</h3>
                <p style="color:#888;margin-top:.5rem;">Please check your API key and try again.</p>
                <a href="/plan/new/" style="display:inline-block;margin-top:1rem;padding:.6rem 1.5rem;
                   background:#3D6B35;color:#fff;border-radius:8px;text-decoration:none;">Try Again</a>
            </div>
        ''')
        response['HX-Trigger'] = 'planComplete'
        return response

    else:
        return HttpResponse(f'''
            <div hx-get="/plan/{pk}/status/"
                 hx-trigger="every 3s"
                 hx-swap="outerHTML"
                 style="text-align:center;padding:3rem;">
                <div class="spinner"></div>
                <p style="color:#6B8C5A;font-size:1rem;margin-top:1rem;">
                    🌱 AI is analysing your farm data...
                </p>
                <p style="color:#aaa;font-size:.85rem;margin-top:.3rem;">This usually takes 10–20 seconds</p>
            </div>
        ''')


def all_plans(request):
    plans = FarmPlan.objects.order_by('-created_at')
    return render(request, 'planner/all_plans.html', {'plans': plans})