from  django.db import models
from django.contrib.auth.models import AbstractBaseUser,BaseUserManager
from django.conf import settings
from django.shortcuts import reverse,redirect
from autoslug import AutoSlugField
from django import forms

class CustomerManager(BaseUserManager):
    def create_user(self, email, phone, username,password=None):
        if not email:
            raise ValueError('Users must have an email address')
        if not phone:
            raise ValueError('Users must have an phone number')
        if not username:
            raise ValueError('Users must have an name')

        user = self.model(
            email=CustomerManager.normalize_email(email),
            phone=phone,
            username=username,
        )

        user.set_password(password)
        user.save(using=self._db)
        return user


    def create_superuser(self, email, phone, username,password=None):
        user = self.create_user(
                        email=self.normalize_email(email),
                        phone=phone,
                        username=username,
                        password=password,
        )
        user.is_admin = True
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user

class Customer(AbstractBaseUser):
    email = models.EmailField(verbose_name='email address',unique=True,max_length=100)
    phone = models.CharField(verbose_name='phone number',unique=True,max_length=10)
    username = models.CharField(verbose_name='Name',unique=True,max_length=50,null=True)
    date_created = models.DateTimeField(verbose_name='date created',auto_now_add=True)
    last_login = models.DateTimeField(verbose_name='last login',auto_now=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ['phone','username']

    objects = CustomerManager()

    def has_perm(self,perm,obj=None):
        return True

    def has_module_perms(self,app_label):
        return True

#for item
CATEGORY_CHOICES = (
    ('V', 'vegtables'),
    ('F', 'fruits'),
    ('D', 'dried'),
    ('J', 'juices')
)
#for shipping
Category = (
    ('Pending', 'Pending'),
    ('Out for Delivery', 'Out for Delivery'),
    ('Delivered', 'Delivered'),
)
class Item(models.Model):
    title = models.CharField(max_length=100)
    price = models.FloatField()
    discount_price = models.FloatField(blank=True,null=True)
    category = models.CharField(choices=CATEGORY_CHOICES, max_length=1,null=True)
    slug = AutoSlugField(populate_from='title')
    description = models.TextField(null=True)
    images = models.CharField(blank=True,null=True,max_length=100000)
    image = models.ImageField(blank=True,null=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("product", kwargs={
            'slug': self.slug
        })

    def get_add_to_cart_url(self):
        return reverse("add_to_cart",kwargs={
            'slug': self.slug,
        })

    def get_remove_from_cart_url(self):
        return reverse("remove_from_cart",kwargs={
            'slug': self.slug
        })

class OrderItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE,blank=True,null=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    ordered = models.BooleanField(default=False)
    quantity = models.IntegerField(default=1)
    status = models.CharField(max_length=200,null=True,choices=Category,default='Pending')

    def __str__(self):
        return f"{self.quantity} of {self.item.title}"

    def get_total_item_price(self):
        return self.quantity * self.item.price

    def get_total_discount_item_price(self):
        if self.item.discount_price==None:
            return self.item.price
        return self.quantity * self.item.discount_price

    def get_final_price(self):
        if self.item.discount_price:
            return self.get_total_discount_item_price()
        return self.get_total_item_price()

    def get_amount_saved(self):
        return (self.get_total_item_price()) -(self.get_total_discount_item_price())

    def total_saved(self):
        return (self.get_amount_saved())


class Order(models.Model):

    user = models.ForeignKey(Customer,
                             on_delete=models.CASCADE,null=True)
    items = models.ManyToManyField(OrderItem,)
    start_date = models.DateTimeField(auto_now_add=True)
    ordered_date = models.DateTimeField()
    ordered = models.BooleanField(default=False)
    order_id = models.CharField(unique=True, max_length=100, null=True, blank=True, default=None)
    shipping_address = models.ForeignKey(
        'Userdetials', related_name='shipping_address', on_delete=models.SET_NULL, blank=True, null=True)
    razorpay_order_id = models.CharField(max_length=500, null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=500, null=True, blank=True)
    razorpay_signature = models.CharField(max_length=500, null=True, blank=True)
    status = models.CharField(max_length=200,null=True,choices=Category,default='Pending')


    def __str__(self):
        return str(self.user)

    def get_total(self):
        total = 0
        for order_item in self.items.all():
            total += order_item.get_total_item_price()
        return total

    def total_amount(self):
        total = 0
        for order_item in self.items.all():
            total += order_item.get_final_price()
        return total+50

    def get_total_saved(self,):
        total = 0
        for order_item in self.items.all():
            total += order_item.get_amount_saved()
        return total

def get_foo():
    return Customer().username


class Userdetials(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    first_name = models.CharField(max_length=20,null=True)
    last_name = models.CharField(max_length=20,null=True)
    door_number = models.CharField(max_length=20,null=True)
    street = models.CharField(max_length=30,null=True)
    town = models.CharField(max_length=30,null=True)
    zip_code = models.CharField(max_length=6,null=True)
    phone = models.CharField(max_length=14,null=True)
    default = models.BooleanField(default=False)

    def __str__(self):
        return str(self.user)

    class Meta:
        verbose_name_plural = 'Addresses'





