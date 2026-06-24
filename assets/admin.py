from django.contrib import admin

# Register your models here.
from .models import Category, Item, Supplier, Location, County

admin.site.register(Category)
admin.site.register(Supplier)
admin.site.register(Location)
admin.site.register(Item)
admin.site.register(County)
