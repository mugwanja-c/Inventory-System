from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

class Category(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


phone_validator = RegexValidator(
    regex=r'^(07|01)\d{8}$',
    message="Phone number must be 10 digits and start with 07 or 01."
)

class Supplier(models.Model):
    name = models.CharField(max_length=255)
    contact = models.CharField(max_length=10, validators=[phone_validator])
    email = models.EmailField()

    def __str__(self):
        return f"{self.name} ({self.contact}, {self.email})"

class County(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Location(models.Model):
    county = models.ForeignKey(County,on_delete=models.PROTECT,null=True,blank=True)
    branch_name = models.CharField(max_length=150,null=True,blank=True    )
    description = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        unique_together = ('county', 'branch_name')

    def __str__(self):
        if self.county and self.branch_name:
            return f"{self.county.name} - {self.branch_name}"
        return "Incomplete Location"

class Item(models.Model):
    name = models.CharField(max_length=255, unique=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    barcode = models.CharField(max_length=20, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.barcode:
            import random
            self.barcode = str(random.randint(1000000000, 9999999999))
        super().save(*args, **kwargs)

    def stock_status(self):
        if self.quantity == 0:
            return "Out of Stock"
        elif self.quantity < 10:
            return "Low Stock"
        else:
            return "In Stock"

    def __str__(self):
       category = self.category.name if self.category else "No Category"
       return f"{self.name} ({category})"

class Order(models.Model):
    STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("Assigned", "Assigned"),
        ("Delivered", "Delivered"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    delivery_location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="Pending")
    phone = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=True)

    def __str__(self):
        return f"Order #{self.id} by {self.user.username} - {self.item.name} x{self.quantity}"

class Announcement(models.Model):
    title = models.CharField(max_length=200)
    message = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
 
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=50) # Admin, Staff, Customer
    phone = models.CharField(max_length=10, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.action} at {self.timestamp}"
