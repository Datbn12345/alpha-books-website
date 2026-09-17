from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import (
    Sum,
    Count,
    F,
    DecimalField,
    ExpressionWrapper,
)
from django.db.models.functions import TruncDate
from django.shortcuts import render

from .models import (
    Book,
    Order,
    OrderItem,
)


# =========================================================
# THỐNG KÊ BÁN HÀNG
# =========================================================

@staff_member_required
def statistics_view(request):

    # =====================================================
    # 1. THỐNG KÊ TỔNG QUAN
    # =====================================================

    total_books = Book.objects.filter(
        is_active=True
    ).count()

    total_customers = User.objects.filter(
        is_staff=False,
        is_superuser=False
    ).count()

    total_orders = Order.objects.count()

    # Chỉ tính doanh thu từ đơn hàng đã hoàn thành
    total_revenue = (
        Order.objects
        .filter(status="completed")
        .aggregate(
            total=Sum("total_amount")
        )["total"] or 0
    )


    # =====================================================
    # 2. THỐNG KÊ ĐƠN HÀNG THEO TRẠNG THÁI
    # =====================================================

    pending_orders = Order.objects.filter(
        status="pending"
    ).count()

    confirmed_orders = Order.objects.filter(
        status="confirmed"
    ).count()

    shipping_orders = Order.objects.filter(
        status="shipping"
    ).count()

    completed_orders = Order.objects.filter(
        status="completed"
    ).count()

    cancelled_orders = Order.objects.filter(
        status="cancelled"
    ).count()


    # =====================================================
    # 3. TOP 5 SÁCH BÁN CHẠY
    # =====================================================

    best_selling_books = (
        Book.objects
        .filter(
            is_active=True,
            order_items__order__status="completed"
        )
        .annotate(
            total_sold=Sum(
                "order_items__quantity"
            )
        )
        .order_by(
            "-total_sold",
            "title"
        )[:5]
    )


    # =====================================================
    # 4. DOANH THU THEO SÁCH
    # =====================================================

    revenue_expression = ExpressionWrapper(
        F("quantity") * F("price"),
        output_field=DecimalField(
            max_digits=15,
            decimal_places=2
        )
    )

    book_revenue = (
        OrderItem.objects
        .filter(
            order__status="completed"
        )
        .values(
            "book__title"
        )
        .annotate(
            total_quantity=Sum("quantity"),
            total_revenue=Sum(
                revenue_expression
            )
        )
        .order_by(
            "-total_revenue"
        )[:10]
    )


    # =====================================================
    # 5. DOANH THU THEO DANH MỤC
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
            total_quantity=Sum("quantity"),
            total_revenue=Sum(
                revenue_expression
            )
        )
        .order_by(
            "-total_revenue"
        )
    )


    # =====================================================
    # 6. DOANH THU THEO NGÀY
    # =====================================================

    daily_revenue = (
        Order.objects
        .filter(
            status="completed"
        )
        .annotate(
            day=TruncDate("created_at")
        )
        .values(
            "day"
        )
        .annotate(
            revenue=Sum("total_amount"),
            order_count=Count("id")
        )
        .order_by(
            "day"
        )
    )


    # =====================================================
    # 7. CHUẨN BỊ DỮ LIỆU BIỂU ĐỒ DOANH THU
    # =====================================================

    revenue_chart_labels = []
    revenue_chart_data = []
    revenue_chart_orders = []

    for item in daily_revenue:

        if item["day"]:
            revenue_chart_labels.append(
                item["day"].strftime("%d/%m/%Y")
            )

            revenue_chart_data.append(
                float(item["revenue"] or 0)
            )

            revenue_chart_orders.append(
                item["order_count"] or 0
            )


    # =====================================================
    # 8. CHUẨN BỊ DỮ LIỆU BIỂU ĐỒ DANH MỤC
    # =====================================================

    category_chart_labels = []
    category_chart_data = []

    for item in category_revenue:

        category_name = (
            item["book__category__name"]
            or "Chưa phân loại"
        )

        category_chart_labels.append(
            category_name
        )

        category_chart_data.append(
            float(item["total_revenue"] or 0)
        )


    # =====================================================
    # 9. THỐNG KÊ TỒN KHO
    # =====================================================

    total_stock = (
        Book.objects
        .filter(is_active=True)
        .aggregate(
            total=Sum("stock")
        )["total"] or 0
    )

    out_of_stock = Book.objects.filter(
        is_active=True,
        stock=0
    ).count()

    low_stock = Book.objects.filter(
        is_active=True,
        stock__gt=0,
        stock__lte=10
    ).count()


    # =====================================================
    # 10. THỐNG KÊ ĐÁNH GIÁ
    # =====================================================

    total_reviews = (
        Book.objects
        .filter(
            reviews__isnull=False
        )
        .aggregate(
            total=Count("reviews")
        )["total"] or 0
    )


    # =====================================================
    # 11. CONTEXT
    # =====================================================

    context = {

        # -------------------------------------------------
        # Tổng quan
        # -------------------------------------------------

        "total_books": total_books,

        "total_customers": total_customers,

        "total_orders": total_orders,

        "total_revenue": total_revenue,


        # -------------------------------------------------
        # Đơn hàng
        # -------------------------------------------------

        "pending_orders": pending_orders,

        "confirmed_orders": confirmed_orders,

        "shipping_orders": shipping_orders,

        "completed_orders": completed_orders,

        "cancelled_orders": cancelled_orders,


        # -------------------------------------------------
        # Sách bán chạy
        # -------------------------------------------------

        "best_selling_books": best_selling_books,


        # -------------------------------------------------
        # Doanh thu
        # -------------------------------------------------

        "book_revenue": book_revenue,

        "category_revenue": category_revenue,


        # -------------------------------------------------
        # Biểu đồ doanh thu theo ngày
        # -------------------------------------------------

        "revenue_chart_labels": revenue_chart_labels,

        "revenue_chart_data": revenue_chart_data,

        "revenue_chart_orders": revenue_chart_orders,


        # -------------------------------------------------
        # Biểu đồ doanh thu theo danh mục
        # -------------------------------------------------

        "category_chart_labels": category_chart_labels,

        "category_chart_data": category_chart_data,


        # -------------------------------------------------
        # Kho
        # -------------------------------------------------

        "total_stock": total_stock,

        "out_of_stock": out_of_stock,

        "low_stock": low_stock,


        # -------------------------------------------------
        # Đánh giá
        # -------------------------------------------------

        "total_reviews": total_reviews,
    }


    # =====================================================
    # 12. HIỂN THỊ TRANG THỐNG KÊ
    # =====================================================

    return render(
        request,
        "admin/store/statistics.html",
        context
    )