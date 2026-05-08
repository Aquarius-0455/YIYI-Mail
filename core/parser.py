import os
import mimetypes
from email.message import EmailMessage
from email.utils import make_msgid
from typing import List, Union, Dict, Any

class AirParser:
    """
    Handles conversion between Python objects and MIME messages.
    """
    @staticmethod
    def compose(sender: str, recipients: Union[str, List[str]], subject: str, 
                text: str = None, html: str = None, attachments: List[str] = None) -> EmailMessage:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = recipients if isinstance(recipients, str) else ", ".join(recipients)
        
        if text:
            msg.set_content(text)
        
        if html:
            if text:
                msg.add_alternative(html, subtype='html')
            else:
                msg.set_content(html, subtype='html')
                
        if attachments:
            for path in attachments:
                if not os.path.isfile(path):
                    continue
                
                ctype, encoding = mimetypes.guess_type(path)
                if ctype is None or encoding is not None:
                    ctype = 'application/octet-stream'
                maintype, subtype = ctype.split('/', 1)
                
                with open(path, 'rb') as f:
                    msg.add_attachment(
                        f.read(),
                        maintype=maintype,
                        subtype=subtype,
                        filename=os.path.basename(path)
                    )
        return msg

    @staticmethod
    def decompose(msg: EmailMessage) -> Dict[str, Any]:
        """
        Convert a MIME message into a friendly Python dictionary.
        """
        result = {
            'subject': msg.get('Subject'),
            'from': msg.get('From'),
            'to': msg.get('To'),
            'date': msg.get('Date'),
            'content_text': [],
            'content_html': [],
            'attachments': []
        }
        
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            
            filename = part.get_filename()
            if filename:
                result['attachments'].append({
                    'name': filename,
                    'content': part.get_payload(decode=True),
                    'type': part.get_content_type()
                })
            else:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        content = payload.decode(charset, errors='replace')
                        if part.get_content_subtype() == 'html':
                            result['content_html'].append(content)
                        else:
                            result['content_text'].append(content)
                    except:
                        pass
        
        # Flatten content if list has 1 item
        result['content_text'] = "\n".join(result['content_text'])
        result['content_html'] = "\n".join(result['content_html'])
        return result
