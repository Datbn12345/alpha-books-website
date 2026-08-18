from django.urls import path
from . import views


urlpatterns = [

    # =====================================================
    # TRANG CHỦ
    # =====================================================

    path(
        "",
        views.home,
        name="home"
    ),


    # =====================================================
    # SÁCH
    # =====================================================

    path(
        "books/",
        views.book_list,
        name="book_list"
    ),

    path(
        "books/<int:book_id>/",
        views.book_detail,
        name="book_detail"
    ),


    # =====================================================
    # GIỎ HÀNG
    # =====================================================

    path(
        "cart/",
        views.cart_detail,
        name="cart_detail"
    ),


    # =====================================================
    # TÀI KHOẢN
    # =====================================================

    path(
        "register/",
        views.register,
        name="register"
    ),

    path(
        "login/",
        views.login_view,
        name="login"
    ),

    path(
        "logout/",
        views.logout_view,
        name="logout"
    ),


    # =====================================================
    # ĐƠN HÀNG
    # =====================================================

    path(
        "my-orders/",
        views.my_orders,
        name="my_orders"
    ),

    path(
        "order/<int:order_id>/",
        views.order_detail,
        name="order_detail"
    ),

]