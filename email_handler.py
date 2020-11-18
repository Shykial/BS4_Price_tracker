import smtplib
from email.message import EmailMessage
import email_secrets


def send_email(to: str, from_: str = email_secrets.email_address, mail_server_: str = email_secrets.mail_server,
               msg: EmailMessage = None, subject: str = None, body: str = None):
    if not msg:
        if subject and body:
            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From'] = from_
            msg['To'] = to
            msg.set_content(body)
        else:
            raise AttributeError('Insufficient arguments provided, please "msg" or both "subject" and "body"')

    with smtplib.SMTP(mail_server_, 587, timeout=1000) as smtp:

        smtp.starttls()
        smtp.login(from_, email_secrets.email_password)
        smtp.send_message(msg)
