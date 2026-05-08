import smtplib
import poplib
import imaplib
import logging
from typing import Optional, Tuple, Dict, Any, List, Union
from email import message_from_bytes
from .structures import AuthenticationError, ConnectionError
from .parser import AirParser

# Predefined configurations for common providers
SERVER_PRESETS = {
    'gmail.com': {
        'smtp_host': 'smtp.gmail.com', 'smtp_port': 465,
        'pop3_host': 'pop.gmail.com', 'pop3_port': 995,
        'imap_host': 'imap.gmail.com', 'imap_port': 993
    },
    'outlook.com': {
        'smtp_host': 'smtp.office365.com', 'smtp_port': 587,
        'pop3_host': 'outlook.office365.com', 'pop3_port': 995,
        'imap_host': 'outlook.office365.com', 'imap_port': 993
    },
    '163.com': {
        'smtp_host': 'smtp.163.com', 'smtp_port': 465,
        'pop3_host': 'pop.163.com', 'pop3_port': 995,
        'imap_host': 'imap.163.com', 'imap_port': 993
    },
    'qq.com': {
        'smtp_host': 'smtp.qq.com', 'smtp_port': 465,
        'pop3_host': 'pop.qq.com', 'pop3_port': 995,
        'imap_host': 'imap.qq.com', 'imap_port': 993
    },
}

class AirGateway:
    """
    Main entry point for AirMail. Handles connections to mail servers.
    """
    def __init__(self, user: str, password: str, smtp_host: str = None, pop3_host: str = None, 
                 imap_host: str = None, smtp_port: int = None, pop3_port: int = None, 
                 imap_port: int = None, use_ssl: bool = True):
        self.user = user
        self.password = password
        
        # Auto-detect server settings if not provided
        domain = user.split('@')[-1] if '@' in user else ''
        preset = SERVER_PRESETS.get(domain, {})
        
        self.smtp_host = smtp_host or preset.get('smtp_host')
        self.pop3_host = pop3_host or preset.get('pop3_host')
        self.imap_host = imap_host or preset.get('imap_host')
        
        self.smtp_port = smtp_port or preset.get('smtp_port', 465 if use_ssl else 25)
        self.pop3_port = pop3_port or preset.get('pop3_port', 995 if use_ssl else 110)
        self.imap_port = imap_port or preset.get('imap_port', 993 if use_ssl else 143)
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

    def _get_imap_conn(self):
        try:
            if self.use_ssl:
                conn = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            else:
                conn = imaplib.IMAP4(self.imap_host, self.imap_port)
            conn.login(self.user, self.password)
            return conn
        except Exception as e:
            raise AuthenticationError(f"IMAP Login failed for {self.user}: {str(e)}")

    def reachable(self) -> bool:
        """Check if SMTP, POP3 and IMAP (if available) are reachable."""
        try:
            with self._get_smtp_conn() as s:
                smtp_ok = True
            with self._get_pop3_conn() as p:
                pop3_ok = True
            imap_ok = True
            if self.imap_host:
                with self._get_imap_conn() as i:
                    imap_ok = True
            return smtp_ok and pop3_ok and imap_ok
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
        """Get the most recent email. Tries IMAP first, falls back to POP3."""
        if self.imap_host:
            try:
                with self._get_imap_conn() as server:
                    server.select('INBOX')
                    resp, data = server.search(None, 'ALL')
                    ids = data[0].split()
                    if not ids:
                        return {}
                    latest_id = ids[-1]
                    resp, data = server.fetch(latest_id, '(RFC822)')
                    msg_bytes = data[0][1]
                    mime_msg = message_from_bytes(msg_bytes)
                    return AirParser.decompose(mime_msg)
            except Exception as e:
                logging.warning(f"IMAP fetch_latest failed, falling back to POP3: {e}")
        
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
        """Fetch a range of emails. Tries IMAP first, falls back to POP3."""
        if self.imap_host:
            try:
                results = []
                with self._get_imap_conn() as server:
                    server.select('INBOX')
                    resp, data = server.search(None, 'ALL')
                    ids = data[0].split()
                    if not ids:
                        return []
                    
                    total = len(ids)
                    end = end or total
                    # IMAP ids are 1-based, we use the list index
                    for i in range(max(1, start), min(end, total) + 1):
                        msg_id = ids[i-1]
                        resp, msg_data = server.fetch(msg_id, '(RFC822)')
                        mime_msg = message_from_bytes(msg_data[0][1])
                        results.append(AirParser.decompose(mime_msg))
                return results
            except Exception as e:
                logging.warning(f"IMAP fetch_mails failed, falling back to POP3: {e}")

        results = []
        with self._get_pop3_conn() as server:
            total = len(server.list()[1])
            end = end or total
            for i in range(max(1, start), min(end, total) + 1):
                resp, lines, octets = server.retr(i)
                mime_msg = message_from_bytes(b'\n'.join(lines))
                results.append(AirParser.decompose(mime_msg))
        return results

    def folders(self) -> List[str]:
        """List all available folders (mailboxes)."""
        if not self.imap_host:
            return ['INBOX']
        with self._get_imap_conn() as server:
            resp, folder_list = server.list()
            if resp != 'OK':
                return []
            
            result = []
            for f in folder_list:
                line = f.decode()
                parts = line.split(' "/" ')
                if len(parts) > 1:
                    name = parts[-1].strip('"')
                    result.append(name)
            return result
