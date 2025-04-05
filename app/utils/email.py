import logging
import boto3
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_email(
    recipients: List[str],
    subject: str,
    body_html: str,
    body_text: Optional[str] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    reply_to: Optional[List[str]] = None,
) -> bool:
    """
    Send email using AWS SES service.
    
    Args:
        recipients: List of recipient email addresses
        subject: Email subject
        body_html: HTML body content
        body_text: Plain text body (optional, will be generated from HTML if not provided)
        cc: List of CC recipients (optional)
        bcc: List of BCC recipients (optional)
        reply_to: List of Reply-To addresses (optional)
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    # If text body not provided, create a simple version from HTML
    if not body_text:
        # Very simple HTML to text conversion - just remove tags
        # In a production app, you'd want a better HTML to text converter
        body_text = body_html.replace('<br>', '\n').replace('<p>', '\n').replace('</p>', '\n')
        for tag in ['<[^>]*>', '</[^>]*>']:
            import re
            body_text = re.sub(tag, '', body_text)
    
    try:
        # Create a new SES resource
        ses_client = boto3.client(
            'ses',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        
        # Create a multipart message container
        msg = MIMEMultipart('mixed')
        msg['Subject'] = subject
        msg['From'] = f"{settings.SES_SENDER_NAME} <{settings.SES_SENDER_EMAIL}>"
        msg['To'] = ", ".join(recipients)
        
        # Optional headers
        if cc:
            msg['Cc'] = ", ".join(cc)
        if reply_to:
            msg['Reply-To'] = ", ".join(reply_to)
            
        # Create a multipart/alternative child container
        msg_body = MIMEMultipart('alternative')
        
        # Attach the plain text version
        textpart = MIMEText(body_text, 'plain', 'utf-8')
        msg_body.attach(textpart)
        
        # Attach the HTML version
        htmlpart = MIMEText(body_html, 'html', 'utf-8')
        msg_body.attach(htmlpart)
        
        # Attach the multipart/alternative child container to the multipart/mixed parent
        msg.attach(msg_body)
        
        # Add all recipients for the SES API
        all_recipients = set(recipients)
        if cc:
            all_recipients.update(cc)
        if bcc:
            all_recipients.update(bcc)
            
        # Convert the entire email to a string
        raw_message = {'Data': msg.as_string()}
        
        # Send the email
        response = ses_client.send_raw_email(
            Source=f"{settings.SES_SENDER_NAME} <{settings.SES_SENDER_EMAIL}>",
            Destinations=list(all_recipients),
            RawMessage=raw_message
        )
        
        logger.info(f"Email sent! Message ID: {response['MessageId']}")
        return True
    
    except ClientError as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending email: {str(e)}")
        return False
        

async def send_password_reset_email(email: str, reset_token: str, reset_url: str) -> bool:
    """
    Send a password reset email with token
    
    Args:
        email: Recipient email address
        reset_token: Password reset token
        reset_url: Base URL for password reset (token will be appended)
        
    Returns:
        bool: True if email was sent successfully
    """
    subject = "Reset Your Password - Expense Tracker"
    
    # Add token to reset URL
    reset_link = f"{reset_url}?token={reset_token}"
    
    # HTML email body
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #4a6ee0; color: white; padding: 15px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9f9f9; }}
            .button {{ display: inline-block; padding: 10px 20px; margin: 20px 0; background-color: #4a6ee0; color: white; 
                       text-decoration: none; border-radius: 4px; }}
            .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #999; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Reset Your Password</h1>
            </div>
            <div class="content">
                <p>Hello,</p>
                <p>We received a request to reset your password for the Expense Tracker app. 
                   If you didn't make this request, you can ignore this email.</p>
                <p>To reset your password, click the button below:</p>
                <p style="text-align: center;">
                    <a href="{reset_link}" class="button">Reset Password</a>
                </p>
                <p>Or copy and paste this link into your browser:</p>
                <p>{reset_link}</p>
                <p>This password reset link will expire in 30 minutes.</p>
                <p>Best regards,<br>The Expense Tracker Team</p>
            </div>
            <div class="footer">
                <p>This is an automated message, please do not reply to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Send the email
    return await send_email(
        recipients=[email],
        subject=subject,
        body_html=html_body
    )
