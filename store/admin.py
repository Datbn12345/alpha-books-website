from django.contrib import admin

from .models import (
    Category,
    Author,
    Publisher,
    Book,
    Cart,
    CartItem,
    Order,
    OrderItem,
    Review,
)


# =========================================================
# DANH MỤC
# =========================================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
    )

    ordering = (
        "name",
    )


# =========================================================
# TÁC GIẢ
# =========================================================

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
    )

    ordering = (
        "name",
    )


# =========================================================
# NHÀ XUẤT BẢN
# =========================================================

@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "phone",
        "email",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
        "phone",
        "email",
    )

    ordering = (
        "name",
    )


# =========================================================
# SÁCH
# =========================================================

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "isbn",
        "category",
        "publisher",
        "price",
        "stock",
        "is_active",
        "created_at",
    )

    list_filter = (
        "category",
        "publisher",
        "is_active",
        "created_at",
    )

    search_fields = (
        "title",
        "isbn",
        "authors__name",
    )

    filter_horizontal = (
        "authors",
    )

    ordering = (
        "-created_at",
    )

    list_per_page = 20


# =========================================================
# CHI TIẾT GIỎ HÀNG
# =========================================================

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):

    list_display = (
        "cart",
        "book",
        "quantity",
    )

    search_fields = (
        "cart__user__username",
        "book__title",
    )


# =========================================================
# GIỎ HÀNG
# =========================================================

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "user__username",
        "user__email",
    )

    ordering = (
        "-updated_at",
    )


# =========================================================
# CHI TIẾT ĐƠN HÀNG
# =========================================================

class OrderItemInline(admin.TabularInline):

    model = OrderItem

    extra = 0

    readonly_fields = (
        "book",
        "quantity",
        "price",
        "subtotal",
    )

    can_delete = False


# =========================================================
# ĐƠN HÀNG
# =========================================================

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "full_name",
        "phone",
        "payment_method",
        "status",
        "total_amount",
        "created_at",
    )

    list_filter = (
        "status",
        "payment_method",
        "created_at",
    )

    search_fields = (
        "id",
        "user__username",
        "user__email",
        "full_name",
        "phone",
    )

    readonly_fields = (
        "user",
        "created_at",
        "updated_at",
        "total_amount",
    )

    inlines = (
        OrderItemInline,
    )

    ordering = (
        "-created_at",
    )

    list_per_page = 20


# =========================================================
# ĐÁNH GIÁ SÁCH
# =========================================================

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "book",
        "rating",
        "created_at",
    )

    list_filter = (
        "rating",
        "created_at",
    )

    search_fields = (
        "user__username",
        "book__title",
        "comment",
    )

    ordering = (
        "-created_at",
    )