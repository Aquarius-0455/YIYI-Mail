import json
import os
from typing import Dict, Any

def show(mail: Dict[str, Any]):
    """
    邮件对象控制台可视化输出。
    """
    if not mail:
        print("Empty email.")
        return
    print("-" * 50)
    print(f"Subject: {mail.get('subject')}")
    print(f"From:    {mail.get('from')}")
    print(f"Date:    {mail.get('date')}")
    print("-" * 50)
    print(f"Text Content: {len(mail.get('content_text', ''))} chars")
    print(f"HTML Content: {len(mail.get('content_html', ''))} chars")
    print(f"Attachments:  {[a['name'] for a in mail.get('attachments', [])]}")
    print("-" * 50)

def save(mail: Dict[str, Any], path: str):
    """
    将邮件对象持久化为 JSON 文件。
    """
    # 处理 JSON 序列化：将二进制内容转为十六进制字符串
    serializable_mail = mail.copy()
    if 'attachments' in serializable_mail:
        serializable_mail['attachments'] = [
            {**a, 'content': a['content'].hex() if isinstance(a['content'], bytes) else a['content']}
            for a in serializable_mail['attachments']
        ]
    if 'inlines' in serializable_mail:
        serializable_mail['inlines'] = [
            {**a, 'content': a['content'].hex() if isinstance(a['content'], bytes) else a['content']}
            for a in serializable_mail['inlines']
        ]

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(serializable_mail, f, ensure_ascii=False, indent=4)

def load(path: str) -> Dict[str, Any]:
    """
    从本地 JSON 文件加载邮件对象并还原二进制数据。
    """
    with open(path, 'r', encoding='utf-8') as f:
        mail = json.load(f)
    
    # 还原二进制数据
    if 'attachments' in mail:
        for attr in mail['attachments']:
            if isinstance(attr['content'], str):
                attr['content'] = bytes.fromhex(attr['content'])
    if 'inlines' in mail:
        for attr in mail['inlines']:
            if isinstance(attr['content'], str):
                attr['content'] = bytes.fromhex(attr['content'])
    return mail

def decode_imap_utf7(s: str) -> str:
    """
    IMAP 专用 Modified UTF-7 解码（参考 RFC 2060/3501）。
    """
    import base64
    res = []
    i = 0
    while i < len(s):
        if s[i] == '&':
            j = s.find('-', i)
            if j == -1:
                res.append(s[i:])
                break
            part = s[i+1:j]
            if not part:
                res.append('&')
            else:
                res.append(base64.b64decode(part.replace(',', '/') + '===').decode('utf-16-be'))
            i = j + 1
        else:
            res.append(s[i])
            i += 1
    return "".join(res)

def encode_imap_utf7(s: str) -> str:
    """
    IMAP 专用 Modified UTF-7 编码（处理中文目录名）。
    """
    import base64
    if s == 'INBOX':
        return 'INBOX'
    res = []
    i = 0
    while i < len(s):
        c = s[i]
        if ord(c) < 32 or ord(c) > 126 or c == '&':
            j = i
            while j < len(s) and (ord(s[j]) < 32 or ord(s[j]) > 126 or s[j] == '&'):
                j += 1
            part = s[i:j].encode('utf-16-be')
            res.append('&' + base64.b64encode(part).decode('ascii').replace('/', ',').rstrip('=') + '-')
            i = j
        else:
            res.append(c)
            i += 1
    return "".join(res)
