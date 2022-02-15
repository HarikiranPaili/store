from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Customer,Item,OrderItem,Order,Userdetials
# Register your models here.
class BookAdmin(UserAdmin):
    list_display = ( 'email','phone','is_active','is_admin','is_staff')
    list_filter = ('last_login',)
    readonly_fields = ('date_created','last_login')
    search_fields = ('email','phone')
    fieldsets = ()
    filter_horizontal = ()
    exclude = ('is_active','is_staff')

    add_fieldsets = (
        (None,{
             'classes':('wide'),
             'fields':('email','phone','password1','password2'),
         }),
    )
    ordering = ('email',)

class BokAdmin(UserAdmin):
    list_display = ('user','ordered')
    readonly_fields = ('razorpay_signature','razorpay_payment_id','razorpay_order_id','order_id')
    list_filter = ('ordered','user')
    search_fields = ()
    fieldsets = ()
    filter_horizontal = ()

    add_fieldsets = (

    )
    ordering = ()


admin.site.register(Customer,BookAdmin)
admin.site.register(OrderItem)
admin.site.register(Order,BokAdmin)
admin.site.register(Item)
admin.site.register(Userdetials)