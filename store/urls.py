from django.urls import path
from django.contrib.auth import views as auth_views

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
    # ĐÁNH GIÁ
    # =====================================================

    path(
        "books/<int:book_id>/review/",
        views.add_review,
        name="add_review"
    ),

    path(
        "books/<int:book_id>/review/delete/",
        views.delete_review,
        name="delete_review"
    ),

    # =====================================================
    # GIỎ HÀNG
    # =====================================================

    path(
        "cart/",
        views.cart_detail,
        name="cart_detail"
    ),

    path(
        "cart/update/<int:item_id>/",
        views.cart_update,
        name="cart_update"
    ),

    path(
        "cart/remove/<int:item_id>/",
        views.cart_remove,
        name="cart_remove"
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
    # QUÊN MẬT KHẨU
    # =====================================================

    path(
        "forgot-password/",
        auth_views.PasswordResetView.as_view(
            template_name="store/password_reset.html",
            email_template_name="store/password_reset_email.txt",
            subject_template_name="store/password_reset_subject.txt",
            success_url="/forgot-password/sent/"
        ),
        name="password_reset"
    ),

    path(
        "forgot-password/sent/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="store/password_reset_done.html"
        ),
        name="password_reset_done"
    ),

    path(
        "reset-password/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="store/password_reset_confirm.html",
            success_url="/reset-password/complete/"
        ),
        name="password_reset_confirm"
    ),

    path(
        "reset-password/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="store/password_reset_complete.html"
        ),
        name="password_reset_complete"
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

    path(
        "checkout/",
        views.checkout,
        name="checkout"
    ),

    # =====================================================
    # SÁCH BÁN CHẠY
    # =====================================================

    path(
        "best-sellers/",
        views.best_sellers,
        name="best_sellers"
    ),

    # =====================================================
    # KHUYẾN MÃI
    # =====================================================

    path(
        "promotions/",
        views.promotions,
        name="promotions"
    ),

    # =====================================================
    # THỐNG KÊ
    # =====================================================

    path(
        "admin/statistics/",
        views.statistics_view,
        name="statistics"
    ),
    # =====================================================
    # ALPHABOT AI
    # =====================================================
    path(
        "ai/chat/",
        views.alphabot_chat,
        name="alphabot_chat"
    ),
]