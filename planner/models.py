from django.db import models

class UserProfile(models.Model):
    external_id = models.IntegerField(unique=True) 
    username = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.username

class FarmPlan(models.Model):
    CROP_CHOICES = [
        ('maize', 'Maize'),
        ('beans', 'Beans'),
        ('tomatoes', 'Tomatoes'),
        ('potatoes', 'Potatoes'),
        ('wheat', 'Wheat'),
        ('sorghum', 'Sorghum'),
        ('cassava', 'Cassava'),
        ('sweet_potato', 'Sweet Potato'),
        ('kale', 'Kale (Sukuma Wiki)'),
        ('cabbage', 'Cabbage'),
    ]

    SOIL_CHOICES = [
        ('loam', 'Loam'),
        ('clay', 'Clay'),
        ('sandy', 'Sandy'),
        ('silty', 'Silty'),
        ('peaty', 'Peaty'),
    ]

    SEASON_CHOICES = [
        ('long_rains', 'Long Rains (Mar–May)'),
        ('short_rains', 'Short Rains (Oct–Dec)'),
        ('dry', 'Dry Season (Irrigation)'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('complete', 'Complete'),
        ('error', 'Error'),
    ]
    userprofile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='farm_plans')    
    farmer_name = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    land_size = models.DecimalField(max_digits=6, decimal_places=2)
    crop = models.CharField(max_length=50, choices=CROP_CHOICES)
    soil_type = models.CharField(max_length=50, choices=SOIL_CHOICES)
    season = models.CharField(max_length=50, choices=SEASON_CHOICES)
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    additional_notes = models.TextField(blank=True)

    planting_schedule = models.TextField(blank=True)
    input_requirements = models.TextField(blank=True)
    weather_risks = models.TextField(blank=True)
    purchase_orders = models.TextField(blank=True)
    ai_summary = models.TextField(blank=True)

     # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.farmer_name} - {self.crop} ({self.location})"
