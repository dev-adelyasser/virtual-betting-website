from django.db import models
from django.utils import timezone


class Event(models.Model):
    """
    TEMPORARY PLACEHOLDER - Will be replaced by Developer 4's implementation
    This allows Bets app to be developed independently
    """
    # Basic fields that any event model should have
    name = models.CharField(max_length=255, help_text="Event name (e.g., 'Real Madrid vs Barcelona')")
    
    team_a = models.CharField(max_length=100, default="Team A")
    team_b = models.CharField(max_length=100, default="Team B")
    
    # Odds (Developer 4 might structure this differently)
    odds_team_a = models.DecimalField(max_digits=6, decimal_places=2, default=2.00)
    odds_team_b = models.DecimalField(max_digits=6, decimal_places=2, default=2.00)
    odds_draw = models.DecimalField(max_digits=6, decimal_places=2, default=3.00)
    
    start_time = models.DateTimeField()
    
    # Status
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('live', 'Live'),
        ('finished', 'Finished'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    
    # Result (will be set by Developer 6 - Results)
    result = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        choices=[
            ('team_a_win', 'Team A Won'),
            ('team_b_win', 'Team B Won'),
            ('draw', 'Draw'),
        ]
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['start_time']
    
    def __str__(self):
        return f"{self.team_a} vs {self.team_b} - {self.start_time.strftime('%Y-%m-%d')}"
    
    def is_bettable(self):
        """Check if event is still open for betting"""
        return self.status == 'upcoming' and self.start_time > timezone.now()
    
    def get_odds_for_bet_type(self, bet_type):
        """Get odds based on bet type"""
        odds_map = {
            'team_a_win': self.odds_team_a,
            'team_b_win': self.odds_team_b,
            'draw': self.odds_draw,
        }
        return odds_map.get(bet_type, 1.00)
