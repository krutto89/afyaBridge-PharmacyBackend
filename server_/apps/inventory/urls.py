
from django.urls import path
from . import views
 
urlpatterns = [
    path('',                    views.DrugListCreateView.as_view(),  name='drug-list'),
    path('dashboard/',           views.InventoryDashboardView.as_view(), name='inv-dashboard'),
    path('low-stock/',           views.LowStockView.as_view(),       name='low-stock'),
    path('expiring/',            views.ExpiringDrugsView.as_view(),  name='expiring'),
    path('<uuid:drug_id>/',      views.DrugDetailView.as_view(),     name='drug-detail'),
    path('<uuid:drug_id>/restock/', views.RestockView.as_view(),     name='drug-restock'),
]
 

