import datetime,operator
import threading
from django.shortcuts import render,redirect
from .models import Item,OrderItem,Order,Userdetials
from django.views.generic import ListView,DetailView,View
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User,auth
from .forms import *
from django import template
from django.http import HttpResponse,HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.mail import EmailMessage,EmailMultiAlternatives
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_str, DjangoUnicodeDecodeError
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from .utls import account_activation_token
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.admin.views.decorators import staff_member_required,user_passes_test

#razorpay details
razorpay_id = settings.RAZORPAY_ID
razorpay_account_id = settings.RAZORPAY_ACCOUNT_ID
import razorpay
razorpay_client = razorpay.Client(auth=(razorpay_id, razorpay_account_id))

# for generating pdf invoice
from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
import os

def render_to_pdf(template_src, context_dict={ }):
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("ISO-8859-1")), result)#, link_callback=fetch_resources)
    if not pdf.err:
        return result.getvalue()
    return None

@method_decorator(login_required, name='dispatch')
class GenerateInvoice(View):
    def get(self, request, pk, *args, **kwargs):
        try:
            order_db = Order.objects.get(id= pk, user= request.user, ordered= True)
            order_detials = (order_db.items.all())
        except:
            return HttpResponse("505 Not Found")
        data = {
            'order_id': order_db.order_id,
            'transaction_id': order_db.razorpay_payment_id,
            'user_email': order_db.user.email,
            'date': str(timezone.now()),
            'name': order_db.user.username,
            'order_detials': order_detials,
            'amount': order_db.total_amount(),
        }
        pdf = render_to_pdf('invoice.html', data)
        return HttpResponse(pdf, content_type='application/pdf')

class HomeView(ListView):
    model = Item
    paginate_by = 8
    template_name = 'home.html'


def vegtables(request):
    print(razorpay_id)
    items = Item.objects.filter(category='V')
    context = {'items': items}
    return render(request,'vegtable.html',context)

def fruits(request):
    items = Item.objects.filter(category='F')
    context = {'items': items}
    return render(request,'fruits.html',context)

def dried(request):
    items = Item.objects.filter(category='D')
    context = {'items': items}
    return render(request,'dried.html',context)

def juices(request):
    items = Item.objects.filter(category='J')
    context = {'items': items}
    return render(request,'juices.html',context)



class ItemDetailView(DetailView):
    model = Item
    template_name = 'product-single.html'

@login_required(login_url='login')
def checkouts(request):
    if request.method == 'POST':
        payment_option = request.POST.get('payment_option')
        shipping_choices = request.POST.get('shipping_choices')
        order = Order.objects.get(user=request.user, ordered=False)
        order.order_id = 'ORDER_ID'+timezone.now().strftime('%Y%m%d%H%M%S')
        if shipping_choices == 'D':
            address_qs = Userdetials.objects.filter(
                    user=request.user,
                    default=True
                )
            if address_qs.exists():
                shipping_address = address_qs[0]
                order.shipping_address = shipping_address
                order.save()
                if payment_option == 'O':
                    order_currency = 'INR'
                    amount = int(order.total_amount()) * 100
                    order_id = order.order_id

                    callback_url = 'http://' + str(get_current_site(request)) + '/payment_handle'
                    notes = {'order-type': "basic order from the website", 'key': 'value'}
                    razorpay_order = razorpay_client.order.create(
                        dict(amount=amount, currency=order_currency, notes=notes, receipt=order_id,
                             payment_capture='0'))
                    order.razorpay_order_id = razorpay_order['id']
                    order.save()
                    context = {
                        'order': order, 'order_id': razorpay_order['id'],
                        'orderId': order_id, 'final_price': amount,
                        'razorpay_merchant_id': razorpay_id, 'callback_url': callback_url
                    }
                    return render(request, 'payment.html', context)
                if payment_option == 'C':
                    order_detials = (order.items.all())
                    context = {
                        'user': order.user,
                        'order': order,
                        'order_details': order_detials
                    }
                    data = {
                        'order_id': order.order_id,
                        'transaction_id': order.razorpay_payment_id,
                        'user_email': order.user.email,
                        'date': str(timezone.now()),
                        'name': order.user.username,
                        'order_detials': order_detials,
                        'amount': order.total_amount(),
                    }
                    pdf = render_to_pdf('invoice.html', data)
                    filename = 'Invoice_' + str(data['order_id']) + '.pdf'
                    mail_subject = 'Recent Order Details'
                    context_dict = {
                        'user': order.user,
                        'order': order,
                        'order_details': order_detials
                    }
                    template = get_template('emailinvoice.html')
                    message = template.render(context_dict)
                    to_email = order.user.email
                    email = EmailMultiAlternatives(
                        mail_subject,
                        "hello",  # necessary to pass some message here
                        settings.EMAIL_HOST_USER,
                        [to_email]
                    )
                    email.attach_alternative(message, "text/html")
                    email.attach(filename, pdf, 'application/pdf')
                    EmailThread(email).start()
                    order.ordered = True
                    order.save()
                    order_item = OrderItem.objects.filter(
                        user=request.user,
                        ordered=False
                    )
                    for i in order_item:
                        i.ordered = True
                        i.save()

                    return render(request, 'success.html', context)
                return redirect('ordersummary', )
        if shipping_choices == 'N':
            form = CheckoutForm()
            context = {'form': form}
            return render(request, '2ndCheckout.html',context)
        return redirect('ordersummary')

