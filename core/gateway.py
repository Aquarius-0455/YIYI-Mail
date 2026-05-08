import smtplib
import poplib
import logging
from typing import Optional, Tuple, Dict, Any, List, Union
from email import message_from_bytes
from .structures import AuthenticationError, ConnectionError
from .parser import AirParser

# Predefined configurations for common providers
SERVER_PRESETS = {
    'gmail.com': {'smtp_host': 'smtp.gmail.com', 'pop3_host': 'pop.gmail.com', 'smtp_port': 465, 'pop3_port': 995},
    'outlook.com': {'smtp_host': 'smtp.office365.com', 'pop3_host': 'outlook.office365.com', 'smtp_port': 587, 'pop3_port': 995},
    '163.com': {'smtp_host': 'smtp.163.com', 'pop3_host': 'pop.163.com', 'smtp_port': 465, 'pop3_port': 995},
    'qq.com': {'smtp_host': 'smtp.qq.com', 'pop3_host': 'pop.qq.com', 'smtp_port': 465, 'pop3_port': 995},
}

class AirGateway:
    """
    Main entry point for AirMail. Handles connections to mail servers.
    """
    def __init__(self, user: str, password: str, smtp_host: str = None, pop3_host: str = None, 
                 smtp_port: int = None, pop3_port: int = None, use_ssl: bool = True):
        self.user = user
        self.password = password
        
        # Auto-detect server settings if not provided
        domain = user.split('@')[-1] if '@' in user else ''
        preset = SERVER_PRESETS.get(domain, {})
        
        self.smtp_host = smtp_host or preset.get('smtp_host')
        self.pop3_host = pop3_host or preset.get('pop3_host')
        self.smtp_port = smtp_port or preset.get('smtp_port', 465 if use_ssl else 25)
        self.pop3_port = pop3_port or preset.get('pop3_port', 995 if use_ssl else 110)
        self.use_ssl = use_ssl

    def _get_smtp_conn(self):
        try:
            if self.use_ssl:
                conn = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
            else:
                conn = smtplib.SMTP(self.smtp_host, self.smtp_port)
                conn.starttls()
            conn.login(self.user, self.password)
            return conn
        except Exception as e:
            raise AuthenticationError(f"SMTP Login failed for {self.user}: {str(e)}")

    def _get_pop3_conn(self):
        try:
            if self.use_ssl:
                conn = poplib.POP3_SSL(self.pop3_host, self.pop3_port)
            else:
                conn = poplib.POP3(self.pop3_host, self.pop3_port)
            conn.user(self.user)
            conn.pass_(self.password)
            return conn
        except Exception as e:
            raise AuthenticationError(f"POP3 Login failed for {self.user}: {str(e)}")

    def reachable(self) -> bool:
        """Check if both SMTP and POP3 are reachable."""
        try:
            with self._get_smtp_conn() as s:
                smtp_ok = True
            with self._get_pop3_conn() as p:
                pop3_ok = True
            return smtp_ok and pop3_ok
        except:
            return False

    def send(self, recipients: Union[str, List[str]], subject: str, content: str, 
             html: str = None, attachments: list = None):
        """
        Send an email.
        """
        msg = AirParser.compose(self.user, recipients, subject, content, html, attachments)
        with self._get_smtp_conn() as server:
            server.send_message(msg)
            logging.info(f"Email sent successfully to {recipients}")

    def fetch_latest(self) -> Dict[str, Any]:
        """Get the most recent email from the inbox."""
        with self._get_pop3_conn() as server:
            msg_count = len(server.list()[1])
            if msg_count == 0:
                return {}
            
            # POP3 is 1-indexed
            resp, lines, octets = server.retr(msg_count)
            msg_bytes = b'\n'.join(lines)
            mime_msg = message_from_bytes(msg_bytes)
            return AirParser.decompose(mime_msg)

    def fetch_mails(self, start: int = 1, end: int = None) -> List[Dict[str, Any]]:
        """Fetch a range of emails."""
        results = []
        with self._get_pop3_conn() as server:
            total = len(server.list()[1])
            end = end or total
            for i in range(max(1, start), min(end, total) + 1):
                resp, lines, octets = server.retr(i)
                mime_msg = message_from_bytes(b'\n'.join(lines))
                results.append(AirParser.decompose(mime_msg))
        return results
