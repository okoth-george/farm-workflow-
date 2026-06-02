from django.urls import include, path
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('plan/new/', views.new_plan, name='new_plan'),
    path('plan/<int:pk>/', views.plan_detail, name='plan_detail'),
    path('plan/<int:pk>/status/', views.plan_status, name='plan_status'),
    path('plan/<int:pk>/delete/', views.delete_plan, name='delete_plan'),
    path('plans/', views.all_plans, name='all_plans'),
    path('auth/callback/', views.auth_callback, name='auth_callback'),
]
