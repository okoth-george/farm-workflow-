from django.db import models


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

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.farmer_name} - {self.crop} ({self.location})"
