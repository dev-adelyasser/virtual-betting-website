from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    #path('', include('apps.accounts.urls')),
    path('wallet/', include('apps.wallet.urls')),     
    path('bets/', include('apps.bets.urls')),        
]
