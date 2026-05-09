import os
import mimetypes
from email.message import EmailMessage
from email.utils import make_msgid
from typing import List, Union, Dict, Any

class AirParser:
    """
    邮件处理类，负责 Python 对象与 MIME 格式的互转。
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
        解析 MIME 消息为字典格式，支持嵌套结构、附件提取及 CID 资源映射。
        """
        result = {
            'subject': msg.get('Subject'),
            'from': msg.get('From'),
            'to': msg.get('To'),
            'date': msg.get('Date'),
            'content_text': [],
            'content_html': [],
            'attachments': [],
            'inlines': []
        }
        
        cid_map = {}
        
        for part in msg.walk():
            content_type = part.get_content_type()
            maintype = part.get_content_maintype()
            
            if maintype == 'multipart':
                continue
            
            filename = part.get_filename()
            cid = part.get('Content-ID')
            if cid:
                cid = cid.strip('<>')
            
            payload = part.get_payload(decode=True)
            if not payload:
                continue

            if filename:
                # Regular attachment
                result['attachments'].append({
                    'name': filename,
                    'content': payload,
                    'type': content_type,
                    'cid': cid
                })
            elif cid:
                # Inline resource (embedded images, etc.)
                inline_data = {
                    'cid': cid,
                    'content': payload,
                    'type': content_type
                }
                result['inlines'].append(inline_data)
                cid_map[cid] = inline_data
            else:
                # Body payload
                charset = part.get_content_charset() or 'utf-8'
                try:
                    content = payload.decode(charset, errors='replace')
                    if part.get_content_subtype() == 'html':
                        result['content_html'].append(content)
                    else:
                        result['content_text'].append(content)
                except:
                    pass
        
        result['content_text'] = "\n".join(result['content_text'])
        html_content = "\n".join(result['content_html'])
        
        # 提取 HTML 并处理 CID 资源映射（用于内联显示图片）
        # We also provide a raw version
        result['content_html'] = html_content
        
        # 自动生成：将图片转为 Base64 嵌入 HTML（用于离线预览）
        if html_content and result['inlines']:
            import base64
            rendered_html = html_content
            for cid, data in cid_map.items():
                if data['type'].startswith('image/'):
                    b64_data = base64.b64encode(data['content']).decode()
                    src = f"data:{data['type']};base64,{b64_data}"
                    rendered_html = rendered_html.replace(f"cid:{cid}", src)
            result['rendered_html'] = rendered_html
            
        return result
