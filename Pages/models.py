from django.db import models

class Team(models.Model):
    name = models.CharField(max_length=100)  
    country = models.CharField(max_length=50) 

    def __str__(self):
        return self.name

class Match(models.Model):
    home_team = models.ForeignKey(Team, related_name='home_matches', on_delete=models.CASCADE)
    away_team = models.ForeignKey(Team, related_name='away_matches', on_delete=models.CASCADE) 
    date = models.DateTimeField() 
    
    home_odds = models.DecimalField(max_digits=5, decimal_places=2, default=1.50) 
    draw_odds = models.DecimalField(max_digits=5, decimal_places=2, default=3.00) 
    away_odds = models.DecimalField(max_digits=5, decimal_places=2, default=2.50) 

    def __str__(self):
        return f"{self.home_team} vs {self.away_team}"