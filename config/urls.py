from django.urls import path,include
from assets import views

urlpatterns = [
    
path("accounts/", include("accounts.urls")),

    # LANDING / AUTH 
path('', views.landing_page, name='landing'),
path('about/', views.about, name='about'),
path('contact/', views.contact, name='contact'),
path('login/', views.login_page, name='login'),
path('register/', views.register, name='register'),
path('logout/', views.logout_page, name='logout'),

    # DASHBOARDS 
path('dashboard/', views.dashboard, name='dashboard'),
path('user-dashboard/', views.user_dashboard, name='user_dashboard'),

    # PROFILE 
path('complete-profile/', views.complete_profile, name='complete_profile'),
path('change-password/', views.change_password, name='change_password'),

    # CATEGORIES 
path('categories/', views.categories_page, name='categories'),
path('edit-category/<int:pk>/', views.edit_category, name='edit_category'),
path('categories/delete/<int:pk>/', views.delete_category, name='category_delete'),

    # SUPPLIERS 
path('suppliers/', views.suppliers_page, name='suppliers'),
path('edit-supplier/<int:pk>/', views.edit_supplier, name='edit_supplier'),
path('suppliers/delete/<int:pk>/', views.delete_supplier, name='supplier_delete'),

    # LOCATIONS 
path('locations/', views.locations_page, name='locations'),
path('edit-location/<int:pk>/', views.edit_location, name='edit_location'),
path('locations/delete/<int:pk>/', views.delete_location, name='location_delete'),

    # ITEMS
path('items/', views.items_page, name='items'),
path('edit-item/<int:pk>/', views.edit_item, name='edit_item'),
path('items/delete/<int:pk>/', views.delete_item, name='delete_item'),

    # ORDERS 
path('place-order/', views.place_order, name='place_order'),
path('orders/', views.all_orders, name='orders'),
path('update-order/<int:order_id>/', views.update_order_status, name='update_order_status'),

    # ADMIN TOOLS 
path('activity-logs/', views.activity_logs, name='activity_logs'),
path('send-announcement/', views.send_announcement, name='send_announcement'),
path('announcement/', views.user_announcement, name='user_announcement'),

    # SETTINGS 
path('settings/', views.settings, name='settings'),
path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
path('add-user/', views.add_user, name='add_user'),
path('user/edit/<int:user_id>/', views.edit_user, name='edit_user'),

    # REPORTS 
path('sales-insights/', views.sales_insights, name='sales_insights'),
path('sales-report/print/', views.sales_report_print, name='sales_report_print'),
]