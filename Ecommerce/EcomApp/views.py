from django.http import HttpResponse
from django.shortcuts import render,redirect
from django.urls import reverse
from .models import Product,CartItem,Order,Address
from django.views.generic .detail import DetailView
from django.db.models import Q
from django.contrib import messages
from .forms import CreateUserForm
from django.contrib.auth import authenticate,login,logout
import razorpay
import random
from django.core.mail import send_mail


# Create your views here.
def index(req):
    products = Product.objects.all()
    if req.user.is_authenticated:
        cart_item = CartItem.objects.filter(user=req.user)
        length = len(cart_item)
        context = {'products':products,'items':length}
    else:
        context ={'products':products}
    return render(req,"index.html",context)

class SpecificView(DetailView):
    model = Product
    template_name = "prod_detail_view.html"
  
def mobileView(req):
    queryset=Product.prod.mobile_list()
    print(queryset)
    context = {'products':queryset}
    return render(req,"index.html",context)
 
def tvView(req):
    queryset=Product.prod.tv_list()
    print(queryset)
    context = {'products':queryset}
    return render(req,"index.html",context)

def laptopView(req):
   queryset=Product.objects.filter(category__iexact="laptop")
   context = {'products':queryset}
   return render(req,"index.html",context)

def rangeView(req):
    if req.method =="GET":
        return redirect("/")
    else:
        try:
            min =req.POST.get("min")
            max =req.POST.get("max")
            print(min,max)
            products = Product.objects.filter(price__range=(min,max))
            context = {'products':products}
            return render(req,"index.html",context)
        except:
            products = Product.objects.all()
            msg = "Enter both the values for filtering"
            context = {'products':products,'msg':msg}
            return render(req,"index.html",context)
        
def sortProducts(req):
    sort_option = req.GET.get('sort')
    print(sort_option)
    if sort_option == "high_to_low":
        products=Product.objects.all().order_by('-price')
    elif sort_option == "low_to_high":
        products = Product.objects.all().order_by('price')
    else:
        products = Product.objects.all()
    context= {'products':products}
    return render(req,"index.html",context)

def search(req):
    query = req.POST.get('q')
    results = Product.objects.filter(Q(prod_name__icontains = query)|Q(desc__icontains = query)|Q(price__iexact= query))
    context = {'products':results}
    return render(req,"index.html",context)

def addCart(req,prod_id):
    try:
        products = Product.objects.get(product_id = prod_id )
        user = req.user if req.user.is_authenticated else None
        print(user)
        if user:
            cart_item,created = CartItem.objects.get_or_create(product=products,user=user)
        #prod = CartItem.objects.all()
        #context = {'products' : prod}
        print(cart_item,created)
        if not created:
            cart_item.quantity += 1
        else:
            cart_item.quantity = 1
        cart_item.save()
        return redirect('/viewCart')
    except:
        return redirect("login")

def viewCart(req):
    try:
        prod = CartItem.objects.filter(user=req.user)
        context = {}
        total_price=0
        length = len(prod)
        for x in prod:
            total_price += (x.product.price * x.quantity)
            print(total_price)
        context['products'] = prod
        context['total']= total_price
        context['items']= length
        return render(req,'cart.html',context)
    except:
        return redirect("login")


def updateqty(req,uval,item_id):
    c = CartItem.objects.filter(user=req.user,product_id = item_id)
    print(uval,c[0].quantity)
    if uval == 1:
        temp = c[0].quantity+1
        c.update(quantity = temp)
    else:
        temp = c[0].quantity-1
        c.update(quantity = temp)
        if temp == 0:
            c.delete()
    context = {'products':c}
    return redirect("/viewCart")

def removeCart(req,item_id):
    c = CartItem.objects.filter(product_id = item_id)
    c.delete()
    return redirect("/viewCart")
    
def register(req):
    #form = UserCreationForm() default form
    form = CreateUserForm()
    if req.method == "POST":
        form = CreateUserForm(req.POST)
        if form.is_valid():
            form.save()
            print("User created successfully")
            return redirect("/login")
        else:
            messages.error(req,"Your username or password format is invalid")
    context = {'form':form}
    return render(req,"register.html",context)