@login_required(login_url='login')
def checkout(request):
    try:
        if request.method == 'GET':
            form = CheckoutForm()
            order = Order.objects.get(user=request.user, ordered=False)
            context = {'form': form, 'object': order}
            shipping_address_qs = Userdetials.objects.filter(
                user=request.user,
                default=True
            )
            if shipping_address_qs:
                context.update(
                    {'default_shipping_address': shipping_address_qs[0]})
                return render(request, 'checkout.html', context)
            return render(request, 'checkout.html', context)
        if request.method == 'POST':
            shipping_first_name = request.POST.get('shipping_first_name')
            shipping_last_name = request.POST.get('shipping_last_name')
            shipping_door_number = request.POST.get('shipping_door_number')
            shipping_street = request.POST.get('shipping_street')
            shipping_town = request.POST.get('shipping_town')
            shipping_zip = request.POST.get('shipping_zip')
            phone_no = request.POST.get('shipping_zip')
            payment_option = request.POST.get('payment_option')
            order = Order.objects.get(user=request.user, ordered=False)
            order.order_id = 'ORDER_ID' + timezone.now().strftime('%Y%m%d%H%M%S')

            shipping_address = Userdetials(
                user=request.user,
                first_name=shipping_first_name,
                last_name=shipping_last_name,
                door_number=shipping_door_number,
                street=shipping_street,
                town=shipping_town,
                zip_code=shipping_zip,
                phone=phone_no
            )
            shipping_address.save()
            order.shipping_address = shipping_address
            order.save()
            set_default_shipping = request.POST.get('set_default_shipping')
            if set_default_shipping:
                shipping_address.default = True
                shipping_address.save()
            if payment_option == 'O':
                order_currency = 'INR'
                print('pl')
                amount = int(order.total_amount()) * 100
                order_id = order.order_id
                callback_url = 'http://' + str(get_current_site(request)) + '/payment_handle'
                notes = {'order-type': "basic order from the website", 'key': 'value'}
                razorpay_order = razorpay_client.order.create(
                    dict(amount=amount, currency=order_currency, notes=notes, receipt=order_id,
                         payment_capture='0'))
                order.razorpay_order_id = razorpay_order['id']
                order.save()
                context = {
                    'order': order, 'order_id': razorpay_order['id'],
                    'orderId': order_id, 'final_price': amount,
                    'razorpay_merchant_id': razorpay_id, 'callback_url': callback_url
                }
                return render(request, 'payment.html', context)

            if payment_option == 'C':
                order.ordered = True
                order.save()
                order_item = OrderItem.objects.filter(
                    user=request.user,
                    ordered=False
                )
                for i in order_item:
                    i.ordered = True
                    i.save()
                order_detials = (order.items.all())
                context = {
                    'user': order.user,
                    'order': order,
                    'order_details': order_detials
                }
                data = {
                    'order_id': order.order_id,
                    'user_email': order.user.email,
                    'date': str(timezone.now()),
                    'name': order.user.username,
                    'order_detials': order_detials,
                    'amount': order.total_amount(),
                }
                pdf = render_to_pdf('invoice.html', data)
                filename = 'Invoice_' + str(data['order_id']) + '.pdf'
                mail_subject = 'Recent Order Details'
                context_dict = {
                    'user': order.user,
                    'order': order,
                    'order_details': order_detials
                }
                template = get_template('emailinvoice.html')
                message = template.render(context_dict)
                to_email = order.user.email
                email = EmailMultiAlternatives(
                    mail_subject,
                    "hello",  # necessary to pass some message here
                    settings.EMAIL_HOST_USER,
                    [to_email]
                )
                email.attach_alternative(message, "text/html")
                email.attach(filename, pdf, 'application/pdf')
                EmailThread(email).start()
                return render(request, 'success.html', context)
            else:
                messages.info(request, "No default shipping address available")
                return redirect('checkout')
    except:
        messages.info(request, "You don't have any orders")
        return redirect('home')

