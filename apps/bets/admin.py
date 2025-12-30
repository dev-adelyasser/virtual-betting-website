from django.contrib import admin
from django.utils.html import format_html
from .models import Bet


@admin.register(Bet)  
class BetAdmin(admin.ModelAdmin):
    """
    Admin interface for managing bets
    """
    list_display = [
        'id', 
        'user_email', 
        'event_name', 
        'bet_type_display',
        'stake_display', 
        'odds', 
        'potential_payout_display',
        'status_badge',
        'placed_at'
    ]
    
    list_filter = [
        'status',
        'bet_type',
        'placed_at',
        'resolved_at',
    ]
    
    search_fields = [
        'user__email',
        'event__name',
        'event__team_a',
        'event__team_b',
    ]
    
    readonly_fields = [
        'placed_at', 
        'resolved_at', 
        'potential_payout',
        'ip_address'
    ]
    
    fieldsets = (
        ('Bet Information', {
            'fields': ('user', 'event', 'bet_type', 'stake', 'odds', 'potential_payout')
        }),
        ('Status', {
            'fields': ('status', 'placed_at', 'resolved_at')
        }),
        ('Additional Info', {
            'fields': ('ip_address', 'notes'),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'placed_at'
    
    actions = ['mark_as_won', 'mark_as_lost', 'mark_as_cancelled']
    
    def user_email(self, obj):
        """Display user email"""
        return obj.user.email
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'
    
    def event_name(self, obj):
        """Display event name"""
        return str(obj.event)
    event_name.short_description = 'Event'
    event_name.admin_order_field = 'event__start_time'
    
    def bet_type_display(self, obj):
        """Display formatted bet type"""
        return obj.get_bet_type_display()
    bet_type_display.short_description = 'Bet On'
    
    def stake_display(self, obj):
        """Display stake with currency"""
        return f"${obj.stake}"
    stake_display.short_description = 'Stake'
    stake_display.admin_order_field = 'stake'
    
    def potential_payout_display(self, obj):
        """Display potential payout with currency"""
        return f"${obj.potential_payout}"
    potential_payout_display.short_description = 'Potential Payout'
    potential_payout_display.admin_order_field = 'potential_payout'
    
    def status_badge(self, obj):
        """Display status as colored badge"""
        colors = {
            'pending': '#FFA500',  # Orange
            'won': '#28A745',      # Green
            'lost': '#DC3545',     # Red
            'cancelled': '#6C757D', # Gray
            'refunded': '#17A2B8',  # Blue
        }
        color = colors.get(obj.status, '#000000')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    def mark_as_won(self, request, queryset):
        """Admin action to mark selected bets as won"""
        updated = 0
        for bet in queryset.filter(status=Bet.PENDING):
            bet.mark_as_won()
            updated += 1
        self.message_user(request, f'{updated} bet(s) marked as won.')
    mark_as_won.short_description = "Mark selected bets as WON"
    
    def mark_as_lost(self, request, queryset):
        """Admin action to mark selected bets as lost"""
        updated = 0
        for bet in queryset.filter(status=Bet.PENDING):
            bet.mark_as_lost()
            updated += 1
        self.message_user(request, f'{updated} bet(s) marked as lost.')
    mark_as_lost.short_description = "Mark selected bets as LOST"
    
    def mark_as_cancelled(self, request, queryset):
        """Admin action to cancel selected bets"""
        updated = 0
        for bet in queryset.filter(status=Bet.PENDING):
            bet.mark_as_cancelled()
            updated += 1
        self.message_user(request, f'{updated} bet(s) cancelled.')
    mark_as_cancelled.short_description = "Cancel selected bets"


