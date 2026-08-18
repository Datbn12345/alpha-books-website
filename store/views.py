from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages

from .models import (
    Category,
    Book,
    Cart,
    CartItem,
    Order,
    OrderItem,
)


# =========================================================
# TRANG CHỦ
# =========================================================

def home(request):

    categories = Category.objects.filter(
        is_active=True
    )

    books = Book.objects.filter(
        is_active=True
    )

    context = {
        "categories": categories,
        "books": books,
    }

    return render(
        request,
        "store/home.html",
        context
    )


# =========================================================
# DANH SÁCH SÁCH
# =========================================================

def book_list(request):

    books = Book.objects.filter(
        is_active=True
    )

    categories = Category.objects.filter(
        is_active=True
    )

    # Tìm kiếm
    query = request.GET.get(
        "q",
        ""
    ).strip()

    if query:

        books = books.filter(
            title__icontains=query
        )


    # Lọc danh mục
    category_id = request.GET.get(
        "category",
        ""
    )

    if category_id:

        books = books.filter(
            category_id=category_id
        )


    # Sắp xếp
    sort = request.GET.get(
        "sort",
        "newest"
    )

    if sort == "price_asc":

        books = books.order_by(
            "price"
        )

    elif sort == "price_desc":

        books = books.order_by(
            "-price"
        )

    else:

        books = books.order_by(
            "-created_at"
        )


    context = {
        "books": books,
        "categories": categories,
        "query": query,
        "selected_category": category_id,
        "selected_sort": sort,
    }

    return render(
        request,
        "store/book_list.html",
        context
    )


# =========================================================
# CHI TIẾT SÁCH
# =========================================================

def book_detail(
    request,
    book_id
):

    book = get_object_or_404(
        Book,
        id=book_id,
        is_active=True
    )


    if request.method == "POST":

        # Chưa đăng nhập
        if not request.user.is_authenticated:

            return redirect(
                f"/login/?next=/books/{book.id}/"
            )


        quantity = int(
            request.POST.get(
                "quantity",
                1
            )
        )


        if quantity < 1:

            quantity = 1


        if quantity > book.stock:

            quantity = book.stock


        cart, created = Cart.objects.get_or_create(
            user=request.user
        )


        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            book=book
        )


        if created:

            cart_item.quantity = quantity

        else:

            cart_item.quantity += quantity

            if cart_item.quantity > book.stock:

                cart_item.quantity = book.stock


        cart_item.save()


        messages.success(
            request,
            "Đã thêm sách vào giỏ hàng."
        )


        return redirect(
            "cart_detail"
        )


    context = {
        "book": book,
    }


    return render(
        request,
        "store/book_detail.html",
        context
    )


# =========================================================
# GIỎ HÀNG
# =========================================================

@login_required(
    login_url="/login/"
)
def cart_detail(request):

    cart, created = Cart.objects.get_or_create(
        user=request.user
    )


    items = cart.items.select_related(
        "book"
    )


    total = sum(
        item.book.price * item.quantity
        for item in items
    )


    context = {
        "cart": cart,
        "items": items,
        "total": total,
    }


    return render(
        request,
        "store/cart_detail.html",
        context
    )


# =========================================================
# CẬP NHẬT SỐ LƯỢNG GIỎ HÀNG
# =========================================================

@login_required(
    login_url="/login/"
)
def cart_update(
    request,
    item_id
):

    item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )


    if request.method == "POST":

        try:

            quantity = int(
                request.POST.get(
                    "quantity",
                    1
                )
            )

        except ValueError:

            quantity = 1


        if quantity < 1:

            quantity = 1


        if quantity > item.book.stock:

            quantity = item.book.stock


        if quantity <= 0:

            item.delete()

        else:

            item.quantity = quantity

            item.save()


    return redirect(
        "cart_detail"
    )


# =========================================================
# XÓA SẢN PHẨM KHỎI GIỎ
# =========================================================

@login_required(
    login_url="/login/"
)
def cart_remove(
    request,
    item_id
):

    item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )


    if request.method == "POST":

        item.delete()


        messages.success(
            request,
            "Đã xóa sách khỏi giỏ hàng."
        )


    return redirect(
        "cart_detail"
    )


# =========================================================
# ĐĂNG KÝ
# =========================================================

