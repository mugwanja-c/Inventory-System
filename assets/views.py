from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from .models import (
    Category, Supplier, Location, County, Item,
    Order, Announcement, UserProfile
)

from .forms import OrderForm

from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from datetime import timedelta
import json, re
from dateutil.relativedelta import relativedelta


def landing_page(request):
    return render(request, 'assets/landing.html')

def about(request):
    return render(request, 'assets/about.html')


def contact(request):
    if request.method == "POST":
        messages.success(request, "Message sent successfully!")
        return redirect('landing')
    return render(request, 'assets/contact.html')

@login_required
def dashboard(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    now = timezone.now()

    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_today = start_of_today + timedelta(days=1)

    todays_orders = Order.objects.filter(
        created_at__gte=start_of_today,
        created_at__lt=end_of_today
    ).select_related('user', 'item', 'supplier').order_by('-created_at')

  
    all_orders = Order.objects.select_related(
        'user', 'item', 'supplier'
    ).order_by('-created_at')[:10]

    total_orders = Order.objects.count()

    total_revenue = Order.objects.aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    daily_revenue = Order.objects.filter(
        created_at__gte=start_of_today,
        created_at__lt=end_of_today
    ).aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    
    start_of_month = now.replace(day=1)

    monthly_revenue = Order.objects.filter(
        created_at__gte=start_of_month
    ).aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    
    start_of_last_month = (start_of_month - timedelta(days=1)).replace(day=1)

    previous_month_revenue = Order.objects.filter(
        created_at__gte=start_of_last_month,
        created_at__lt=start_of_month
    ).aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    
    LOW_STOCK_THRESHOLD = 10
    low_stock_items = Item.objects.filter(quantity__lte=LOW_STOCK_THRESHOLD)

    
    top_category = (
        Item.objects
        .values('category__name')
        .annotate(total=Count('id'))
        .order_by('-total')
        .first()
    )

    context = {
        "todays_orders": todays_orders,
        "todays_orders_count": todays_orders.count(),

        "all_orders": all_orders,

        "categories_count": Category.objects.count(),
        "items_count": Item.objects.count(),
        "suppliers_count": Supplier.objects.count(),
        "locations_count": Location.objects.count(),

        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "daily_revenue": daily_revenue,
        "monthly_revenue": monthly_revenue,

        "low_stock_items": low_stock_items,
        "low_stock_count": low_stock_items.count(),

        "top_category": top_category,

    }

    return render(request, "assets/dashboard.html", context)

@login_required
def user_dashboard(request):
    if request.user.is_staff:
        return redirect('dashboard')

    items = Item.objects.select_related('category', 'location', 'supplier')
    locations = Location.objects.select_related('county')
    suppliers = Supplier.objects.all()
    announcements = Announcement.objects.order_by('-created_at')[:5]
    latest_announcement = Announcement.objects.order_by('-created_at').first()

    message = None

    if request.method == "POST":
        item_id = request.POST.get("item", "").strip()
        quantity = request.POST.get("quantity", "").strip()
        location_id = request.POST.get("location", "").strip()
        supplier_id = request.POST.get("supplier", "").strip()
        phone = request.POST.get("phone", "").strip()

        phone_pattern = r"^(?:\+254|0)[7]\d{8}$"

  
        if not item_id or not quantity or not location_id or not supplier_id:
            message = "All fields are required."
        elif not quantity.isdigit():
            message = "Quantity must be a valid number."
        elif phone and not re.match(phone_pattern, phone):
            message = "Enter a valid Kenyan phone number (07XXXXXXXX or +2547XXXXXXXX)."
        else:
            try:
                quantity = int(quantity)

                item = get_object_or_404(Item, id=item_id)
                location = get_object_or_404(Location, id=location_id)
                supplier = get_object_or_404(Supplier, id=supplier_id)

            
                if quantity <= 0:
                    message = "Quantity must be greater than 0."

                elif quantity > item.quantity:
                    message = "Not enough stock available."

                else:
                    item.quantity -= quantity
                    item.save()

                    Order.objects.create(
                        user=request.user,
                        item=item,
                        quantity=quantity,
                        delivery_location=location,
                        supplier=supplier,
                        phone=phone,
                        status="Pending",
                        total_amount=item.price * quantity
                    )

                    message = "Order placed successfully!"

            except (ValueError, TypeError):
                message = "Invalid quantity entered."

    user_orders = Order.objects.filter(user=request.user).select_related(
        'item', 'supplier'
    ).order_by('-created_at')

    context = {
        "items": items,
        "locations": locations,
        "suppliers": suppliers,
        "user_orders": user_orders,
        "announcements": announcements,
        "latest_announcement": latest_announcement,
        "message": message
    }

    return render(request, "assets/user_dashboard.html", context)

import re
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

@login_required
def place_order(request):

    if not request.user.first_name or not request.user.last_name:
        return redirect('complete_profile')

    items = Item.objects.all()
    locations = Location.objects.select_related('county').all()
    suppliers = Supplier.objects.all()

    message = None

    
    user_phone = None
    try:
        user_phone = request.user.userprofile.phone
    except:
        user_phone = None

    phone_pattern = r"^(?:\+254|0)[7]\d{8}$"

    if request.method == "POST":

        item_id = request.POST.get("item", "").strip()
        quantity = request.POST.get("quantity", "").strip()
        location_id = request.POST.get("location", "").strip()
        supplier_id = request.POST.get("supplier", "").strip()

        phone = user_phone

        # Basic empty check
        if not item_id or not quantity or not location_id or not supplier_id:
            message = "All fields are required."
            return render(request, "assets/user_dashboard.html", locals())

  
        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            message = "Quantity must be a valid number."
            return render(request, "assets/user_dashboard.html", locals())

    
        if quantity <= 0:
            message = "Quantity must be greater than 0."
            return render(request, "assets/user_dashboard.html", locals())


        if not phone or not re.match(phone_pattern, phone):
            message = "Invalid registered phone number."
            return render(request, "assets/user_dashboard.html", locals())

        try:
            item = Item.objects.get(id=item_id)
            location = Location.objects.get(id=location_id)
            supplier = Supplier.objects.get(id=supplier_id)

            if quantity > item.quantity:
                message = "Not enough stock available."
                return render(request, "assets/user_dashboard.html", locals())

   
            item.quantity -= quantity
            item.save()

       
            Order.objects.create(
                user=request.user,
                item=item,
                quantity=quantity,
                delivery_location=location,
                supplier=supplier,
                phone=phone,
                status="Pending",
                total_amount=item.price * quantity
            )

            message = "Order placed successfully!"

        except Item.DoesNotExist:
            message = "Item not found."
        except Location.DoesNotExist:
            message = "Location not found."
        except Supplier.DoesNotExist:
            message = "Supplier not found."
        except Exception:
            message = "Something went wrong."

    user_orders = Order.objects.filter(user=request.user).select_related(
        'item', 'supplier'
    )

    return render(request, "assets/user_dashboard.html", {
        "items": items,
        "locations": locations,
        "suppliers": suppliers,
        "user_orders": user_orders,
        "message": message,
        "phone": user_phone
    })

@login_required
def all_orders(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    orders = Order.objects.all().select_related('user', 'item', 'supplier').order_by('-created_at')

    return render(request, 'assets/orders.html', {
        'orders': orders
    })

@login_required
def update_order_status(request, order_id):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    order = get_object_or_404(Order, id=order_id)

    STATUS_FLOW = {
        "pending": ["assigned"],
        "assigned": ["delivered"],
        "delivered": []
    }

    if request.method == "POST":
        new_status = request.POST.get("status")

        current_status = order.status

        allowed_next_states = STATUS_FLOW.get(current_status, [])

        if new_status in allowed_next_states:
            order.status = new_status
            order.save()

    return redirect('dashboard')


@login_required
def profile(request):
    profile, created = request.user.profile, False 

    if request.method == "POST":
        email = (request.POST.get("email") or "").strip()
        phone = (request.POST.get("phone") or "").strip().replace(" ", "")

        phone_pattern = r"^(?:\+2547\d{8}|07\d{8}|2547\d{8}|01\d{8})$"

        if not email:
            messages.error(request, "Email is required.")
            return redirect("profile")

        if not re.fullmatch(phone_pattern, phone):
            messages.error(request, "Enter a valid phone number (07XXXXXXXX or +2547XXXXXXXX or 01XXXXXXXX).")
            return redirect("profile")

        request.user.email = email
        request.user.save()

        profile.phone = phone
        profile.save()

        messages.success(request, "Profile updated successfully!")
        return redirect("profile")

    return render(request, "accounts/profile.html", {
        "profile": profile,
        "user": request.user
    })


def login_page(request):

    if "login_attempts" not in request.session:
        request.session["login_attempts"] = 0

    if request.method == 'POST':

        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        remember = request.POST.get('remember_me')


        if not username or not password:
            return render(request, 'assets/login.html', {
                'error': 'All fields are required'
            })

        # STEP 1: Try authentication FIRST
        user = authenticate(request, username=username, password=password)

        # STEP 2: If login is successful
        if user:
            request.session["login_attempts"] = 0
            login(request, user)

            # Remember me logic
            if not remember:
                request.session.set_expiry(0)
            else:
                request.session.set_expiry(None)

            # Role-based redirect
            profile = getattr(user, "userprofile", None)

            if user.is_staff or (profile and profile.role.lower() == "admin"):
                return redirect('dashboard')
            else:
                return redirect('user_dashboard')

        # STEP 3: If login fails, increase attempts
        request.session["login_attempts"] = request.session.get("login_attempts", 0) + 1

        # STEP 4: Lock after 3 failed attempts
        if request.session["login_attempts"] >= 3:
            return render(request, 'assets/login.html', {
                'error': 'Too many failed attempts. Please try again later.'
            })

        # STEP 5: Normal failed login message
        return render(request, 'assets/login.html', {
            'error': f'Invalid credentials ({request.session["login_attempts"]}/3 attempts)'
        })

    return render(request, 'assets/login.html')

def logout_page(request):
    logout(request)
    return redirect('landing')


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)

        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password changed successfully!")
            return redirect('dashboard')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, 'assets/change_password.html', {'form': form})


