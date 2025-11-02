import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(
    to_email: str,
    subject: str,
    body: str,
    sender_email: str = "",
    app_password: str = ""
):
    """
    Sends an email via Gmail SMTP.
    """
    msg = MIMEMultipart("alternative")
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject

    html_body = f"""
    <html>
        <body>
            <p>{body}</p>
            <br>
            <p style="font-size:small;color:gray;">
                This is an automated message from CEP Lost & Found.
            </p>
        </body>
    </html>
    """
    msg.attach(MIMEText(html_body, "html"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()
        print(f"[INFO] Email sent successfully to {to_email}")
    except smtplib.SMTPAuthenticationError:
        print("[ERROR] Authentication failed. Check your Gmail and App Password.")
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")
