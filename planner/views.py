import json
import threading
import requests
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from .models import FarmPlan, UserProfile
from .ai_engine import generate_farm_plan
import os  # 👈 Make sure os is imported at the top of your file
from django.core.exceptions import ImproperlyConfigured


# 🛡️ SECURITY DECORATOR
def express_login_required(view_func):
    """
    Ensures a user has a valid active session from the Express gateway
    before letting them view or interact with any planner page.
    """
    def _wrapped_view(request, *args, **kwargs):
        if 'user_id' not in request.session:
            # Not authenticated? Kick them back out to your React UI gateway
            return redirect('http://localhost:5173/login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


@require_http_methods(["GET"])
def auth_callback(request):
    """
    Production-Ready Auth Callback.
    Bypasses hardcoded URLs by fetching the Identity Provider address
    from system environment variables.
    """
    exchange_code = request.GET.get('code')
    
    if not exchange_code:
        return JsonResponse({'error': 'Security handshake failed: Authorization code missing.'}, status=400)
    
    # DYNAMIC CONFIGURATION: Fetch the Express API root from environment variables
    express_api_base = os.environ.get('EXPRESS_API_BASE_URL')
    
    if not express_api_base:
        print("[FarmFlow Critical Error] EXPRESS_API_BASE_URL environment variable is missing!")
        return JsonResponse({'error': 'Server configuration error.'}, status=500)
        
    try:
        # Construct the exchange endpoint dynamically without trailing slash worries .
        express_exchange_url = f"{express_api_base.rstrip('/')}/api/users/exchange-code"
        
        #  SERVER-TO-SERVER REDEMPTION over HTTPS (Production) or HTTP (Local)
        response = requests.post(
            express_exchange_url, 
            json={'code': exchange_code},
            timeout=7  # Slightly higher timeout for cross-server production networks
        )
        
        if response.status_code != 200:
            return JsonResponse({'error': 'Authorization code was rejected or expired.'}, status=401)
            
        data = response.json()
        node_user = data.get('user', {})
        node_id = node_user.get('id')
        node_username = node_user.get('username')
        
        if not node_id or not node_username:
            return JsonResponse({'error': 'Invalid payload data structure from Identity Provider.'}, status=400)
        
        # 🔄 JUST-IN-TIME PROVISIONING
        user_profile, created = UserProfile.objects.get_or_create(
            external_id=node_id,
            defaults={'username': node_username}
        )
        
        if not created and user_profile.username != node_username:
            user_profile.username = node_username
            user_profile.save()
            
        # 🔑 STATEFUL SESSION LOCKING
        request.session['user_id'] = user_profile.id
        request.session['username'] = user_profile.username
        
        return redirect('/')
        
    except requests.exceptions.RequestException as e:
        print(f"[FarmFlow Critical] Cross-server auth line connection failed: {e}")
        return JsonResponse({'error': 'Authentication microservices temporarily out of sync.'}, status=503)
    

def _run_ai_in_background(plan_id, farm_data):
    """
    3. Application State and Core Business Logic
    Runs asynchronous Gemini instructions inside an isolated background daemon worker thread.
    """
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


@express_login_required
def index(request):
    # 🔒 Filtered: Only show the 6 most recent plans belonging to THIS specific profile
    recent_plans = FarmPlan.objects.filter(
        userprofile_id=request.session['user_id']
    ).order_by('-created_at')[:6]
    
    return render(request, 'planner/index.html', {
        'recent_plans': recent_plans,
        'username': request.session.get('username')
    })


@express_login_required
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

        current_user = UserProfile.objects.get(id=request.session['user_id'])

        # 🔒 Linked: Explicitly tie this plan to the active session owner
        plan = FarmPlan.objects.create(
            userprofile=current_user,
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


@express_login_required
def plan_detail(request, pk):
    # 🔒 Secured: Multi-tenant scope guard check
    plan = get_object_or_404(FarmPlan, pk=pk, userprofile_id=request.session['user_id'])

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
@express_login_required
def delete_plan(request, pk):
    plan = get_object_or_404(FarmPlan, pk=pk, userprofile_id=request.session['user_id'])
    plan.delete()
    return redirect('all_plans')


@require_GET
@express_login_required
def plan_status(request, pk):
    """
    5. UI Rendering and Frontend Delivery (HTMX Engine)
    Serves asynchronous partial chunks over the line directly to HTMX swap listeners.
    """
    plan = get_object_or_404(FarmPlan, pk=pk, userprofile_id=request.session['user_id'])

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


@express_login_required
def all_plans(request):
    plans = FarmPlan.objects.filter(userprofile_id=request.session['user_id']).order_by('-created_at')
    return render(request, 'planner/all_plans.html', {'plans': plans})

@require_GET
def health_check(request):
    """
    Health check endpoint for monitoring and uptime verification.
    Returns a simple JSON response indicating the service is operational.
    """
    return JsonResponse({'status': 'ok', 'message': 'FarmFlow Planner service is running.'})