from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Customer,Userdetials,Order,OrderItem
from django.contrib.auth import authenticate
from django.forms import ModelForm

class MyUserForm(UserCreationForm):
    class Meta:
        model = Customer
        fields = ('email','phone','username','password1','password2')

Payment_Choices = (
    ('O', 'online payment'),
    ('C', 'cash on delivery'),
)

Shipping_Choices = (
    ('D', 'Ship to this address'),
    ('N', 'Ship to different address'),
)

class CheckoutForm(ModelForm):
    class Meta:
        model = Userdetials
        fields = '__all__'
        exclude = ['user','default']


    payment_option = forms.ChoiceField(
        widget=forms.RadioSelect, choices=Payment_Choices,required=False)
    shipping_choices = forms.ChoiceField(
        widget=forms.RadioSelect, choices=Shipping_Choices,required=False)


class OrderForm(ModelForm):
    class Meta:
        model = Order
        fields = ('status',)

class OrderItemForm(ModelForm):
    class Meta:
        model = OrderItem
        fields = ('status',)