@csrf_exempt
def payment_handle(request):
    if request.method == "POST":
        payment_id = request.POST.get('razorpay_payment_id', '')
        order_id = request.POST.get('razorpay_order_id', '')
        signature = request.POST.get('razorpay_signature', '')
        params_dict = {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }
        order_db = Order.objects.get(razorpay_order_id=order_id)
        order_db.razorpay_payment_id = payment_id
        order_db.razorpay_signature = signature
        order_db.save()
        order_item = OrderItem.objects.filter(
            user=request.user,
            ordered=False
        )
        for i in order_item:
            i.ordered = True
            i.save()
        result = razorpay_client.utility.verify_payment_signature(params_dict)
        if result == None:
            amount = int(order_db.total_amount())*100
            razorpay_client.payment.capture(payment_id, amount)
            order_db.ordered = True
            order_db.save()
            order_detials = (order_db.items.all())
            data = {
                'order_id': order_db.order_id,
                'transaction_id': order_db.razorpay_payment_id,
                'user_email': order_db.user.email,
                'date': str(timezone.now()),
                'name': order_db.user.username,
                'order_detials': order_detials,
                'amount': order_db.total_amount(),
            }
            pdf = render_to_pdf('invoice.html', data)
            filename = 'Invoice_' + str(data['order_id']) + '.pdf'
            mail_subject = 'Recent Order Details'
            context_dict = {
                'user': order_db.user,
                'order': order_db,
                'order_details': order_detials
            }
            template = get_template('emailinvoice.html')
            message = template.render(context_dict)
            to_email = order_db.user.email
            email = EmailMultiAlternatives(
                mail_subject,
                "hello",  # necessary to pass some message here
                settings.EMAIL_HOST_USER,
                [to_email]
            )
            email.attach_alternative(message, "text/html")
            email.attach(filename, pdf, 'application/pdf')
            EmailThread(email).start()
            return render(request, 'success.html',context_dict)
        else:
            return render(request, 'failure.html',)

    return redirect('ordersummary')

register= template.Library
@register.filter
@login_required(login_url='login')
def cart_qun(user):
    qs = Order.objects.filter(user=user, ordered=False)
    if qs.exists():
        return qs[0].items.count()
    else:
        return 0

class OrderSummaryView(LoginRequiredMixin, View):
    login_url = '/login'
    redirect_field_name = None
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            order_item = OrderItem.objects.filter(
                user=self.request.user,
                ordered=False,
            )
            context = {
                'object': order,
                'oops': order_item,
            }
            return render(self.request, 'cart.html', context)
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("/")

@login_required(login_url='login')
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item,created = OrderItem.objects.get_or_create(
            item=item,
            user=request.user,
            ordered=False,
        )
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "This item quantity was updated.")
            return redirect("product", slug=slug, )
        else:
            order.items.add(order_item)
            messages.info(request, "This item was added to your cart.")
            return redirect("product", slug=slug, )
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(
            user=request.user, ordered_date=ordered_date,)
        order.items.add(order_item)
        messages.info(request, "This item was added to your cart.")
        return redirect("product", slug=slug,)

@login_required(login_url='login')
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            order.items.remove(order_item)
            order_item.delete()
            messages.info(request, "This item was removed from your cart.")
            return redirect('ordersummary')
        else:
            messages.info(request, "This item was not in your cart")
            return redirect('ordersummary')
    else:
        messages.info(request, "You do not have an active order")
        return redirect('ordersummary')

