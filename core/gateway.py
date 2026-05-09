import smtplib
import poplib
import imaplib
import logging
from typing import Optional, Tuple, Dict, Any, List, Union
from email import message_from_bytes
from .structures import AuthenticationError, ConnectionError
from .parser import AirParser
from .utils import decode_imap_utf7, encode_imap_utf7

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
    # Enterprise Presets
    'exmail.qq.com': {
        'smtp_host': 'smtp.exmail.qq.com', 'smtp_port': 465,
        'pop3_host': 'pop.exmail.qq.com', 'pop3_port': 995,
        'imap_host': 'imap.exmail.qq.com', 'imap_port': 993
    },
    'mxhichina.com': {
        'smtp_host': 'smtp.mxhichina.com', 'smtp_port': 465,
        'pop3_host': 'pop3.mxhichina.com', 'pop3_port': 995,
        'imap_host': 'imap.mxhichina.com', 'imap_port': 993
    },
    'qiye.163.com': {
        'smtp_host': 'smtphz.qiye.163.com', 'smtp_port': 465,
        'pop3_host': 'pophz.qiye.163.com', 'pop3_port': 995,
        'imap_host': 'imaphz.qiye.163.com', 'imap_port': 993
    },
}

class YIYIGateway:
    """
    YIYIMail 核心网关类。负责维护协议连接、会话状态及多协议平滑回退。
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
            # Ensure ID command is registered in imaplib
            if 'ID' not in imaplib.Commands:
                imaplib.Commands['ID'] = ('AUTH', 'NONAUTH')

            if self.use_ssl:
                conn = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            else:
                conn = imaplib.IMAP4(self.imap_host, self.imap_port)
            conn.login(self.user, self.password)
            
            # 遵循 RFC 2971：发送 ID 命令。
            # 163/网易系列邮箱强制要求 ID 验证，否则会拦截 SELECT 等后续指令（报 Unsafe Login）。
            try:
                conn._simple_command('ID', '("name" "YIYIMail" "version" "1.0.1")')
            except:
                pass # 服务器不支持或扩展已禁用
                
            return conn
        except Exception as e:
            raise AuthenticationError(f"IMAP Login failed for {self.user}: {str(e)}")

    def _smart_select(self, server, folder: str):
        """
        文件夹选择策略：优先尝试原始名称，失败则通过目录列表进行大小写不敏感匹配。
        """
        # 1. Try direct select (standard or encoded)
        resp, _ = server.select(encode_imap_utf7(folder))
        if resp == 'OK':
            return True
        
        # 2. Try fuzzy match from server folder list
        all_folders = self.folders()
        for f in all_folders:
            if f.lower() == folder.lower():
                resp, _ = server.select(encode_imap_utf7(f))
                if resp == 'OK':
                    return True
        return False

    def reachable(self) -> bool:
        """Check if SMTP, POP3 and IMAP (if available) are reachable."""
        try:
            with self._get_smtp_conn():
                smtp_ok = True
            
            pop3_ok = False
            p = self._get_pop3_conn()
            try:
                pop3_ok = True
            finally:
                p.quit()
                
            imap_ok = True
            if self.imap_host:
                with self._get_imap_conn():
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

    def fetch_latest(self, folder: str = 'INBOX') -> Dict[str, Any]:
        """获取最新邮件。优先走 IMAP 管道，失败则平滑回退至 POP3。"""
        if self.imap_host:
            try:
                with self._get_imap_conn() as server:
                    if not self._smart_select(server, folder):
                        raise ConnectionError(f"Folder not found: {folder}")
                    resp, data = server.search(None, 'ALL')
                    ids = data[0].split()
                    if not ids:
                        return {}
                    latest_id = ids[-1]
                    resp, data = server.fetch(latest_id, '(RFC822)')
                    msg_bytes = data[0][1]
                    mime_msg = message_from_bytes(msg_bytes)
                    result = AirParser.decompose(mime_msg)
                    result['uid'] = latest_id.decode()
                    return result
            except Exception as e:
                logging.warning(f"IMAP fetch_latest failed, falling back to POP3: {e}")
        
        p = self._get_pop3_conn()
        try:
            msg_count = len(p.list()[1])
            if msg_count == 0:
                return {}
            
            resp, lines, octets = p.retr(msg_count)
            msg_bytes = b'\n'.join(lines)
            mime_msg = message_from_bytes(msg_bytes)
            return AirParser.decompose(mime_msg)
        finally:
            p.quit()

    def fetch_mails(self, start: int = 1, end: int = None, folder: str = 'INBOX') -> List[Dict[str, Any]]:
        """Fetch a range of emails with IMAP/POP3 fallback."""
        if self.imap_host:
            try:
                results = []
                with self._get_imap_conn() as server:
                    if not self._smart_select(server, folder):
                        raise ConnectionError(f"Folder not found: {folder}")
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
                        res = AirParser.decompose(mime_msg)
                        res['uid'] = msg_id.decode()
                        results.append(res)
                    return results
            except Exception as e:
                logging.warning(f"IMAP fetch_mails failed, falling back to POP3: {e}")

        results = []
        p = self._get_pop3_conn()
        try:
            total = len(p.list()[1])
            end = end or total
            for i in range(max(1, start), min(end, total) + 1):
                resp, lines, octets = p.retr(i)
                mime_msg = message_from_bytes(b'\n'.join(lines))
                results.append(AirParser.decompose(mime_msg))
        finally:
            p.quit()
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
                    # 解析 IMAP LIST 返回值中的 Modified UTF-7 编码（处理中文目录名）
                    result.append(decode_imap_utf7(name))
            return result

    def info(self) -> Dict[str, Any]:
        """Get mailbox statistics (count, total size)."""
        p = self._get_pop3_conn()
        try:
            count, size = p.stat()
            return {'count': count, 'size_bytes': size}
        finally:
            p.quit()

    def delete(self, index: int):
        """Mark an email for deletion."""
        p = self._get_pop3_conn()
        try:
            p.dele(index)
            logging.info(f"Email at index {index} marked for deletion.")
        finally:
            p.quit()

    def search(self, subject: str = None, sender: str = None, unseen: bool = False,
               after: str = None, before: str = None, folder: str = 'INBOX', limit: int = None) -> List[Dict[str, Any]]:
        """
        Search for emails matching criteria. 
        after/before format: 'YYYY-MM-DD'
        """
        if self.imap_host:
            try:
                with self._get_imap_conn() as server:
                    if not self._smart_select(server, folder):
                        raise ConnectionError(f"Folder not found: {folder}")
                    
                    criteria = []
                    if subject: criteria.append(f'SUBJECT "{subject}"')
                    if sender: criteria.append(f'FROM "{sender}"')
                    if unseen: criteria.append('UNSEEN')
                    
                    # 基于 RFC 3501 规范构造搜索指令
                    import datetime
                    if after:
                        dt = datetime.datetime.strptime(after, '%Y-%m-%d')
                        criteria.append(f'SINCE {dt.strftime("%d-%b-%Y")}')
                    if before:
                        dt = datetime.datetime.strptime(before, '%Y-%m-%d')
                        criteria.append(f'BEFORE {dt.strftime("%d-%b-%Y")}')

                    query = " ".join(criteria) or 'ALL'
                    resp, data = server.search(None, query)
                    
                    ids = data[0].split()
                    if limit:
                        ids = ids[-limit:]
                        
                    results = []
                    for msg_id in ids:
                        resp, msg_data = server.fetch(msg_id, '(RFC822)')
                        mime_msg = message_from_bytes(msg_data[0][1])
                        res = AirParser.decompose(mime_msg)
                        res['uid'] = msg_id.decode()
                        results.append(res)
                    return results
            except Exception as e:
                logging.warning(f"IMAP search failed, falling back to POP3: {e}")

        return self._legacy_pop3_search(subject, sender)

    def _legacy_pop3_search(self, subject: str = None, sender: str = None) -> List[Dict[str, Any]]:
        """Legacy local filtering for POP3."""
        logging.info("Searching inbox (this may take time for large mailboxes)...")
        all_mails = self.fetch_mails()
        filtered = []
        for mail in all_mails:
            match = True
            if subject and subject.lower() not in (mail.get('subject') or '').lower():
                match = False
            if sender and sender.lower() not in (mail.get('from') or '').lower():
                match = False
            if match:
                filtered.append(mail)
        return filtered

    def smtp_able(self) -> bool:
        """Verify SMTP connection and login."""
        try:
            with self._get_smtp_conn():
                return True
        except:
            return False

    def pop_able(self) -> bool:
        """Verify POP3 connection and login."""
        try:
            p = self._get_pop3_conn()
            p.quit()
            return True
        except:
            return False

    def mark_as_read(self, uid: str, folder: str = 'INBOX'):
        """Apply \Seen flag (IMAP specific)."""
        if not self.imap_host:
            logging.warning("mark_as_read requires IMAP support.")
            return
        with self._get_imap_conn() as server:
            if self._smart_select(server, folder):
                server.store(uid, '+FLAGS', '\\Seen')

    def mark_as_unread(self, uid: str, folder: str = 'INBOX'):
        """Mark email as unseen (IMAP only)."""
        if not self.imap_host:
            logging.warning("mark_as_unread requires IMAP support.")
            return
        with self._get_imap_conn() as server:
            if self._smart_select(server, folder):
                server.store(uid, '-FLAGS', '\\Seen')
