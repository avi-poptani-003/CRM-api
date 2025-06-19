from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

def send_lead_assignment_email(lead, agent):
    """
    Send an email notification to an agent when a lead is assigned to them.
    """
    subject = f'New Lead Assigned: {lead.name}'
    
    # Prepare the context for the email template
    context = {
        'agent_name': f"{agent.first_name or agent.username}",
        'lead_name': lead.name,
        'lead_email': lead.email,
        'lead_phone': lead.phone,
        'lead_status': lead.status,
        'lead_source': lead.source,
        'lead_interest': lead.interest or 'Not specified',
        'company': lead.company or 'Not specified',
    }
    
    # Render the HTML message using a template
    html_message = render_to_string('leads/email/lead_assignment.html', context)
    
    # Plain text version
    plain_message = f"""
Hi {context['agent_name']},

A new lead has been assigned to you:

Name: {lead.name}
Email: {lead.email}
Phone: {lead.phone}
Status: {lead.status}
Source: {lead.source}
Interest: {context['lead_interest']}
Company: {context['company']}

Please follow up as soon as possible.

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
