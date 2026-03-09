from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('current/', views.CurrentUserView.as_view(), name='current-user'),
    path('challenge/', views.SignatureView.as_view()),
    path('account_nft_update/', views.account_nft_update, name='account_nft_update'),
    path('update-profile/', views.UpdateProfileView.as_view(), name='LoginAdminView'),
    path('my-rank/', views.UserRankView.as_view(), name='user-rank'),
    path('verify-referral-code/', views.VerifyReferralCodeView.as_view(), name='verify-referral-code'),
    # Food inventory endpoints
    path('food/items/', views.FoodItemListView.as_view(), name='food-items'),
    path('food/inventory/', views.FoodInventoryView.as_view(), name='food-inventory'),
    # Lootbox endpoints
    path('lootbox/available/', views.LootBoxListView.as_view(), name='lootbox-list'),
    path('lootbox/<uuid:loot_box_id>/purchase/', views.LootBoxPurchaseView.as_view(), name='lootbox-purchase'),
    path('lootbox/<uuid:loot_box_id>/open/', views.LootBoxOpenView.as_view(), name='lootbox-open'),
    path('lootbox/inventory/', views.LootBoxInventoryView.as_view(), name='lootbox-inventory'),
    path('lootbox/my-purchases/', views.LootBoxPurchaseHistoryView.as_view(), name='lootbox-purchase-history'),
    path('lootbox/my-rewards/', views.LootBoxRewardHistoryView.as_view(), name='lootbox-reward-history'),

]
