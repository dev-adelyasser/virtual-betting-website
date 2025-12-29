from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Sum, Q
from decimal import Decimal
from apps.events.models import Event
from apps.wallet.models import Wallet, WalletManager
from .models import Bet
from .forms import PlaceBetForm, BetFilterForm


@login_required
def place_bet(request, event_id):
    """
    View for placing a bet on an event
    Integrates with Wallet app to deduct stake
    """
    # Get the event
    event = get_object_or_404(Event, id=event_id)
    
    # Get user's wallet
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    # Check if event is bettable
    if hasattr(event, 'is_bettable') and not event.is_bettable():
        messages.error(request, 'This event is no longer accepting bets.')
        return redirect('events:detail', event_id=event_id)
    
    if request.method == 'POST':
        form = PlaceBetForm(request.POST, event=event, user=request.user)
        
        if form.is_valid():
            # Use atomic transaction to ensure wallet and bet are updated together
            try:
                with transaction.atomic():
                    # Get form data
                    bet_type = form.cleaned_data['bet_type']
                    stake = form.cleaned_data['stake']
                    
                    # Get odds for the selected bet type
                    odds = event.get_odds_for_bet_type(bet_type) if hasattr(event, 'get_odds_for_bet_type') else Decimal('2.00')
                    
                    # Deduct stake from wallet using WalletManager
                    success, message, wallet_transaction = WalletManager.process_bet_placement(
                        user=request.user,
                        bet_amount=stake
                    )
                    
                    if not success:
                        messages.error(request, message)
                        return redirect('bets:place_bet', event_id=event_id)
                    
                    # Create the bet
                    bet = form.save(commit=False)
                    bet.user = request.user
                    bet.event = event
                    bet.odds = odds
                    bet.potential_payout = stake * odds
                    
                    # Get user's IP address
                    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                    if x_forwarded_for:
                        bet.ip_address = x_forwarded_for.split(',')[0]
                    else:
                        bet.ip_address = request.META.get('REMOTE_ADDR')
                    
                    bet.save()
                    
                    messages.success(
                        request, 
                        f'Bet placed successfully! ${stake} on {bet.get_bet_type_display()}. Potential payout: ${bet.potential_payout}'
                    )
                    return redirect('bets:detail', bet_id=bet.id)
                    
            except Exception as e:
                messages.error(request, f'Error placing bet: {str(e)}')
                return redirect('bets:place_bet', event_id=event_id)
    else:
        form = PlaceBetForm(event=event, user=request.user)
    
    context = {
        'form': form,
        'event': event,
        'wallet': wallet,
    }
    
    return render(request, 'bets/place_bet.html', context)


@login_required
def bet_history(request):
    """
    Display user's betting history with filters
    """
    # Get user's wallet for stats
    wallet = get_object_or_404(Wallet, user=request.user)
    
    # Get all user's bets
    bets = Bet.objects.filter(user=request.user).select_related('event')
    
    # Apply filters
    filter_form = BetFilterForm(request.GET)
    if filter_form.is_valid():
        status = filter_form.cleaned_data.get('status')
        bet_type = filter_form.cleaned_data.get('bet_type')
        date_from = filter_form.cleaned_data.get('date_from')
        date_to = filter_form.cleaned_data.get('date_to')
        
        if status:
            bets = bets.filter(status=status)
        if bet_type:
            bets = bets.filter(bet_type=bet_type)
        if date_from:
            bets = bets.filter(placed_at__gte=date_from)
        if date_to:
            bets = bets.filter(placed_at__lte=date_to)
    
    # Get statistics
    stats = Bet.get_user_stats(request.user)
    
    context = {
        'bets': bets,
        'wallet': wallet,
        'filter_form': filter_form,
        'stats': stats,
    }
    
    return render(request, 'bets/bet_history.html', context)


@login_required
def bet_detail(request, bet_id):
    """
    Display detailed information about a specific bet
    """
    bet = get_object_or_404(Bet, id=bet_id, user=request.user)
    
    context = {
        'bet': bet,
        'can_cancel': bet.can_be_cancelled(),
    }
    
    return render(request, 'bets/bet_detail.html', context)


@login_required
def cancel_bet(request, bet_id):
    """
    Cancel a pending bet and refund the stake
    """
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('bets:history')
    
    bet = get_object_or_404(Bet, id=bet_id, user=request.user)
    
    if not bet.can_be_cancelled():
        messages.error(request, 'This bet cannot be cancelled.')
        return redirect('bets:detail', bet_id=bet_id)
    
    try:
        with transaction.atomic():
            # Refund the stake to wallet
            success, message, wallet_transaction = WalletManager.process_bet_winning(
                user=request.user,
                winning_amount=bet.stake,
                bet_id=bet.id
            )
            
            if success:
                # Mark bet as cancelled
                bet.mark_as_cancelled()
                messages.success(request, f'Bet cancelled. ${bet.stake} has been refunded to your wallet.')
            else:
                messages.error(request, f'Error refunding bet: {message}')
                
    except Exception as e:
        messages.error(request, f'Error cancelling bet: {str(e)}')
    
    return redirect('bets:history')


@login_required
def active_bets(request):
    """
    Display only active (pending) bets
    """
    bets = Bet.objects.filter(
        user=request.user, 
        status=Bet.PENDING
    ).select_related('event')
    
    context = {
        'bets': bets,
        'page_title': 'Active Bets',
    }
    
    return render(request, 'bets/active_bets.html', context)


# API Endpoints for AJAX requests

@login_required
def calculate_payout_api(request):
    """
    API endpoint to calculate potential payout
    Used for real-time calculation in the betting form
    """
    try:
        event_id = request.GET.get('event_id')
        bet_type = request.GET.get('bet_type')
        stake = Decimal(request.GET.get('stake', '0'))
        
        event = Event.objects.get(id=event_id)
        odds = event.get_odds_for_bet_type(bet_type) if hasattr(event, 'get_odds_for_bet_type') else Decimal('2.00')
        
        potential_payout = stake * odds
        profit = potential_payout - stake
        
        return JsonResponse({
            'success': True,
            'stake': float(stake),
            'odds': float(odds),
            'potential_payout': float(potential_payout),
            'profit': float(profit),
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def bet_stats_api(request):
    """
    API endpoint to get user's betting statistics
    """
    try:
        stats = Bet.get_user_stats(request.user)
        
        # Convert Decimal to float for JSON
        stats_json = {
            key: float(value) if isinstance(value, Decimal) else value
            for key, value in stats.items()
        }
        
        return JsonResponse({
            'success': True,
            'stats': stats_json
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def check_bet_eligibility(request, event_id):
    """
    API endpoint to check if user can bet on an event
    """
    try:
        event = Event.objects.get(id=event_id)
        wallet = Wallet.objects.get(user=request.user)
        
        is_bettable = event.is_bettable() if hasattr(event, 'is_bettable') else True
        
        return JsonResponse({
            'success': True,
            'is_bettable': is_bettable,
            'wallet_balance': float(wallet.balance),
            'message': 'Event is open for betting' if is_bettable else 'Event is closed for betting'
        })
    except Event.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Event not found'
        }, status=404)
    except Wallet.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Wallet not found'
        }, status=404)
