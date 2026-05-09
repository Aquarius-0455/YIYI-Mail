<p align="center">
  <img src="https://raw.githubusercontent.com/Aquarius-0455/YIYI-Mail/master/YIYIMail_logo.png" alt="YIYIMail Logo" width="200">
</p>

# YIYIMail 🚀

中文说明 | [English Version](README.md)


YIYIMail 是一个高性能、现代化的 Python 邮件处理库。它旨在替代陈旧的邮件库，提供对 IMAP、POP3 和 SMTP 的完美支持，具备高性能的服务端搜索、优雅的 HTML/CID 解析以及极致的易用性。

## 🌟 核心特性

- **现代协议支持**：完美支持 IMAP、POP3 和 SMTP，自动识别主流个人邮箱（Gmail, Outlook, 163, QQ）及企业邮箱（腾讯、阿里、网易企业邮）。
- **高性能搜索**：利用 IMAP 服务端搜索，瞬间定位目标。支持按**主题、发件人、日期、未读状态**过滤，并支持 **limit** 结果限制。
- **卓越兼容性**：内置 IMAP `ID` 命令支持，完美解决网易、腾讯等厂商的“不安全登录”拦截问题。
- **智能文件夹匹配**：自动处理中文文件夹名的 Modified UTF-7 编码，支持直接使用“已发送”、“草稿箱”等中文名称。
- **优雅的解析器**：自动处理 CID 内联图片，生成 Base64 渲染的 HTML，让邮件在离线状态下也能完美显示。
- **辅助工具箱**：内置 `show()` 美化输出、`save()` / `load()` 本地持久化工具。
- **类型安全**：完全基于 Python 3.7+ 的类型注解。

## 📦 安装

```bash
pip install YIYIMail
```

## 🚀 快速开始

### 1. 连接邮箱
YIYIMail 会根据您的邮箱后缀自动配置服务器地址。

```python
import YIYIMail

# 建议使用授权码（如 163、QQ 邮箱）
mail = YIYIMail.connect('your_name@163.com', 'your_auth_code')

# 也支持企业邮箱（自动识别腾讯、阿里、网易企业邮）
# mail = YIYIMail.connect('admin@exmail.qq.com', 'password')

# 或手动指定服务器
# mail = YIYIMail.connect('user@company.com', 'pwd', smtp_host='smtp.company.com', imap_host='imap.company.com')
```

### 2. 发送邮件
支持多收件人、多附件、HTML 格式。

```python
mail.send(
    recipients=['friend@example.com'],
    subject='你好',
    content='这是一封测试邮件',
    html='<h1>你好</h1><p>YIYIMail 测试成功！</p>',
    attachments=['/path/to/report.pdf']
)
```

### 3. 高级搜索 (IMAP)
无需下载所有邮件，直接让服务器筛选。

```python
# 搜索 2026 年 5 月 1 日之后的邮件，只取最新的 5 封
results = mail.search(after='2026-05-01', subject='报表', limit=5)

# 搜索来自特定发件人的未读邮件
unread_mails = mail.search(sender='boss@company.com', unseen=True)

# 在特定文件夹搜索
sent_items = mail.search(subject='项目进度', folder='已发送')
```

### 4. 获取与展示
```python
# 获取最新一封邮件
latest = mail.fetch_latest()

# 获取收件箱前 10 封
mails = mail.fetch_mails(start=1, end=10)

# 漂亮地打印邮件内容
YIYIMail.show(latest)
```

### 5. 状态管理
```python
uid = latest['uid']
mail.mark_as_read(uid)    # 标记为已读
mail.mark_as_unread(uid)  # 标记为未读
```

### 6. 持久化存储
```python
# 保存到本地 JSON
YIYIMail.save(latest, 'my_mail.json')

# 从本地加载
local_mail = YIYIMail.load('my_mail.json')
```

### 7. 邮箱信息
```python
# 获取邮箱统计信息 (邮件总数, 占用空间)
stats = mail.info()
print(f"邮件总数: {stats['count']}, 总大小: {stats['size_bytes']} bytes")
```

## 🛠️ 文件夹管理
通过 `mail.folders()` 获取服务器上真实的文件夹列表（已自动解码为中文）。

```python
folders = mail.folders()
print(folders) 
# 输出: ['INBOX', '草稿箱', '已发送', '已删除', '垃圾邮件', ...]
```

## ⚖️ 开源协议
MIT License
