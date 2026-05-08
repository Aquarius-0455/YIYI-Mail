# AirMail 🛫

A modernized, lightweight Python library for sending and retrieving emails.

Inspired by Zmail, built for the future.

## ✨ Features
- **Zero Configuration**: Automatically detects server settings for major providers (Gmail, Outlook, 163, QQ).
- **Modern Python**: Full type hinting, f-strings, and Python 3.7+ support.
- **Robust Parsing**: Uses modern `email.message.EmailMessage` for reliable MIME handling.
- **Clean API**: Intuitive methods like `push` and `fetch`.

## 🚀 Quick Start

### Installation
```bash
pip install airmail-python
```

### Sending an Email
```python
import AirMail

# Connect to your account
mail = AirMail.connect('your_name@gmail.com', 'your_app_password')

# Send a message
mail.send(
    recipients='friend@example.com',
    subject='Hello from AirMail!',
    content='This is a plain text message.',
    html='<h1>Or send HTML</h1>',
    attachments=['report.pdf']
)
```

### Retrieving Emails
```python
# Get the most recent email
latest = mail.fetch_latest()
print(f"From: {latest['from']}")
print(f"Subject: {latest['subject']}")

# Get a range of emails
inbox = mail.fetch_mails(start=1, end=5)
```

## 🛠️ Comparison with Zmail

| Feature | Zmail | **AirMail** |
| :--- | :--- | :--- |
| **API Style** | `server.send_mail` | `gateway.send` / `push` |
| **Code Base** | Legacy Python 2/3 | Python 3.7+ Clean |
| **Type Hints** | ❌ No | ✅ Yes |
| **Parsing** | Custom Logic | Standard `EmailMessage` |
| **Maintenance** | Unmaintained | **Active** |

## 📄 License
MIT
