# forms.py
from django import forms
from .models import Order, Supplier

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['item', 'quantity', 'delivery_location', 'supplier']
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-select'}),
        }