@login_required(login_url='login')
def decrease_item_quantity(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
               order_item.quantity -= 1
               order_item.save()
               messages.info(request, "Item quantity was updated to your cart.")
               return redirect("ordersummary",)
            else:
                order.items.remove(order_item)
                messages.info(request, "This item was not in your cart")
                return redirect("ordersummary",)
        else:
            messages.info(request, "This item was not in your cart")
            return redirect("product", slug=slug)
    else:
        messages.info(request, "You do not have an active order")
        return redirect("product", slug=slug)

@login_required(login_url='login')
def increase_item_quantity(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "Item quantity was updated to your cart.")
            return redirect("ordersummary")
        else:
            messages.info(request, "This item was not in your cart")
            return redirect("product", slug=slug)
    else:
        messages.info(request, "You do not have an active order")
        return redirect("product", slug=slug)

class EmailThread(threading.Thread):
    def __init__(self,email):
        self.email = email
        threading.Thread.__init__(self)
    def run(self):
        self.email.send(fail_silently=False)

def register(request):
    form = MyUserForm
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        form = MyUserForm(request.POST)
        if password1 == password2:
            if Customer.objects.filter(email=email).exists():
                messages.info(request, 'Email Already Used')
                return redirect('register')
            elif Customer.objects.filter(phone=phone).exists():
                messages.info(request, 'Phone Number Already Used')
                return redirect('register')
            elif Customer.objects.filter(username=username).exists():
                messages.info(request, ' Name Already Used')
                return redirect('register')
            elif len(phone) != 10 or phone.isdigit()==False:
                messages.info(request, 'Provide valid mobile number')
                return redirect('register')

            elif form.is_valid():
                user = Customer.objects.create_user(username=username, email=email,
                                                    phone=phone)
                user.set_password(password1)
                user.is_active = False
                user.save()
                current_site = get_current_site(request)
                email_body = {
                    'user': user,
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': account_activation_token.make_token(user),
                }

                link = reverse('activate', kwargs={
                    'uidb64': email_body['uid'], 'token': email_body['token']})

                email_subject = 'Activate your account'

                activate_url = 'http://' + current_site.domain + link

                email = EmailMessage(
                    email_subject,
                    'Hi ' + user.username + ', Please click the link below to activate your account \n' + activate_url,
                    'noreply@semycolon.com',
                    [email],
                )
                EmailThread(email).start()
                messages.info(request, 'Your account created successfully ,Verification link sent to your mail,Click on the link to activate your account')
                return redirect('login')
            else:
                messages.info(request, 'Password Should be minimum 8 letter contain one number and symbal @')
                return redirect('register')
        else:
              messages.info(request, 'Password Not Matched')
              return redirect('register')

    else:
        return render(request, 'register.html',{'form': form})

class VerificationView(View):
    def get(self, request, uidb64, token):
        try:
            id = force_str(urlsafe_base64_decode(uidb64))
            user = Customer.objects.get(pk=id)

            if not account_activation_token.check_token(user, token):
                return redirect('login'+'?message='+'User already activated')
            if user.is_staff:
                if user.is_active:
                    messages.success(request, 'Account activated successfully')
                    return redirect('staff_login')

            if user.is_active:
                return redirect('login')
            user.is_active = True

            user.save()
            if user.is_staff:
                if user.is_active:
                    messages.success(request, 'Account activated successfully')
                    return redirect('staff_login')

            messages.success(request, 'Account activated successfully')
            return redirect('login')

        except Exception as ex:
            pass
        return redirect('login')

class RequestPasswordRest(View):
    def get(self, request):
        return render(self.request, 'passwordrequest.html',)
    def post(self, request):
        email = request.POST.get('email')
        current_site = get_current_site(request)
        user = Customer.objects.filter(email=email)
        if user.exists():
            email_body = {
                'user': user[0],
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user[0].pk)),
                'token': PasswordResetTokenGenerator().make_token(user[0]),
            }

            link = reverse('reset_user_password', kwargs={
                'uidb64': email_body['uid'], 'token': email_body['token']})

            email_subject = 'Password Reset'

            reset_url = 'http://' + current_site.domain + link

            email = EmailMessage(
                email_subject,
                'Hi,\n Please click the link below to reset password \n' + reset_url,
                'noreply@semycolon.com',
                [email],
            )
            EmailThread(email).start()
            messages.info(request, 'Password Reset link sent to your mail')
            return render(self.request, 'passwordrequest.html', )

        return render(self.request, 'passwordrequest.html',)

class PasswordResetView(View):
    def get(self, request, uidb64, token):
        context = {
            'uidb64': uidb64,
            'token': token,
        }
        user_id = force_str(urlsafe_base64_decode(uidb64))
        user = Customer.objects.get(pk=user_id)
        if not PasswordResetTokenGenerator().check_token(user,token):
            messages.info(request, 'Link already expired, request a new one ')
            return render(self.request, 'passwordrequest.html', )
        return render(self.request, 'passwordreset.html',context)

    def post(self, request, uidb64, token):
        context = {
            'uidb64': uidb64,
            'token': token,
        }
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        if password != password2:
            if len(password)>7 and (not password.isalpha() and operator.contains(password, '@')):
                user_id = force_str(urlsafe_base64_decode(uidb64))
                user = Customer.objects.get(pk=user_id)
                user.set_password(password)
                user.save()
                messages.info(request, 'Password Changed Successfully')
                return redirect('login')
            else:
                messages.info(request, 'Password Should be minimum 8 letter contain one number and symbal @')
                return render(self.request, 'passwordreset.html', context)
        else:
            messages.info(request, 'Password Not Matched')
            return render(self.request, 'passwordreset.html', context)