@login_required
def complete_profile(request):
  
    if request.user.first_name and request.user.last_name:
        return redirect('user_dashboard')

    if request.method == "POST":
        first_name = (request.POST.get("first_name") or "").strip()
        last_name = (request.POST.get("last_name") or "").strip()

        if not first_name or not last_name:
            messages.error(request, "Both first name and last name are required.")
            return render(request, "assets/complete_profile.html")

        request.user.first_name = first_name
        request.user.last_name = last_name
        request.user.save()

        messages.success(request, "Profile completed successfully!")
        return redirect('user_dashboard')

    return render(request, "assets/complete_profile.html")


def register(request):
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        email = (request.POST.get("email") or "").strip()
        phone = (request.POST.get("phone") or "").strip().replace(" ", "")
        password = request.POST.get("password") or ""
        confirm_password = request.POST.get("confirm_password") or ""

        phone_pattern = r"^(?:\+2547\d{8}|07\d{8}|2547\d{8}|01\d{8})$"

  
        if not all([username, email, phone, password, confirm_password]):
            messages.error(request, "All fields are required")
            return redirect("register")

        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Invalid email format")
            return redirect("register")

        if not re.fullmatch(phone_pattern, phone):
            messages.error(request, "Enter a valid Kenyan phone number")
            return redirect("register")
        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long")
            return redirect("register")
        
        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect("register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists")
            return redirect("register")

        User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        messages.success(request, "Account created successfully. Please login.")
        return redirect("login")

    return render(request, "assets/register.html")

