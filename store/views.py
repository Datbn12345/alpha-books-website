from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import (
    Sum,
    Avg,
    Count,
    F,
    DecimalField,
    ExpressionWrapper,
)
from django.http import JsonResponse
from google import genai
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import models
from django.db.models.functions import TruncDate
from decimal import Decimal
import json
import re
from .models import (
    Category,
    Book,
    Cart,
    CartItem,
    Order,
    OrderItem,
    Review,
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
    ).order_by(
        "-created_at"
    )[:8]

    # =====================================================
    # SÁCH BÁN CHẠY
    # =====================================================

    best_selling_books = (
        Book.objects
        .filter(
            is_active=True,
            order_items__order__status__in=[
                "pending",
                "confirmed",
                "shipping",
                "completed",
            ]
        )
        .annotate(
            total_sold=Sum(
                "order_items__quantity"
            )
        )
        .order_by(
            "-total_sold",
            "-created_at"
        )[:8]
    )

    # =====================================================
    # SÁCH NỔI BẬT DỰA TRÊN ĐÁNH GIÁ
    # =====================================================

    featured_books = (
        Book.objects
        .filter(
            is_active=True,
            reviews__rating__isnull=False
        )
        .annotate(
            average_rating=Avg(
                "reviews__rating"
            ),
            review_count=Count(
                "reviews"
            )
        )
        .order_by(
            "-average_rating",
            "-review_count",
            "-created_at"
        )[:8]
    )

    context = {
        "categories": categories,
        "books": books,
        "best_selling_books": best_selling_books,
        "featured_books": featured_books,
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

    # =====================================================
    # TÌM KIẾM
    # =====================================================

    query = request.GET.get(
        "q",
        ""
    ).strip()

    if query:

        books = books.filter(
            models.Q(
                title__icontains=query
            )
            |
            models.Q(
                authors__name__icontains=query
            )
        ).distinct()

    # =====================================================
    # LỌC THEO DANH MỤC
    # =====================================================

    category_id = request.GET.get(
        "category",
        ""
    )

    if category_id:

        books = books.filter(
            category_id=category_id
        )

    # =====================================================
    # SẮP XẾP
    # =====================================================

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

def book_detail(request, book_id):

    book = get_object_or_404(
        Book,
        id=book_id,
        is_active=True
    )

    # =====================================================
    # THÊM VÀO GIỎ HÀNG
    # =====================================================

    if request.method == "POST":

        # Kiểm tra request có phải thêm giỏ hàng không
        if request.POST.get("quantity") is not None:

            # -------------------------------------------------
            # CHƯA ĐĂNG NHẬP
            # -------------------------------------------------

            if not request.user.is_authenticated:

                messages.warning(
                    request,
                    "Bạn cần đăng nhập để thêm sách vào giỏ hàng."
                )

                return redirect(
                    f"/login/?next=/books/{book.id}/"
                )

            # -------------------------------------------------
            # LẤY SỐ LƯỢNG
            # -------------------------------------------------

            try:

                quantity = int(
                    request.POST.get(
                        "quantity",
                        1
                    )
                )

            except (TypeError, ValueError):

                messages.error(
                    request,
                    "Thêm vào giỏ hàng thất bại. "
                    "Số lượng sách không hợp lệ."
                )

                return redirect(
                    "book_detail",
                    book_id=book.id
                )

            # -------------------------------------------------
            # KIỂM TRA SỐ LƯỢNG
            # -------------------------------------------------

            if quantity < 1:

                messages.error(
                    request,
                    "Thêm vào giỏ hàng thất bại. "
                    "Số lượng phải lớn hơn 0."
                )

                return redirect(
                    "book_detail",
                    book_id=book.id
                )

            # -------------------------------------------------
            # HẾT HÀNG
            # -------------------------------------------------

            if book.stock <= 0:

                messages.error(
                    request,
                    f'Không thể thêm "{book.title}" vào giỏ hàng. '
                    "Sách hiện đã hết hàng."
                )

                return redirect(
                    "book_detail",
                    book_id=book.id
                )

            # -------------------------------------------------
            # VƯỢT QUÁ TỒN KHO
            # -------------------------------------------------

            if quantity > book.stock:

                messages.error(
                    request,
                    f'Không thể thêm "{book.title}" vào giỏ hàng. '
                    f"Chỉ còn {book.stock} cuốn trong kho."
                )

                return redirect(
                    "book_detail",
                    book_id=book.id
                )

            # -------------------------------------------------
            # TẠO GIỎ HÀNG
            # -------------------------------------------------

            cart, created = Cart.objects.get_or_create(
                user=request.user
            )

            cart_item, item_created = (
                CartItem.objects.get_or_create(
                    cart=cart,
                    book=book
                )
            )

            # -------------------------------------------------
            # KIỂM TRA NẾU SẢN PHẨM ĐÃ CÓ TRONG GIỎ
            # -------------------------------------------------

            if item_created:

                cart_item.quantity = quantity

            else:

                new_quantity = (
                    cart_item.quantity
                    + quantity
                )

                if new_quantity > book.stock:

                    messages.error(
                        request,
                        f'Không thể thêm thêm {quantity} cuốn '
                        f'"{book.title}". '
                        f"Trong giỏ đã có {cart_item.quantity} cuốn "
                        f"và kho chỉ còn {book.stock} cuốn."
                    )

                    return redirect(
                        "book_detail",
                        book_id=book.id
                    )

                cart_item.quantity = new_quantity

            cart_item.save()

            messages.success(
                request,
                f'Đã thêm "{book.title}" vào giỏ hàng thành công.'
            )

            return redirect(
                "cart_detail"
            )

    # =====================================================
    # ĐÁNH GIÁ
    # =====================================================

    reviews = (
        Review.objects
        .filter(
            book=book
        )
        .select_related(
            "user"
        )
    )

    review_count = reviews.count()

    average_rating = 0

    if review_count > 0:

        average_rating = sum(
            review.rating
            for review in reviews
        ) / review_count

    user_review = None

    if request.user.is_authenticated:

        user_review = Review.objects.filter(
            user=request.user,
            book=book
        ).first()

    context = {
        "book": book,
        "reviews": reviews,
        "user_review": user_review,
        "review_count": review_count,
        "average_rating": average_rating,
    }

    return render(
        request,
        "store/book_detail.html",
        context
    )


# =========================================================
# THÊM / SỬA ĐÁNH GIÁ
# =========================================================

@login_required(login_url="/login/")
def add_review(request, book_id):

    book = get_object_or_404(
        Book,
        id=book_id,
        is_active=True
    )

    if request.method != "POST":

        messages.error(
            request,
            "Đánh giá thất bại. "
            "Yêu cầu không hợp lệ."
        )

        return redirect(
            "book_detail",
            book_id=book.id
        )

    # =====================================================
    # KIỂM TRA ĐÃ MUA SÁCH
    # =====================================================

    has_purchased = OrderItem.objects.filter(
        order__user=request.user,
        order__status="completed",
        book=book
    ).exists()

    if not has_purchased:

        messages.error(
            request,
            f'Bạn chưa mua "{book.title}" '
            "hoặc đơn hàng chưa hoàn thành. "
            "Chỉ khách hàng đã mua và hoàn thành đơn hàng "
            "mới có thể đánh giá sách."
        )

        return redirect(
            "book_detail",
            book_id=book.id
        )

    # =====================================================
    # LẤY DỮ LIỆU
    # =====================================================

    rating = request.POST.get(
        "rating",
        ""
    )

    comment = request.POST.get(
        "comment",
        ""
    ).strip()

    # =====================================================
    # KIỂM TRA SỐ SAO
    # =====================================================

    try:

        rating = int(rating)

    except (ValueError, TypeError):

        messages.error(
            request,
            "Đánh giá thất bại. "
            "Số sao không hợp lệ."
        )

        return redirect(
            "book_detail",
            book_id=book.id
        )

    if rating < 1 or rating > 5:

        messages.error(
            request,
            "Đánh giá thất bại. "
            "Vui lòng chọn số sao từ 1 đến 5."
        )

        return redirect(
            "book_detail",
            book_id=book.id
        )

    # =====================================================
    # KIỂM TRA ĐÁNH GIÁ CŨ
    # =====================================================

    review = Review.objects.filter(
        user=request.user,
        book=book
    ).first()

    if review:

        review.rating = rating
        review.comment = comment
        review.save()

        messages.success(
            request,
            "Đánh giá của bạn đã được cập nhật thành công."
        )

    else:

        Review.objects.create(
            user=request.user,
            book=book,
            rating=rating,
            comment=comment
        )

        messages.success(
            request,
            "Đánh giá sách thành công."
        )

    return redirect(
        "book_detail",
        book_id=book.id
    )


# =========================================================
# XÓA ĐÁNH GIÁ
# =========================================================

@login_required(login_url="/login/")
def delete_review(request, book_id):

    book = get_object_or_404(
        Book,
        id=book_id,
        is_active=True
    )

    review = get_object_or_404(
        Review,
        book=book,
        user=request.user
    )

    if request.method == "POST":

        review.delete()

        messages.success(
            request,
            "Đã xóa đánh giá của bạn thành công."
        )

        return redirect(
            "book_detail",
            book_id=book.id
        )

    messages.error(
        request,
        "Xóa đánh giá thất bại. "
        "Phương thức yêu cầu không hợp lệ."
    )

    return redirect(
        "book_detail",
        book_id=book.id
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

    if request.method != "POST":

        messages.error(
            request,
            "Cập nhật giỏ hàng thất bại. "
            "Yêu cầu không hợp lệ."
        )

        return redirect(
            "cart_detail"
        )

    # =====================================================
    # KIỂM TRA SỐ LƯỢNG
    # =====================================================

    quantity_raw = request.POST.get(
        "quantity",
        ""
    )

    try:

        quantity = int(
            quantity_raw
        )

    except (ValueError, TypeError):

        messages.error(
            request,
            "Cập nhật số lượng thất bại. "
            "Số lượng phải là một số nguyên."
        )

        return redirect(
            "cart_detail"
        )

    if quantity < 1:

        messages.error(
            request,
            "Cập nhật số lượng thất bại. "
            "Số lượng phải lớn hơn 0."
        )

        return redirect(
            "cart_detail"
        )

    # =====================================================
    # KIỂM TRA TỒN KHO
    # =====================================================

    if item.book.stock <= 0:

        messages.error(
            request,
            f'Cập nhật thất bại. '
            f'"{item.book.title}" hiện đã hết hàng.'
        )

        return redirect(
            "cart_detail"
        )

    if quantity > item.book.stock:

        messages.error(
            request,
            f'Cập nhật thất bại. '
            f'"{item.book.title}" chỉ còn '
            f'{item.book.stock} cuốn trong kho.'
        )

        return redirect(
            "cart_detail"
        )

    # =====================================================
    # CẬP NHẬT
    # =====================================================

    item.quantity = quantity
    item.save()

    messages.success(
        request,
        f'Đã cập nhật số lượng "{item.book.title}" '
        "thành công."
    )

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

    if request.method != "POST":

        messages.error(
            request,
            "Xóa sản phẩm thất bại. "
            "Yêu cầu không hợp lệ."
        )

        return redirect(
            "cart_detail"
        )

    book_title = item.book.title

    item.delete()

    messages.success(
        request,
        f'Đã xóa "{book_title}" khỏi giỏ hàng thành công.'
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

        # =================================================
        # KIỂM TRA DỮ LIỆU
        # =================================================

        if not username:

            messages.error(
                request,
                "Đăng ký thất bại. "
                "Vui lòng nhập tên đăng nhập."
            )

            return render(
                request,
                "store/register.html"
            )

        if not email:

            messages.error(
                request,
                "Đăng ký thất bại. "
                "Vui lòng nhập email."
            )

            return render(
                request,
                "store/register.html"
            )

        if not password:

            messages.error(
                request,
                "Đăng ký thất bại. "
                "Vui lòng nhập mật khẩu."
            )

            return render(
                request,
                "store/register.html"
            )

        if password != password2:

            messages.error(
                request,
                "Đăng ký thất bại. "
                "Mật khẩu nhập lại không khớp."
            )

            return render(
                request,
                "store/register.html"
            )

        # =================================================
        # KIỂM TRA USERNAME
        # =================================================

        if User.objects.filter(
            username=username
        ).exists():

            messages.error(
                request,
                f'Đăng ký thất bại. '
                f'Tên đăng nhập "{username}" đã tồn tại.'
            )

            return render(
                request,
                "store/register.html"
            )

        # =================================================
        # TẠO TÀI KHOẢN
        # =================================================

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        login(
            request,
            user
        )

        messages.success(
            request,
            f'Đăng ký tài khoản "{username}" thành công.'
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

        if not username:

            messages.error(
                request,
                "Đăng nhập thất bại. "
                "Vui lòng nhập tên đăng nhập."
            )

            return render(
                request,
                "store/login.html"
            )

        if not password:

            messages.error(
                request,
                "Đăng nhập thất bại. "
                "Vui lòng nhập mật khẩu."
            )

            return render(
                request,
                "store/login.html"
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

            messages.success(
                request,
                f'Đăng nhập thành công. '
                f'Chào mừng {username} quay trở lại!'
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

        messages.error(
            request,
            "Đăng nhập thất bại. "
            "Tên đăng nhập hoặc mật khẩu không đúng."
        )

        return render(
            request,
            "store/login.html"
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

    messages.success(
        request,
        "Đăng xuất thành công."
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

    # =====================================================
    # GIỎ HÀNG TRỐNG
    # =====================================================

    if not items.exists():

        messages.warning(
            request,
            "Không thể đặt hàng. "
            "Giỏ hàng của bạn đang trống."
        )

        return redirect(
            "cart_detail"
        )

    total = sum(
        item.book.price * item.quantity
        for item in items
    )

    # =====================================================
    # XỬ LÝ ĐẶT HÀNG
    # =====================================================

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

        # =================================================
        # KIỂM TRA HỌ TÊN
        # =================================================

        if not full_name:

            messages.error(
                request,
                "Đặt hàng thất bại. "
                "Vui lòng nhập họ và tên người nhận."
            )

            return render(
                request,
                "store/checkout.html",
                {
                    "items": items,
                    "total": total,
                }
            )

        # =================================================
        # KIỂM TRA SỐ ĐIỆN THOẠI
        # =================================================

        if not phone:

            messages.error(
                request,
                "Đặt hàng thất bại. "
                "Vui lòng nhập số điện thoại."
            )

            return render(
                request,
                "store/checkout.html",
                {
                    "items": items,
                    "total": total,
                    "full_name": full_name,
                    "phone": phone,
                    "address": address,
                    "payment_method": payment_method,
                    "note": note,
                }
            )


        # Số điện thoại phải đúng định dạng số điện thoại Việt Nam
        import re

        phone_pattern = r"^0[35789][0-9]{8}$"

        if not re.fullmatch(
            phone_pattern,
            phone
        ):

            messages.error(
                request,
                "Đặt hàng thất bại. "
                "Số điện thoại phải gồm 10 chữ số, "
                "bắt đầu bằng 0 và đúng định dạng số điện thoại Việt Nam. "
                "Ví dụ: 0912345678."
            )

            return render(
                request,
                "store/checkout.html",
                {
                    "items": items,
                    "total": total,
                    "full_name": full_name,
                    "phone": phone,
                    "address": address,
                    "payment_method": payment_method,
                    "note": note,
                }
            )

        # =================================================
        # KIỂM TRA ĐỊA CHỈ
        # =================================================

        if not address:

            messages.error(
                request,
                "Đặt hàng thất bại. "
                "Vui lòng nhập địa chỉ nhận hàng."
            )

            return render(
                request,
                "store/checkout.html",
                {
                    "items": items,
                    "total": total,
                }
            )

        # =================================================
        # KIỂM TRA PHƯƠNG THỨC THANH TOÁN
        # =================================================

        valid_payment_methods = [
            "cod",
            "bank",
            "momo",
        ]

        if payment_method not in valid_payment_methods:

            messages.error(
                request,
                "Đặt hàng thất bại. "
                "Phương thức thanh toán không hợp lệ."
            )

            return render(
                request,
                "store/checkout.html",
                {
                    "items": items,
                    "total": total,
                }
            )

        # =================================================
        # KIỂM TRA TỒN KHO
        # =================================================

        for item in items:

            if item.book.stock <= 0:

                messages.error(
                    request,
                    f'Đặt hàng thất bại. '
                    f'Sách "{item.book.title}" đã hết hàng.'
                )

                return render(
                    request,
                    "store/checkout.html",
                    {
                        "items": items,
                        "total": total,
                    }
                )

            if item.quantity > item.book.stock:

                messages.error(
                    request,
                    f'Đặt hàng thất bại. '
                    f'Sách "{item.book.title}" '
                    f'không đủ số lượng trong kho. '
                    f'Hiện chỉ còn {item.book.stock} cuốn.'
                )

                return render(
                    request,
                    "store/checkout.html",
                    {
                        "items": items,
                        "total": total,
                    }
                )

        # =================================================
        # TẠO ĐƠN HÀNG
        # =================================================

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

        # =================================================
        # TẠO CHI TIẾT ĐƠN HÀNG
        # =================================================

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

        # =================================================
        # XÓA GIỎ HÀNG
        # =================================================

        items.delete()

        messages.success(
            request,
            f"Đặt hàng thành công! "
            f"Mã đơn hàng của bạn là #{order.id}."
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


# =========================================================
# DANH SÁCH ĐƠN HÀNG
# =========================================================

@login_required(
    login_url="/login/"
)
def my_orders(request):

    orders = (
        request.user.orders
        .prefetch_related(
            "items__book"
        )
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


# =========================================================
# SÁCH BÁN CHẠY
# =========================================================

def best_sellers(request):

    books = (
        Book.objects
        .filter(
            is_active=True,
            order_items__order__status__in=[
                "pending",
                "confirmed",
                "shipping",
                "completed",
            ]
        )
        .annotate(
            total_sold=Sum(
                "order_items__quantity"
            )
        )
        .order_by(
            "-total_sold",
            "-created_at"
        )
    )

    context = {
        "books": books,
    }

    return render(
        request,
        "store/best_sellers.html",
        context
    )


# =========================================================
# KHUYẾN MÃI
# =========================================================

def promotions(request):

    books = (
        Book.objects
        .filter(
            is_active=True,
            original_price__isnull=False,
            original_price__gt=models.F(
                "price"
            )
        )
        .order_by(
            "-created_at"
        )
    )

    return render(
        request,
        "store/promotions.html",
        {
            "books": books,
        }
    )

# =========================================================
# THỐNG KÊ BÁN HÀNG
# =========================================================

def statistics_view(request):

    # =====================================================
    # KIỂM TRA QUYỀN QUẢN TRỊ
    # =====================================================

    if not request.user.is_authenticated:

        messages.error(
            request,
            "Bạn cần đăng nhập để truy cập trang thống kê."
        )

        return redirect("login")

    if not request.user.is_staff:

        messages.error(
            request,
            "Truy cập trang thống kê thất bại. "
            "Bạn không có quyền quản trị."
        )

        return redirect("home")

    # =====================================================
    # 1. TỔNG QUAN
    # =====================================================

    total_books = (
        Book.objects
        .filter(
            is_active=True
        )
        .count()
    )

    total_customers = (
        User.objects
        .filter(
            is_staff=False,
            is_superuser=False
        )
        .count()
    )

    total_orders = (
        Order.objects
        .count()
    )

    # Chỉ tính doanh thu từ đơn hàng đã hoàn thành
    total_revenue = (
        Order.objects
        .filter(
            status="completed"
        )
        .aggregate(
            total=Sum("total_amount")
        )["total"]
        or Decimal("0")
    )

    # =====================================================
    # 2. ĐƠN HÀNG THEO TRẠNG THÁI
    # =====================================================

    pending_orders = (
        Order.objects
        .filter(
            status="pending"
        )
        .count()
    )

    confirmed_orders = (
        Order.objects
        .filter(
            status="confirmed"
        )
        .count()
    )

    shipping_orders = (
        Order.objects
        .filter(
            status="shipping"
        )
        .count()
    )

    completed_orders = (
        Order.objects
        .filter(
            status="completed"
        )
        .count()
    )

    cancelled_orders = (
        Order.objects
        .filter(
            status="cancelled"
        )
        .count()
    )

    # =====================================================
    # 3. TỔNG SỐ SÁCH ĐÃ BÁN
    # =====================================================

    total_books_sold = (
        OrderItem.objects
        .filter(
            order__status="completed"
        )
        .aggregate(
            total=Sum("quantity")
        )["total"]
        or 0
    )

    # =====================================================
    # 4. TOP 5 SÁCH BÁN CHẠY
    # =====================================================

    best_selling_books = (
        Book.objects
        .filter(
            is_active=True,
            order_items__order__status="completed"
        )
        .annotate(
            total_sold=Sum(
                "order_items__quantity",
                filter=models.Q(
                    order_items__order__status="completed"
                )
            )
        )
        .filter(
            total_sold__gt=0
        )
        .order_by(
            "-total_sold",
            "title"
        )[:5]
    )

    # =====================================================
    # 5. BIỂU THỨC TÍNH DOANH THU ORDER ITEM
    #
    # Doanh thu = số lượng x giá bán
    # =====================================================

    revenue_expression = ExpressionWrapper(
        F("quantity") * F("price"),
        output_field=DecimalField(
            max_digits=15,
            decimal_places=2
        )
    )

    # =====================================================
    # 6. DOANH THU THEO SÁCH
    # =====================================================

    book_revenue = (
        OrderItem.objects
        .filter(
            order__status="completed"
        )
        .values(
            "book__title"
        )
        .annotate(
            total_quantity=Sum(
                "quantity"
            ),
            total_revenue=Sum(
                revenue_expression
            )
        )
        .order_by(
            "-total_revenue",
            "book__title"
        )[:10]
    )

    # =====================================================
    # 7. DOANH THU THEO DANH MỤC
    #
    # OrderItem
    #     ↓
    # Book
    #     ↓
    # Category
    # =====================================================

    category_revenue = (
        OrderItem.objects
        .filter(
            order__status="completed"
        )
        .values(
            "book__category__name"
        )
        .annotate(
            total_quantity=Sum(
                "quantity"
            ),
            total_revenue=Sum(
                revenue_expression
            )
        )
        .order_by(
            "-total_revenue",
            "book__category__name"
        )
    )

    # =====================================================
    # 8. DỮ LIỆU BIỂU ĐỒ TRÒN
    #    DOANH THU THEO DANH MỤC
    # =====================================================

    category_chart_labels = []
    category_chart_data = []

    for item in category_revenue:

        category_name = (
            item["book__category__name"]
            or "Chưa phân loại"
        )

        revenue = (
            item["total_revenue"]
            or Decimal("0")
        )

        category_chart_labels.append(
            category_name
        )

        category_chart_data.append(
            float(revenue)
        )

    # =====================================================
    # 9. DOANH THU THEO NGÀY
    #
    # Chỉ tính những đơn hàng:
    # status = completed
    # =====================================================

    daily_revenue_query = (
        Order.objects
        .filter(
            status="completed"
        )
        .annotate(
            day=TruncDate(
                "created_at"
            )
        )
        .values(
            "day"
        )
        .annotate(
            revenue=Sum(
                "total_amount"
            ),
            order_count=Count(
                "id"
            )
        )
        .order_by(
            "day"
        )
    )

    # =====================================================
    # DỮ LIỆU BIỂU ĐỒ CỘT
    # =====================================================

    revenue_chart_labels = []
    revenue_chart_data = []
    revenue_chart_orders = []

    for item in daily_revenue_query:

        day = item["day"]

        if day:

            revenue_chart_labels.append(
                day.strftime("%d/%m/%Y")
            )

        else:

            revenue_chart_labels.append(
                "Không xác định"
            )

        revenue_chart_data.append(
            float(
                item["revenue"] or 0
            )
        )

        revenue_chart_orders.append(
            item["order_count"] or 0
        )

    # =====================================================
    # 10. TỒN KHO
    # =====================================================

    total_stock = (
        Book.objects
        .filter(
            is_active=True
        )
        .aggregate(
            total=Sum("stock")
        )["total"]
        or 0
    )

    out_of_stock = (
        Book.objects
        .filter(
            is_active=True,
            stock=0
        )
        .count()
    )

    low_stock = (
        Book.objects
        .filter(
            is_active=True,
            stock__gt=0,
            stock__lte=10
        )
        .count()
    )

    # =====================================================
    # 11. ĐÁNH GIÁ
    # =====================================================

    total_reviews = (
        Review.objects
        .filter(
            book__is_active=True
        )
        .count()
    )

    # =====================================================
    # 12. CONTEXT
    #
    # QUAN TRỌNG:
    # Truyền LIST trực tiếp.
    #
    # KHÔNG json.dumps() ở đây.
    # statistics.html sẽ dùng json_script.
    # =====================================================

    context = {

        # -------------------------------------------------
        # TỔNG QUAN
        # -------------------------------------------------

        "total_books": total_books,

        "total_customers": total_customers,

        "total_orders": total_orders,

        "total_revenue": total_revenue,

        "total_books_sold": total_books_sold,


        # -------------------------------------------------
        # ĐƠN HÀNG
        # -------------------------------------------------

        "pending_orders": pending_orders,

        "confirmed_orders": confirmed_orders,

        "shipping_orders": shipping_orders,

        "completed_orders": completed_orders,

        "cancelled_orders": cancelled_orders,


        # -------------------------------------------------
        # SÁCH BÁN CHẠY
        # -------------------------------------------------

        "best_selling_books": best_selling_books,


        # -------------------------------------------------
        # DOANH THU THEO SÁCH
        # -------------------------------------------------

        "book_revenue": book_revenue,


        # -------------------------------------------------
        # DOANH THU THEO DANH MỤC
        # -------------------------------------------------

        "category_revenue": category_revenue,


        # -------------------------------------------------
        # BIỂU ĐỒ DOANH THU THEO NGÀY
        # -------------------------------------------------

        "revenue_chart_labels": revenue_chart_labels,

        "revenue_chart_data": revenue_chart_data,

        "revenue_chart_orders": revenue_chart_orders,


        # -------------------------------------------------
        # BIỂU ĐỒ DOANH THU THEO DANH MỤC
        # -------------------------------------------------

        "category_chart_labels": category_chart_labels,

        "category_chart_data": category_chart_data,


        # -------------------------------------------------
        # KHO
        # -------------------------------------------------

        "total_stock": total_stock,

        "out_of_stock": out_of_stock,

        "low_stock": low_stock,


        # -------------------------------------------------
        # ĐÁNH GIÁ
        # -------------------------------------------------

        "total_reviews": total_reviews,
    }

    return render(
        request,
        "admin/store/statistics.html",
        context
    )

# =========================================================
# ALPHABOT AI - CHATBOT TÌM KIẾM SÁCH
# =========================================================

from django.http import JsonResponse


def alphabot_chat(request):

    # =====================================================
    # KIỂM TRA REQUEST
    # =====================================================

    if request.method != "POST":
        return JsonResponse(
            {
                "success": False,
                "message": "Phương thức yêu cầu không hợp lệ."
            },
            status=400
        )

    # =====================================================
    # LẤY CÂU HỎI
    # =====================================================

    try:
        data = json.loads(request.body)
        question = data.get("question", "").strip()

    except (json.JSONDecodeError, TypeError):
        return JsonResponse(
            {
                "success": False,
                "message": "Không thể đọc câu hỏi."
            },
            status=400
        )

    if not question:
        return JsonResponse(
            {
                "success": False,
                "message": "Vui lòng nhập câu hỏi."
            },
            status=400
        )

    # =====================================================
    # QUERY SÁCH TỪ POSTGRESQL
    # =====================================================

    books = (
        Book.objects
        .filter(is_active=True)
        .select_related(
            "category",
            "publisher"
        )
        .prefetch_related(
            "authors"
        )
    )

    question_lower = question.lower().strip()

    # =====================================================
    # NHẬN DIỆN ĐIỀU KIỆN
    # =====================================================

    is_best_seller = any(
        keyword in question_lower
        for keyword in [
            "bán chạy",
            "bán chạy nhất",
            "best seller",
            "best sellers",
            "bestseller",
            "nhiều người mua",
            "được mua nhiều"
        ]
    )

    is_good_book = any(
        keyword in question_lower
        for keyword in [
            "sách hay",
            "sách tốt",
            "sách đáng đọc",
            "sách nên đọc",
            "gợi ý sách",
            "sách nào hay",
            "recommend"
        ]
    )

    # =====================================================
    # GIỚI HẠN GIÁ
    # =====================================================

    max_price = None
    min_price = None

    max_price_match = re.search(
        r"(?:dưới|<|không quá|tối đa|ít hơn|nhỏ hơn)"
        r"\s*"
        r"(\d+(?:[.,]\d+)?)"
        r"\s*"
        r"(k|nghìn|ngàn|000|đ|₫)?",
        question_lower
    )

    if max_price_match:
        try:
            value = float(
                max_price_match.group(1).replace(",", ".")
            )

            unit = max_price_match.group(2) or ""

            if unit == "k":
                value *= 1000

            elif unit in ["nghìn", "ngàn"]:
                value *= 1000

            elif unit == "000":
                value *= 1000

            elif unit in ["đ", "₫"]:
                pass

            elif value < 1000:
                value *= 1000

            max_price = int(value)

        except (ValueError, TypeError):
            max_price = None

    min_price_match = re.search(
        r"(?:trên|>|từ|ít nhất|tối thiểu)"
        r"\s*"
        r"(\d+(?:[.,]\d+)?)"
        r"\s*"
        r"(k|nghìn|ngàn|000|đ|₫)?",
        question_lower
    )

    if min_price_match:
        try:
            value = float(
                min_price_match.group(1).replace(",", ".")
            )

            unit = min_price_match.group(2) or ""

            if unit == "k":
                value *= 1000

            elif unit in ["nghìn", "ngàn"]:
                value *= 1000

            elif unit == "000":
                value *= 1000

            elif unit in ["đ", "₫"]:
                pass

            elif value < 1000:
                value *= 1000

            min_price = int(value)

        except (ValueError, TypeError):
            min_price = None

    # =====================================================
    # XÁC ĐỊNH CHỦ ĐỀ
    # =====================================================

    topic_keywords = []

    if any(
        keyword in question_lower
        for keyword in [
            "tiếng anh",
            "tieng anh",
            "học anh",
            "hoc anh",
            "ngoại ngữ",
            "ngoai ngu",
            "english",
            "ielts",
            "toeic",
            "grammar",
            "từ vựng",
            "tu vung"
        ]
    ):
        topic_keywords = [
            "tiếng anh",
            "ngoại ngữ",
            "english",
            "ielts",
            "toeic",
            "grammar",
            "từ vựng",
            "học tiếng anh"
        ]

    elif any(
        keyword in question_lower
        for keyword in [
            "lịch sử",
            "lich su",
            "lịch sử việt nam",
            "lich su viet nam",
            "history"
        ]
    ):
        topic_keywords = [
            "lịch sử",
            "lich su",
            "history"
        ]

    elif any(
        keyword in question_lower
        for keyword in [
            "kinh doanh",
            "business",
            "khởi nghiệp",
            "khoi nghiep",
            "startup"
        ]
    ):
        topic_keywords = [
            "kinh doanh",
            "business",
            "khởi nghiệp",
            "startup"
        ]

    elif any(
        keyword in question_lower
        for keyword in [
            "công nghệ",
            "cong nghe",
            "lập trình",
            "lap trinh",
            "python",
            "java",
            "django",
            "programming",
            "công nghệ thông tin"
        ]
    ):
        topic_keywords = [
            "công nghệ",
            "lập trình",
            "python",
            "java",
            "django",
            "programming",
            "công nghệ thông tin"
        ]

    elif any(
        keyword in question_lower
        for keyword in [
            "tâm lý",
            "tam ly",
            "psychology"
        ]
    ):
        topic_keywords = [
            "tâm lý",
            "psychology"
        ]

    # =====================================================
    # LỌC THEO CHỦ ĐỀ
    # =====================================================

    if topic_keywords:

        topic_query = models.Q()

        for keyword in topic_keywords:

            topic_query |= (
                models.Q(title__icontains=keyword)
                |
                models.Q(description__icontains=keyword)
                |
                models.Q(category__name__icontains=keyword)
                |
                models.Q(authors__name__icontains=keyword)
            )

        books = (
            books
            .filter(topic_query)
            .distinct()
        )

    # =====================================================
    # LỌC THEO GIÁ
    # =====================================================

    if max_price is not None:
        books = books.filter(price__lte=max_price)

    if min_price is not None:
        books = books.filter(price__gte=min_price)

    # =====================================================
    # LỌC CÒN HÀNG
    # =====================================================

    wants_in_stock = any(
        keyword in question_lower
        for keyword in [
            "còn hàng",
            "con hang",
            "có hàng",
            "co hang",
            "trong kho"
        ]
    )

    if wants_in_stock:
        books = books.filter(stock__gt=0)

    # =====================================================
    # SÁCH BÁN CHẠY
    # =====================================================

    if is_best_seller:

        books = (
            books
            .annotate(
                total_sold=Sum(
                    "order_items__quantity",
                    filter=models.Q(
                        order_items__order__status__in=[
                            "confirmed",
                            "shipping",
                            "completed"
                        ]
                    )
                )
            )
            .filter(total_sold__gt=0)
            .order_by(
                "-total_sold",
                "-created_at"
            )[:5]
        )

    # =====================================================
    # SÁCH HAY
    # =====================================================

    elif is_good_book:

        books = (
            books
            .annotate(
                average_rating=Avg(
                    "reviews__rating"
                ),
                review_count=Count(
                    "reviews"
                )
            )
            .order_by(
                "-average_rating",
                "-review_count",
                "-created_at"
            )[:5]
        )

    # =====================================================
    # TÌM KIẾM TỰ DO
    # =====================================================

    elif not topic_keywords:

        search_words = [
            word.strip()
            for word in re.split(
                r"\s+",
                question_lower
            )
            if len(word.strip()) >= 2
        ]

        ignored_words = {
            "cho",
            "tôi",
            "toi",
            "mình",
            "minh",
            "một",
            "mot",
            "số",
            "so",
            "cuốn",
            "cuon",
            "quyển",
            "quyen",
            "sách",
            "sach",
            "tìm",
            "tim",
            "giúp",
            "giup",
            "về",
            "ve",
            "có",
            "co",
            "nào",
            "nao",
            "hãy",
            "hay",
            "xin",
            "với",
            "voi",
            "đang",
            "dang",
            "phù",
            "phu",
            "hợp",
            "hop",
            "mua",
            "giá",
            "gia",
            "khoảng",
            "khoang",
            "dưới",
            "duoi",
            "trên",
            "tren",
            "không",
            "khong",
            "đồng",
            "dong",
            "nghìn",
            "nghin",
            "ngàn",
            "ngan",
            "k"
        }

        search_words = [
            word
            for word in search_words
            if word not in ignored_words
            and not word.isdigit()
        ]

        if search_words:

            search_query = models.Q()

            for word in search_words:

                search_query |= (
                    models.Q(
                        title__icontains=word
                    )
                    |
                    models.Q(
                        description__icontains=word
                    )
                    |
                    models.Q(
                        authors__name__icontains=word
                    )
                    |
                    models.Q(
                        category__name__icontains=word
                    )
                )

            books = (
                books
                .filter(search_query)
                .distinct()
                .order_by("-created_at")[:10]
            )

    # =====================================================
    # CHUẨN BỊ DỮ LIỆU CHO GEMINI
    # =====================================================

    book_list = list(books[:10])

    book_data = []

    for book in book_list:

        authors = ", ".join(
            author.name
            for author in book.authors.all()
        )

        book_data.append(
            {
                "id": book.id,
                "title": book.title,
                "price": float(book.price),
                "stock": book.stock,
                "category": (
                    book.category.name
                    if book.category
                    else ""
                ),
                "authors": authors,
                "url": f"/books/{book.id}/"
            }
        )

    # =====================================================
    # KHÔNG CÓ SÁCH
    # =====================================================

    if not book_data:

        return JsonResponse(
            {
                "success": True,
                "type": "text",
                "message": (
                    "😔 Xin lỗi, mình chưa tìm thấy "
                    "cuốn sách phù hợp với yêu cầu của bạn.\n\n"
                    "Bạn có thể thử thay đổi chủ đề "
                    "hoặc mức giá nhé!"
                )
            }
        )

    # =====================================================
    # GỌI GEMINI
    # =====================================================

    try:

        client = genai.Client()

        chat = client.chats.create(
            model="gemini-3.6-flash"
        )

        prompt = f"""
Bạn là AlphaBot AI, trợ lý bán sách của website Alpha Books.

Khách hàng hỏi:
"{question}"

Dưới đây là DANH SÁCH SÁCH THẬT được lấy trực tiếp từ
cơ sở dữ liệu PostgreSQL của website:

{json.dumps(book_data, ensure_ascii=False, indent=2)}

Nhiệm vụ:

1. Trả lời khách hàng bằng tiếng Việt.
2. Tự nhiên, thân thiện, ngắn gọn.
3. Chỉ sử dụng những cuốn sách có trong danh sách dữ liệu.
4. Tuyệt đối không được tự tạo tên sách, tác giả,
   giá hoặc số lượng tồn kho.
5. Nếu khách hỏi gợi ý sách, hãy giải thích ngắn gọn
   tại sao những cuốn sách đó phù hợp.
6. Nếu có giá hoặc tồn kho trong dữ liệu thì có thể
   đề cập chính xác.
7. Không nói rằng bạn đã truy cập PostgreSQL.
8. Không trả về JSON.
9. Không đưa link nếu không cần thiết.
10. Không đề cập đến API hoặc kỹ thuật phía sau hệ thống.

Hãy trả lời trực tiếp khách hàng.
"""

        response = chat.send_message(
            message=prompt
        )

        message = response.text.strip()

        # =================================================
        # TRẢ KẾT QUẢ
        # =================================================

        return JsonResponse(
            {
                "success": True,
                "type": "recommendation",
                "message": message,
                "books": book_data
            }
        )

    except Exception as e:

        print("ALPHABOT GEMINI ERROR:", e)

        # =================================================
        # FALLBACK
        # =================================================

        return JsonResponse(
            {
                "success": True,
                "type": "recommendation",
                "message": (
                    "🤖 Mình tìm thấy một số cuốn sách "
                    "có thể phù hợp với yêu cầu của bạn:"
                ),
                "books": book_data
            }
        )