def register(request):

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        password2 = request.POST.get(
            "password2",
            ""
        )


        if not username or not email or not password:

            return render(
                request,
                "store/register.html",
                {
                    "error":
                    "Vui lòng nhập đầy đủ thông tin."
                }
            )


        if password != password2:

            return render(
                request,
                "store/register.html",
                {
                    "error":
                    "Mật khẩu nhập lại không khớp."
                }
            )


        if User.objects.filter(
            username=username
        ).exists():

            return render(
                request,
                "store/register.html",
                {
                    "error":
                    "Tên đăng nhập đã tồn tại."
                }
            )


        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )


        login(
            request,
            user
        )


        return redirect(
            "home"
        )


    return render(
        request,
        "store/register.html"
    )


# =========================================================
# ĐĂNG NHẬP
# =========================================================

def login_view(request):

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )


        user = authenticate(
            request,
            username=username,
            password=password
        )


        if user is not None:

            login(
                request,
                user
            )


            next_url = request.GET.get(
                "next"
            )


            if next_url:

                return redirect(
                    next_url
                )


            return redirect(
                "home"
            )


        return render(
            request,
            "store/login.html",
            {
                "error":
                "Tên đăng nhập hoặc mật khẩu không đúng."
            }
        )


    return render(
        request,
        "store/login.html"
    )


# =========================================================
# ĐĂNG XUẤT
# =========================================================

def logout_view(request):

    logout(
        request
    )


    return redirect(
        "home"
    )


# =========================================================
# CHECKOUT / ĐẶT HÀNG
# =========================================================

@login_required(
    login_url="/login/"
)
def checkout(request):

    cart, created = Cart.objects.get_or_create(
        user=request.user
    )


    items = cart.items.select_related(
        "book"
    )


    # Nếu giỏ hàng trống
    if not items.exists():

        messages.warning(
            request,
            "Giỏ hàng của bạn đang trống."
        )

        return redirect(
            "cart_detail"
        )


    total = sum(
        item.book.price * item.quantity
        for item in items
    )


    if request.method == "POST":

        full_name = request.POST.get(
            "full_name",
            ""
        ).strip()

        phone = request.POST.get(
            "phone",
            ""
        ).strip()

        address = request.POST.get(
            "address",
            ""
        ).strip()

        payment_method = request.POST.get(
            "payment_method",
            "cod"
        )

        note = request.POST.get(
            "note",
            ""
        ).strip()


        # Kiểm tra thông tin
        if not full_name:

            return render(
                request,
                "store/checkout.html",
                {
                    "items": items,
                    "total": total,
                    "error":
                    "Vui lòng nhập họ và tên."
                }
            )


        if not phone:

            return render(
                request,
                "store/checkout.html",
                {
                    "items": items,
                    "total": total,
                    "error":
                    "Vui lòng nhập số điện thoại."
                }
            )


        if not address:

            return render(
                request,
                "store/checkout.html",
                {
                    "items": items,
                    "total": total,
                    "error":
                    "Vui lòng nhập địa chỉ nhận hàng."
                }
            )


        # Kiểm tra tồn kho
        for item in items:

            if item.quantity > item.book.stock:

                return render(
                    request,
                    "store/checkout.html",
                    {
                        "items": items,
                        "total": total,
                        "error":
                        f'Sách "{item.book.title}" '
                        f'không đủ số lượng trong kho.'
                    }
                )


        # Tạo đơn hàng
        order = Order.objects.create(

            user=request.user,

            full_name=full_name,

            phone=phone,

            address=address,

            payment_method=payment_method,

            status="pending",

            total_amount=total,

            note=note
        )


        # Tạo chi tiết đơn hàng
        for item in items:

            OrderItem.objects.create(

                order=order,

                book=item.book,

                quantity=item.quantity,

                price=item.book.price
            )


            # Trừ tồn kho
            item.book.stock -= item.quantity

            item.book.save()


        # Xóa giỏ hàng
        items.delete()


        messages.success(
            request,
            "Đặt hàng thành công!"
        )


        return redirect(
            "order_detail",
            order_id=order.id
        )


    context = {
        "items": items,
        "total": total,
    }


    return render(
        request,
        "store/checkout.html",
        context
    )


# =========================================================
# CHI TIẾT ĐƠN HÀNG
# =========================================================

@login_required(
    login_url="/login/"
)
def order_detail(
    request,
    order_id
):

    order = get_object_or_404(
        Order.objects.prefetch_related(
            "items__book"
        ),
        id=order_id,
        user=request.user
    )


    context = {
        "order": order,
    }


    return render(
        request,
        "store/order_detail.html",
        context
    )

@login_required(login_url="/login/")
def my_orders(request):

    orders = (
        request.user.orders
        .prefetch_related("items__book")
        .all()
    )

    context = {
        "orders": orders,
    }

    return render(
        request,
        "store/my_orders.html",
        context
    )