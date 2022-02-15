from django.urls import path
from django.contrib import admin
from . import views
from .views import *

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',HomeView.as_view(), name='home' ),
    path('vegtables',vegtables, name='vegtables' ),
    path('dried',dried, name='dried' ),
    path('juices',juices, name='juices' ),
    path('fruits',fruits, name='fruits' ),
    path('product/<slug>',ItemDetailView.as_view(), name='product'),
    path('add_to_cart/<slug>', add_to_cart, name='add_to_cart'),
    path('remove_from_cart/<slug>', remove_from_cart, name='remove_from_cart'),
    path('increase_item_quantity/<slug>', increase_item_quantity, name='increase_item_quantity'),
    path('decrease_item_quantity/<slug>', decrease_item_quantity, name='decrease_item_quantity'),
    path('ordersummary', OrderSummaryView.as_view(), name='ordersummary'),
    path('payment_handle',views.payment_handle, name='payment_handle'),
    path('checkout', checkout, name='checkout'),
    path('checkouts', checkouts, name='checkouts'),
    path('login', loginview, name='login'),
    path('logout', logout, name='logout'),
    path('register', register, name='register'),
    path('staff_login', staff_login, name='staff_login'),
    path('creatstaff', creatstaff, name='creatstaff'),
    path('activate/<uidb64>/<token>',VerificationView.as_view(), name='activate'),
    path('set-new-password/<uidb64>/<token>',PasswordResetView.as_view(), name='reset_user_password'),
    path('request_password', RequestPasswordRest.as_view(), name='request_password'),
    path('generateinvoice/<int:pk>/', views.GenerateInvoice.as_view(), name='generateinvoice'),
    path('statusupdate/<int:pk>/', statusupdate, name='statusupdate'),
    path('updateorderitem/<int:pk>/', updateorderitem, name='updateorderitem'),
    path('checkstatus', checkstatus, name='checkstatus'),

]
