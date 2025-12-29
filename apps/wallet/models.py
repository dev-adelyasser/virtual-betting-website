from django.db import models
from apps.accounts.models import CustomUser
from django.core.validators import MinValueValidator
from django.db.models import F
from decimal import Decimal
from django.utils import timezone


class Wallet(models.Model):
    """
    User's wallet to manage virtual currency for betting
    """
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=1000.00,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    currency = models.CharField(max_length=3, default='USD')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'wallets'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username}'s Wallet - Balance: {self.balance} {self.currency}"
    
    def has_sufficient_balance(self, amount):
        """Check if wallet has enough balance for a transaction"""
        return self.balance >= Decimal(str(amount))
    
    def deduct(self, amount, description=""):
        """
        Deduct amount from wallet (for placing bets)
        Returns: Transaction object if successful, None otherwise
        """
        amount = Decimal(str(amount))
        if not self.has_sufficient_balance(amount):
            raise ValueError(f"Insufficient balance. Available: {self.balance}, Required: {amount}")
        
        self.balance = F('balance') - amount
        self.save(update_fields=['balance', 'updated_at'])
        self.refresh_from_db()
        
        # Create transaction record
        transaction = Transaction.objects.create(
            wallet=self,
            transaction_type=Transaction.DEBIT,
            amount=amount,
            balance_after=self.balance,
            description=description or "Bet placed"
        )
        return transaction
    
    def credit(self, amount, description=""):
        """
        Add amount to wallet (for winnings or deposits)
        Returns: Transaction object
        """
        amount = Decimal(str(amount))
        self.balance = F('balance') + amount
        self.save(update_fields=['balance', 'updated_at'])
        self.refresh_from_db()
        
        # Create transaction record
        transaction = Transaction.objects.create(
            wallet=self,
            transaction_type=Transaction.CREDIT,
            amount=amount,
            balance_after=self.balance,
            description=description or "Amount credited"
        )
        return transaction
    
    def get_total_deposited(self):
        """Calculate total amount deposited"""
        return self.transactions.filter(
            transaction_type=Transaction.CREDIT,
            status=Transaction.COMPLETED
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
    
    def get_total_withdrawn(self):
        """Calculate total amount withdrawn"""
        return self.transactions.filter(
            transaction_type=Transaction.DEBIT,
            status=Transaction.COMPLETED
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')


class Transaction(models.Model):
    """
    Record of all wallet transactions
    """
    CREDIT = 'credit'
    DEBIT = 'debit'
    TRANSACTION_TYPES = [
        (CREDIT, 'Credit'),
        (DEBIT, 'Debit'),
    ]
    
    PENDING = 'pending'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (COMPLETED, 'Completed'),
        (FAILED, 'Failed'),
        (CANCELLED, 'Cancelled'),
    ]
    
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=COMPLETED)
    reference_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', '-created_at']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount} - {self.wallet.user.username}"
    
    def get_transaction_icon(self):
        """Return icon class based on transaction type"""
        return '↑' if self.transaction_type == self.CREDIT else '↓'
    
    def get_transaction_class(self):
        """Return CSS class for styling"""
        return 'credit' if self.transaction_type == self.CREDIT else 'debit'


class WalletManager:
    """
    Manager class for wallet operations using OOP principles
    """
    
    @staticmethod
    def create_wallet_for_user(user, initial_balance=1000.00):
        """Create a new wallet for a user"""
        wallet, created = Wallet.objects.get_or_create(
            user=user,
            defaults={'balance': Decimal(str(initial_balance))}
        )
        if created:
            Transaction.objects.create(
                wallet=wallet,
                transaction_type=Transaction.CREDIT,
                amount=Decimal(str(initial_balance)),
                balance_after=wallet.balance,
                description="Initial deposit"
            )
        return wallet, created
    
    @staticmethod
    def process_bet_placement(user, bet_amount):
        """
        Process wallet deduction for bet placement
        Returns: (success: bool, message: str, transaction: Transaction or None)
        """
        try:
            wallet = Wallet.objects.select_for_update().get(user=user)
            
            if not wallet.is_active:
                return False, "Wallet is not active", None
            
            if not wallet.has_sufficient_balance(bet_amount):
                return False, f"Insufficient balance. Available: {wallet.balance}", None
            
            transaction = wallet.deduct(bet_amount, f"Bet placed - {bet_amount}")
            return True, "Bet placed successfully", transaction
            
        except Wallet.DoesNotExist:
            return False, "Wallet not found", None
        except Exception as e:
            return False, str(e), None
    
    @staticmethod
    def process_bet_winning(user, winning_amount, bet_id=None):
        """
        Process wallet credit for bet winnings
        Returns: (success: bool, message: str, transaction: Transaction or None)
        """
        try:
            wallet = Wallet.objects.select_for_update().get(user=user)
            
            if not wallet.is_active:
                return False, "Wallet is not active", None
            
            description = f"Bet winning - {winning_amount}"
            if bet_id:
                description += f" (Bet #{bet_id})"
            
            transaction = wallet.credit(winning_amount, description)
            return True, "Winnings credited successfully", transaction
            
        except Wallet.DoesNotExist:
            return False, "Wallet not found", None
        except Exception as e:
            return False, str(e), None
    
    @staticmethod
    def get_wallet_summary(user):
        """
        Get comprehensive wallet summary
        Returns: dict with wallet statistics
        """
        try:
            wallet = Wallet.objects.get(user=user)
            return {
                'balance': wallet.balance,
                'currency': wallet.currency,
                'total_deposited': wallet.get_total_deposited(),
                'total_withdrawn': wallet.get_total_withdrawn(),
                'is_active': wallet.is_active,
                'created_at': wallet.created_at,
                'transaction_count': wallet.transactions.count(),
            }
        except Wallet.DoesNotExist:
            return None
    
    @staticmethod
    def get_transaction_history(user, limit=50):
        """Get user's transaction history"""
        try:
            wallet = Wallet.objects.get(user=user)
            return wallet.transactions.all()[:limit]
        except Wallet.DoesNotExist:
            return []
