from django import forms
from decimal import Decimal
from .models import Bet


class PlaceBetForm(forms.ModelForm):
    """
    Form for placing a bet on an event
    """
    
    class Meta:
        model = Bet
        fields = ['bet_type', 'stake']
        widgets = {
            'bet_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'bet-type-select'
            }),
            'stake': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter stake amount',
                'min': '1',
                'step': '0.01',
                'id': 'stake-input'
            }),
        }
        labels = {
            'bet_type': 'Select Outcome',
            'stake': 'Stake Amount ($)',
        }
    
    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Customize bet type choices based on event
        if self.event:
            self.fields['bet_type'].choices = self._get_bet_choices()
    
    def _get_bet_choices(self):
        """Generate bet choices with odds from the event"""
        if not self.event:
            return Bet.BET_TYPE_CHOICES
        
        # This will work with Developer 4's Event model once they have it
        try:
            return [
                ('team_a_win', f'{self.event.team_a} Wins (Odds: {self.event.odds_team_a})'),
                ('team_b_win', f'{self.event.team_b} Wins (Odds: {self.event.odds_team_b})'),
                ('draw', f'Draw (Odds: {self.event.odds_draw})'),
            ]
        except AttributeError:
            # Fallback if event structure is different
            return Bet.BET_TYPE_CHOICES
    
    def clean_stake(self):
        """Validate stake amount"""
        stake = self.cleaned_data.get('stake')
        
        # Minimum stake validation
        if stake < Decimal('1.00'):
            raise forms.ValidationError('Minimum stake is $1.00')
        
        # Maximum stake validation
        if stake > Decimal('10000.00'):
            raise forms.ValidationError('Maximum stake is $10,000.00')
        
        # Check if user has sufficient balance
        if self.user:
            try:
                from apps.wallet.models import Wallet
                wallet = Wallet.objects.get(user=self.user)
                if not wallet.has_sufficient_balance(stake):
                    raise forms.ValidationError(
                        f'Insufficient balance. Your balance: ${wallet.balance}'
                    )
            except Wallet.DoesNotExist:
                raise forms.ValidationError('Wallet not found. Please contact support.')
        
        return stake
    
    def clean(self):
        """Additional validation"""
        cleaned_data = super().clean()
        
        # Check if event is still bettable
        if self.event and hasattr(self.event, 'is_bettable'):
            if not self.event.is_bettable():
                raise forms.ValidationError('This event is no longer accepting bets.')
        
        return cleaned_data


class BetFilterForm(forms.Form):
    """
    Form for filtering bet history
    """
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + Bet.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    bet_type = forms.ChoiceField(
        choices=[('', 'All Bet Types')] + Bet.BET_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='From Date'
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='To Date'
    )
