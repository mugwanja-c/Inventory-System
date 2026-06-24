import re
from .models import Profile
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

@login_required
def profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip().replace(" ", "").replace("-", "")

        
        if not re.fullmatch(r'(?:\+254|254|0)(7|1)\d{8}', phone):
            messages.error(request, "Invalid phone format. Use 0712345678 or +254712345678.")
            return render(request, "accounts/profile.html", {"profile": profile})

        
        request.user.email = email
        request.user.save()

    
        profile.phone = phone
        profile.save()

        messages.success(request, "Profile updated successfully!")
        return redirect("user_dashboard")

    return render(request, "accounts/profile.html", {"profile": profile})