def login_user(req):
    if req.method == "GET":
        return render(req,"login.html")
    else:
        username = req.POST["uname"]
        passw = req.POST["upass"]
        #print(username,password)
        user = authenticate(req,username=username,password=passw)
        if user is not None:
            login(req,user)
            req.session['uname'] = username
            messages.success(req,"Logged in successfully")
            return redirect("index")
        else:
            messages.error(req,"there was an error.Try again")
            return redirect("/login")
         

def logout_user(req):
    try:
        logout(req)
        del req.session['uname']
        messages.success(req, "You have logged out successfully")
        return redirect("index")
    except:
        logout(req)
        messages.success(req, "You have logged out successfully")
        return redirect("index")


def placeOrder(req):
    prod = CartItem.objects.filter(user=req.user)
    context = {}
    total_price=0
    length = len(prod)
    for x in prod:
        total_price += (x.product.price * x.quantity)
        print(total_price)
    context['products'] = prod
    context['total']= total_price
    context['items']= length
   
    return render(req,"place_order.html",context)

def makePayment(req):
    try:
        cart_item = CartItem.objects.filter(user=req.user)
        oid =random.randrange(1000,9999)
        oid=str(oid)
        total_price=0
    
    
        for x in cart_item:
            total_price += (x.product.price * x.quantity)
            o = Order.objects.create(order_id=oid,product = x.product,quantity = x.quantity,date_added = x.date_added,user =req.user)
        client = razorpay.Client(auth=("rzp_test_cLjJbEefHFaRVM","DKa9PfsvA6uxYZod56Zq6Emu"))
        
        data = { "amount": total_price*100, "currency": "INR", "receipt": oid }
        payment = client.order.create(data=data)
        print(payment)
        context = {}
        context['data'] = payment
        cart_item.delete()
        #sendUserMail()
        orders = Order.objects.filter(user=req.user,is_completed=False)
        msg =f"Order Details : Order id:{oid}, Price : ₹{total_price}"
        send_mail(
        "Order Placed Successfully",
        msg,
        "",
        [req.user.email],
        fail_silently=False,
        )
        orders.update(is_completed = True)
        return render(req,"payment.html",context)
    except:
        messages.error(req,"Amount should be atleast 1")
        return redirect("/")

def viewOrder(req):
   o= Order.objects.filter(user=req.user,is_completed=True)
   context ={'products':o}
   return render(req,"viewOrder.html",context)

def genAddress(req):
    add = Address.objects.filter(user = req.user)
    print(add)
    context ={'address':add}
    return render(req,'address.html',context)
  
def addAddress(req):
    if req.method=="GET":
        return render(req,'addAddress.html')
    else:
        try:
            new_address=req.POST["address"]
            pincode=req.POST["zip"]
            phone=req.POST["phone"]
            a=Address.objects.create(user=req.user,address=new_address,zipcode=pincode,phone=phone)
            return redirect("address")
        except:
            messages.error(req,"zipcode and phone must be integer")
            return render(req,'addAddress.html')
        
def updateAddress(req,pid):
    address = Address.objects.get(user = req.user,id=pid)       
    if req.method=="GET":
        return render(req,"addAddress.html",{"update_address":address})
    else:
        address.address=req.POST["address"]
        address.zipcode=req.POST["zip"]
        address.phone=req.POST["phone"]
        address.save()
        return redirect("address")
    
def deleteAddress(req,pid):
    address = Address.objects.get(user = req.user,id=pid)  
    address.delete()
    return redirect('address')

def buy(req,prod_id):
    oid = random.randrange(1000,9999)
    oid = str(oid)
    prod = Product.objects.get(product_id = prod_id)
    amount = prod.price
    o = Order.objects.create(order_id = oid,product = prod,quantity =1, user = req.user)
    client = razorpay.Client(auth=("rzp_test_cLjJbEefHFaRVM","DKa9PfsvA6uxYZod56Zq6Emu"))
    data ={'amount':amount * 100, "currency":"INR","receipt":oid}
    payment = client.order.create(data = data)
    context = {}
    context['data'] = payment
    orders = Order.objects.filter(user=req.user,is_completed = False)
    msg =f"Order Details : Order id:{oid}, Price : ₹{amount}"
    send_mail(
    "Order Done",
    msg,
    "pswapnil725@gmail.com",
    [req.user.email],
    fail_silently=False,
    )
    orders.update(is_completed=True)
    return render(req,"payment.html",context)