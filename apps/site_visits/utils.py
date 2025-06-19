from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

def send_site_visit_assignment_email(site_visit, agent):
    """
    Send an email notification to an agent when a site visit is assigned to them.
    """
    subject = f'New Site Visit Scheduled: {site_visit.property.title}'
    
    # Get client name
    client_name = site_visit.client_name_manual
    if site_visit.client_user:
        client_name = site_visit.client_user.get_full_name() or site_visit.client_user.username
    
    # Get client phone
    client_phone = site_visit.client_phone_manual
    if site_visit.client_user and hasattr(site_visit.client_user, 'phone'):
        client_phone = site_visit.client_user.phone
    
    # Prepare the context for the email template
    context = {
        'agent_name': f"{agent.first_name or agent.username}",
        'property_title': site_visit.property.title,
        'client_name': client_name,
        'client_phone': client_phone or 'Not provided',
        'visit_date': site_visit.date.strftime('%B %d, %Y'),
        'visit_time': site_visit.time,
        'visit_status': site_visit.status.title(),
        'property_location': getattr(site_visit.property, 'location', 'Location not specified'),
        'property_type': getattr(site_visit.property, 'property_type', 'Type not specified'),
    }
    
    # Render the HTML message using a template
    html_message = render_to_string('site_visits/email/visit_assignment.html', context)
    
    # Plain text version
    plain_message = f"""
Hi {context['agent_name']},

A new site visit has been scheduled and assigned to you:

Property: {context['property_title']}
Client: {context['client_name']}
Phone: {context['client_phone']}
Date: {context['visit_date']}
Time: {context['visit_time']}
Status: {context['visit_status']}

Property Details:
Location: {context['property_location']}
Type: {context['property_type']}

Please ensure you're available for this visit.

Best regards,
CRM Team
    """.strip()
    
    # Send the email
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[agent.email],
        html_message=html_message,
        fail_silently=False,
    )
