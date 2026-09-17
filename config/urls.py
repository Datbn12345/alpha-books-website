"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from store import admin_views


urlpatterns = [

    # =====================================================
    # THỐNG KÊ BÁN HÀNG
    # =====================================================

    path(
        "admin/statistics/",
        admin_views.statistics_view,
        name="statistics"
    ),


    # =====================================================
    # TRANG QUẢN TRỊ DJANGO
    # =====================================================

    path(
        "admin/",
        admin.site.urls
    ),


    # =====================================================
    # WEBSITE BÁN SÁCH
    # =====================================================

    path(
        "",
        include("store.urls")
    ),
]


# =========================================================
# MEDIA
# =========================================================

urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT
)