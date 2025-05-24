from django.db import models
from django.conf import settings

class Lead(models.Model):
    STATUS_CHOICES = [
    ('New', 'New'),
    ('Contacted', 'Contacted'),
    ('Site Visit Scheduled', 'Site Visit Scheduled'),
    ('Site Visit Done', 'Site Visit Done'),
    ('Qualified', 'Qualified'),
    ('Proposal', 'Proposal'),
    ('Negotiation', 'Negotiation'),
    ('Converted', 'Converted'),
    ('Dropped', 'Dropped'),
]
    
    SOURCE_CHOICES = [
        ('Website', 'Website'),
        ('WhatsApp', 'WhatsApp'),
        ('Facebook', 'Facebook'),
        ('Referral', 'Referral'),
        ('Direct Call', 'Direct Call'),
        ('Email', 'Email'),
        ('Other', 'Other'),
    ]
    
    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Urgent', 'Urgent'),
    ]

    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    company = models.CharField(max_length=255, blank=True)
    position = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='New')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='Website')
    interest = models.CharField(max_length=255, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Medium')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_leads'
    )
    budget = models.CharField(max_length=255, blank=True)
    timeline = models.CharField(max_length=255, blank=True)
    requirements = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    tags = models.JSONField(default=list)
    last_activity = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_leads'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.status}"