@login_required
def categories_page(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    error = None

    if request.method == "POST":
        name = request.POST.get("name", "").strip()

        if name:
            exists = Category.objects.filter(name__iexact=name).exists()

            if exists:
                error = "This category already exists."

            else:
                Category.objects.create(name=name)
                return redirect('categories')

    categories = Category.objects.all()

    return render(request, 'assets/categories.html', {
        'categories': categories,
        'error': error
    })

@login_required
def edit_category(request, pk):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    category = get_object_or_404(Category, pk=pk)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if name:
            category.name = name
            category.save()
            return redirect('categories')

    return render(request, 'assets/edit_category.html', {'category': category})


@login_required
def delete_category(request, pk):
    if request.user.is_staff:
        category = get_object_or_404(Category, pk=pk)
        category.delete()
    return redirect('categories')


@login_required
def suppliers_page(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    error = None

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        contact = request.POST.get('contact', "").strip()
        email = request.POST.get('email', "").strip().lower()

        if name and contact and email:
            exists = Supplier.objects.filter(
                name__iexact=name,
                email=email
            ).exists()

            if exists:
                error = "This supplier already exists."

            else:
                Supplier.objects.create(
                    name=name,
                    contact=contact,
                    email=email
                )
                return redirect('suppliers')

    suppliers = Supplier.objects.all()

    return render(request, 'assets/suppliers.html', {
        'suppliers': suppliers,
        'error': error
    })


@login_required
def edit_supplier(request, pk):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    supplier = get_object_or_404(Supplier, pk=pk)

    if request.method == "POST":
        name = request.POST.get("name").strip()
        contact = request.POST.get("contact").strip()
        email = request.POST.get("email").strip()

      
        if not re.match(r'^(\+254|254|0)(7|1)\d{8}$', contact):
            messages.error(request, "Phone number must be 10 digits and start with 07 or +2547 or 01.")
            return render(request, 'assets/edit_supplier.html', {'supplier': supplier})

   
        supplier.name = name
        supplier.contact = contact
        supplier.email = email
        supplier.save()

        messages.success(request, "Supplier updated successfully.")
        return redirect('suppliers')

    return render(request, 'assets/edit_supplier.html', {'supplier': supplier})


@login_required
def delete_supplier(request, pk):
    if request.user.is_staff:
        supplier = get_object_or_404(Supplier, pk=pk)
        supplier.delete()
    return redirect('suppliers')


@login_required
def items_page(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    if request.method == "POST":
        name = request.POST.get("name")
        barcode = request.POST.get("barcode")
        category_id = request.POST.get("category")
        location_id = request.POST.get("location")
        supplier_id = request.POST.get("supplier")
        quantity = int(request.POST.get("quantity", 0))
        price = float(request.POST.get("price", 0))

        category = get_object_or_404(Category, id=category_id)
        location = get_object_or_404(Location, id=location_id)
        supplier = get_object_or_404(Supplier, id=supplier_id)


        if Item.objects.filter(name__iexact=name).exists():
            return render(request, 'assets/items.html', {
                'items': Item.objects.select_related('category', 'location', 'supplier'),
                'categories': Category.objects.all(),
                'suppliers': Supplier.objects.all(),
                'locations': Location.objects.all(),
                'error': "Item already exists. Please use the edit/update option."
            })


        Item.objects.create(
            name=name,
            barcode=barcode,
            category=category,
            location=location,
            supplier=supplier,
            quantity=quantity,
            price=price
        )

        return redirect('items')

    items = Item.objects.select_related('category', 'location', 'supplier')

    return render(request, 'assets/items.html', {
        'items': items,
        'categories': Category.objects.all(),
        'suppliers': Supplier.objects.all(),
        'locations': Location.objects.all()
    })

@login_required
def edit_item(request, pk):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    item = get_object_or_404(Item, pk=pk)

    if request.method == "POST":
        name = request.POST.get("name")
        barcode = request.POST.get("barcode")
        quantity = request.POST.get("quantity")
        price = request.POST.get("price")

        category = get_object_or_404(Category, id=request.POST.get("category"))
        location = get_object_or_404(Location, id=request.POST.get("location"))
        supplier = get_object_or_404(Supplier, id=request.POST.get("supplier"))

        if Item.objects.filter(name=name).exclude(pk=item.pk).exists():
            return render(request, 'assets/edit_item.html', {
                'item': item,
                'categories': Category.objects.all(),
                'suppliers': Supplier.objects.all(),
                'locations': Location.objects.all(),
                'error': "Item with this name already exists. Please use a different name."
            })

        
        item.name = name
        item.barcode = barcode
        item.quantity = quantity
        item.price = price
        item.category = category
        item.location = location
        item.supplier = supplier

        item.save()
        return redirect('items')

    return render(request, 'assets/edit_item.html', {
        'item': item,
        'categories': Category.objects.all(),
        'suppliers': Supplier.objects.all(),
        'locations': Location.objects.all()
    })


@login_required
def delete_item(request, pk):
    if request.user.is_staff:
        item = get_object_or_404(Item, pk=pk)
        item.delete()
    return redirect('items')



def seed_counties():
    counties_list = [
        "Nairobi","Kiambu","Mombasa","Kisumu","Nakuru",
        "Uasin Gishu","Machakos","Meru","Kakamega","Nyeri","Garissa",
        "Bungoma","Busia","Embu","Kitui","Thika","Eldoret","Naivasha",
        "Voi","Lamu","Isiolo","Marsabit","Wajir","Turkana","Samburu",
        "Tana River","West Pokot","Kilifi","Kitengela","Kisii",
        "Kericho","Murang'a","Nyandarua","Transzoia","Narok","Homa Bay",
        "Migori","Siaya","Kwale","Taita Taveta","Nyamira","Rongo",
        "Bomet","Makueni","Marakwet","Tharaka Nithi","Kajiado",
        "Mwingi","Moyale","Mandera"
    ]

    for c in counties_list:
        County.objects.get_or_create(name=c)


@login_required
def locations_page(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    seed_counties()

    counties = County.objects.all().order_by('name')
    locations = Location.objects.select_related('county').all().order_by('id')

    error = None

    if request.method == "POST":
        county_id = request.POST.get("county")
        branch_name = request.POST.get("branch_name", "").strip()

        if county_id and branch_name:
            county = get_object_or_404(County, id=county_id)

   
            if Location.objects.filter(
                county=county,
                branch_name__iexact=branch_name
            ).exists():
                error = "This location already exists."

            else:
                Location.objects.create(
                    county=county,
                    branch_name=branch_name
                )
                return redirect('locations')

    return render(request, 'assets/locations.html', {
        "counties": counties,
        "locations": locations,
        "error": error
    })

@login_required
def edit_location(request, pk):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    location = get_object_or_404(Location, pk=pk)

    if request.method == "POST":
        county_id = request.POST.get("county")
        branch_name = request.POST.get("branch_name", "").strip()
        description = request.POST.get("description", "")

        if county_id and branch_name:


            if Location.objects.filter(
                county_id=county_id,
                branch_name__iexact=branch_name
            ).exclude(pk=location.pk).exists():
                return render(request, 'assets/edit_location.html', {
                    'location': location,
                    'counties': County.objects.all(),
                    'error': "This location already exists."
                })

            location.county = get_object_or_404(County, id=county_id)
            location.branch_name = branch_name
            location.description = description
            location.save()

            return redirect('locations')

    return render(request, 'assets/edit_location.html', {
        'location': location,
        'counties': County.objects.all()
    })

@login_required
def delete_location(request, pk):
    if request.user.is_staff:
        location = get_object_or_404(Location, pk=pk)
        location.delete()
    return redirect('locations')


@login_required
def add_user(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip().capitalize()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        role = request.POST.get('role', 'Customer').capitalize()

        
        if User.objects.filter(username=username).exists():
            messages.error(request, "User already exists")
            return redirect('add_user')


        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Invalid email format")
            return redirect('add_user')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists")
            return redirect('add_user')

    
        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters")
            return redirect('add_user')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        
        if role.lower() == 'admin' and request.user.is_superuser:
            user.is_staff = True
            user.is_superuser = True

        user.save()

        UserProfile.objects.create(
            user=user,
            role=role,
        )

        messages.success(request, "User created successfully")
        return redirect('settings')

    return render(request, 'assets/add_user.html')


@login_required
def edit_user(request, user_id):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    user = get_object_or_404(User, id=user_id)
    message = None

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()

        if not username or not email:
            message = "Username and email are required."

        else:
            
            try:
                validate_email(email)
            
                if User.objects.exclude(id=user.id).filter(email=email).exists():
                    message = "Email already exists."

                else:
                    user.username = username
                    user.email = email
                    user.save()
                    return redirect('settings')

            except ValidationError:
                message = "Enter a valid email address."

    return render(request, "assets/edit_user.html", {
        "user": user,
        "message": message
    })

@login_required
def settings(request):
    users = User.objects.exclude(is_superuser=True)
    return render(request, 'assets/settings.html', {'users': users})


@login_required
def delete_user(request, user_id):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    user = get_object_or_404(User, id=user_id)

    if user == request.user:
        messages.error(request, "You cannot delete yourself.")
        return redirect('settings')

    if request.method == "POST":
        user.delete()
        messages.success(request, "User deleted successfully!")
        return redirect('settings')

    return redirect('settings')

@login_required
def activity_logs(request):
    today = timezone.now()

    daily_labels = []
    daily_user_counts = []
    daily_order_counts = []
    daily_item_counts = []
    daily_sales = []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        daily_labels.append(day.strftime("%a"))

        users = User.objects.filter(date_joined__date=day.date()).count()

        orders_qs = Order.objects.filter(created_at__date=day.date())
        orders_count = orders_qs.count()

        items = Item.objects.filter(created_at__date=day.date()).count()

        sales = orders_qs.aggregate(total=Sum('total_amount'))['total'] or 0

        daily_user_counts.append(users)
        daily_order_counts.append(orders_count)
        daily_item_counts.append(items)
        daily_sales.append(float(sales))


    monthly_labels = []
    monthly_user_counts = []
    monthly_order_counts = []
    monthly_item_counts = []
    monthly_sales = []

    for i in range(5, -1, -1):
        month = today.replace(day=1) - relativedelta(months=i)

        monthly_labels.append(month.strftime("%b"))

        users = User.objects.filter(
            date_joined__year=month.year,
            date_joined__month=month.month
        ).count()

        orders_qs = Order.objects.filter(
            created_at__year=month.year,
            created_at__month=month.month
        )

        items = Item.objects.filter(
            created_at__year=month.year,
            created_at__month=month.month
        ).count()

        sales = orders_qs.aggregate(total=Sum('total_amount'))['total'] or 0

        monthly_user_counts.append(users)
        monthly_order_counts.append(orders_qs.count())
        monthly_item_counts.append(items)
        monthly_sales.append(float(sales))

    low_stock_list = list(
        Item.objects.filter(quantity__lte=10).values('name', 'quantity')
    )

    return render(request, "assets/activity_logs.html", {
        "daily_labels": daily_labels,
        "daily_user_counts": daily_user_counts,
        "daily_order_counts": daily_order_counts,
        "daily_item_counts": daily_item_counts,
        "daily_sales": daily_sales,

        "monthly_labels": monthly_labels,
        "monthly_user_counts": monthly_user_counts,
        "monthly_order_counts": monthly_order_counts,
        "monthly_item_counts": monthly_item_counts,
        "monthly_sales": monthly_sales,

        "low_stock_list": low_stock_list,
    })

@login_required
def send_announcement(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    if request.method == "POST":
        title = request.POST.get("title")
        message = request.POST.get("message")

        Announcement.objects.create(
            title=title,
            message=message,
            created_by=request.user
        )

        messages.success(request, "Announcement sent successfully!")
        return redirect('settings')

    return render(request, "assets/send_announcement.html")

def user_announcement(request):
    announcement = Announcement.objects.all().order_by('-created_at')

    return render(request, "assets/user_announcement.html", {
        "announcement": announcement
    })


@login_required
def sales_insights(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    filter_type = request.GET.get('filter', 'day')
    today = timezone.now()

    if filter_type == 'week':
        start_date = today - timedelta(days=7)
        date_group = TruncWeek('created_at')

    elif filter_type == 'month':
        start_date = today - timedelta(days=30)
        date_group = TruncMonth('created_at')

    elif filter_type == 'all':
        start_date = None
        date_group = TruncDay('created_at')

    else:
        start_date = today - timedelta(days=1)
        date_group = TruncDay('created_at')

    orders = Order.objects.all()

    if start_date:
        orders = orders.filter(created_at__gte=start_date)

    sales_trend = (
        orders
        .annotate(period=date_group)
        .values('period')
        .annotate(total_sales=Sum('quantity'))
        .order_by('period')
    )

    sales_trend = list(sales_trend)

    for item in sales_trend:
        if item['period']:
            item['period'] = item['period'].strftime('%Y-%m-%d')

    best_selling = (
        orders
        .values('item__name')
        .annotate(total_sold=Sum('quantity'))
        .order_by('-total_sold')[:5]
    )

    low_performing = (
        orders
        .values('item__name')
        .annotate(total_sold=Sum('quantity'))
        .filter(total_sold__gt=0)
        .order_by('total_sold')[:5]
    )

    context = {
        'sales_trend': sales_trend,
        'best_selling': best_selling,
        'low_performing': low_performing,
        'filter_type': filter_type,
    }

    return render(request, 'assets/sales_insights.html', context)

@login_required
def sales_report_print(request):
    if not request.user.is_staff:
        return redirect('user_dashboard')

    orders = Order.objects.select_related(
        'item', 'user', 'supplier'
    ).order_by('-created_at')


    total_orders = orders.count()
    total_sales = orders.aggregate(total=Sum('total_amount'))['total'] or 0

    low_stock_count = Item.objects.filter(quantity__lt=10, quantity__gt=0).count()
    out_of_stock_count = Item.objects.filter(quantity=0).count()
    total_items = Item.objects.count()

    best_selling = (
        orders.values('item__name')
        .annotate(total_quantity=Sum('quantity'))
        .order_by('-total_quantity')
        .first()
    )

    best_selling_item = best_selling['item__name'] if best_selling else "N/A"

    top_user_data = (
        orders.values('user__username')
        .annotate(total_orders=Count('id'))
        .order_by('-total_orders')
        .first()
    )

    top_user = top_user_data['user__username'] if top_user_data else "N/A"

    avg_order_value = orders.aggregate(avg=Avg('total_amount'))['avg'] or 0

    context = {
        'orders': orders,
        'total_orders': total_orders,
        'total_sales': total_sales,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'total_items': total_items,
        'best_selling_item': best_selling_item,
        'top_user': top_user,
        'avg_order_value': round(avg_order_value, 2),
    }

    return render(request, 'assets/sales_report_print.html', context)