def loginview(request):
    if request.method == 'POST':
        email = request.POST.get('email or phone')
        phone = request.POST.get('email or phone')
        password = request.POST.get('password')
        user = authenticate(request,email=email,phone=phone,password=password)
        if user is not None:
            login(request,user)
            return redirect('/')
        else:
            messages.info(request,'Invalid Details')
            return redirect('login')

    return render(request, 'login.html')

@login_required(login_url='login')
def logout(request):
    auth.logout(request)
    return redirect('home')

@user_passes_test(lambda u: u.is_superuser)
def creatstaff(request):
    form = MyUserForm
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        form = MyUserForm(request.POST)
        if password1 == password2:
            if Customer.objects.filter(email=email).exists():
                messages.info(request, 'Email Already Used')
                return redirect('register')
            elif Customer.objects.filter(phone=phone).exists():
                messages.info(request, 'Phone Number Already Used')
                return redirect('register')
            elif Customer.objects.filter(username=username).exists():
                messages.info(request, ' Name Already Used')
                return redirect('register')
            elif len(phone) != 10 or phone.isdigit()==False:
                messages.info(request, 'Provide valid mobile number')
                return redirect('register')

            elif form.is_valid():
                user = Customer.objects.create_user(username=username, email=email,
                                                    phone=phone,)
                user.set_password(password1)
                user.is_active = False
                user.is_staff = True
                user.save()
                current_site = get_current_site(request)
                email_body = {
                    'user': user,
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': account_activation_token.make_token(user),
                }

                link = reverse('activate', kwargs={
                    'uidb64': email_body['uid'], 'token': email_body['token']})

                email_subject = 'Activate your account'

                activate_url = 'http://' + current_site.domain + link

                email = EmailMessage(
                    email_subject,
                    'Hi ' + user.username + ', Please click the link below to activate your account \n' + activate_url,
                    'noreply@semycolon.com',
                    [email],
                )
                EmailThread(email).start()
                messages.info(request, 'Your account created successfully ,Verification link sent to your mail,Click on the link to activate your account')
                return redirect('staff_login')
            else:
                messages.info(request, 'Password Should be minimum 8 letter contain one number and symbal @')
                return redirect('creatstaff')
        else:
              messages.info(request, 'Password Not Matched')
              return redirect('creatstaff')

    else:
        return render(request, 'staffregister.html',{'form': form})

def staff_login(request):
    if request.method == 'POST':
        email = request.POST.get('email or phone')
        phone = request.POST.get('email or phone')
        password = request.POST.get('password')
        user = authenticate(request, email=email, phone=phone, password=password)
        if user is not None:
            login(request, user)
            return redirect('checkstatus')
        else:
            messages.info(request, 'Invalid Details')
            return redirect('staff_login')

    return render(request, 'staff_login.html')

@staff_member_required
def checkstatus(request):
    orders = Order.objects.all()
    orders = orders.filter(ordered=True,)
    context = {
        'orders':orders
    }
    return render(request, 'orderform.html',context)

@staff_member_required
def statusupdate(request,pk):
    order = Order.objects.get(id=pk)
    form = OrderForm(instance=order)
    if request.method == 'POST':
        form = OrderForm(request.POST,instance=order)
        if form.is_valid():
            form.save()
            messages.info(request,'Updated Successfully')

    order_count = order.items.count()
    context = {
        'order_count': order_count,
        'orders':order,'form': form
    }
    return render(request, 'statusupdate.html',context)

@staff_member_required
def updateorderitem(request,pk):
    order = OrderItem.objects.get(id=pk)
    form = OrderItemForm(instance=order)
    if request.method == 'POST':
        form = OrderItemForm(request.POST,instance=order)
        if form.is_valid():
            form.save()
            messages.info(request,'Updated Successfully')

            #return redirect('checkstatus')
    context = {
        'form': form,
        'order': order
    }
    return render(request, 'orderitemupdate.html',context)
