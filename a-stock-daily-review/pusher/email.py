#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件推送器
实现邮件推送功能
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, Dict, List, Any

from logger import logger
from pusher.base import BasePusher


class EmailPusher(BasePusher):
    """邮件推送器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化邮件推送器
        
        Args:
            config: 邮件配置，包含 smtp_host, smtp_port, smtp_user, smtp_password, from_email, to_emails
        """
        super().__init__(config)
        self.smtp_host = config.get('smtp_host', '')
        self.smtp_port = config.get('smtp_port', 587)
        self.smtp_user = config.get('smtp_user', '')
        self.smtp_password = config.get('smtp_password', '')
        self.from_email = config.get('from_email', '')
        self.to_emails = config.get('to_emails', [])
        
        # 确保 to_emails 是列表
        if isinstance(self.to_emails, str):
            self.to_emails = [e.strip() for e in self.to_emails.split(',') if e.strip()]
    
    def _create_message(self, 
                        subject: str, 
                        body: str, 
                        to_emails: List[str],
                        attachments: Optional[List[str]] = None) -> MIMEMultipart:
        """
        创建邮件消息
        
        Args:
            subject: 邮件主题
            body: 邮件正文
            to_emails: 收件人列表
            attachments: 附件路径列表
            
        Returns:
            MIMEMultipart 消息对象
        """
        msg = MIMEMultipart()
        msg['From'] = self.from_email
        msg['To'] = ', '.join(to_emails)
        msg['Subject'] = subject
        
        # 添加正文
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 添加附件
        if attachments:
            for file_path in attachments:
                if not os.path.exists(file_path):
                    logger.warning(f"附件文件不存在: {file_path}")
                    continue
                
                file_name = os.path.basename(file_path)
                
                # 读取文件并编码
                with open(file_path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{file_name}"'
                )
                msg.attach(part)
        
        return msg
    
    def _send_email(self, msg: MIMEMultipart, to_emails: List[str]) -> bool:
        """
        发送邮件
        
        Args:
            msg: 邮件消息
            to_emails: 收件人列表
            
        Returns:
            是否发送成功
        """
        try:
            logger.info(f"发送邮件到: {', '.join(to_emails)}")
            
            # 连接 SMTP 服务器
            if self.smtp_port == 465:
                # 使用 SSL
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
            else:
                # 使用 STARTTLS
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.ehlo()
                server.starttls()
                server.ehlo()
            
            # 登录
            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)
            
            # 发送邮件
            server.sendmail(self.from_email, to_emails, msg.as_string())
            server.quit()
            
            logger.info("邮件发送成功")
            return True
            
        except Exception as e:
            logger.error(f"发送邮件异常: {e}")
            return False
    
    def push(self, title: str, content: str, file_path: Optional[str] = None) -> bool:
        """
        推送消息
        
        Args:
            title: 消息标题（邮件主题）
            content: 消息内容（邮件正文）
            file_path: 附件文件路径（可选）
            
        Returns:
            是否推送成功
        """
        if not self.enabled:
            logger.info("邮件推送已禁用，跳过")
            return False
        
        if not self.smtp_host or not self.from_email or not self.to_emails:
            logger.warning("邮件配置不完整，无法推送")
            return False
        
        attachments = [file_path] if file_path else None
        return self._push_with_attachments(title, content, attachments)
    
    def push_file(self, file_path: str, title: Optional[str] = None) -> bool:
        """
        推送文件
        
        Args:
            file_path: 文件路径
            title: 文件标题（邮件主题，可选）
            
        Returns:
            是否推送成功
        """
        if not self.enabled:
            logger.info("邮件推送已禁用，跳过")
            return False
        
        if not self.smtp_host or not self.from_email or not self.to_emails:
            logger.warning("邮件配置不完整，无法推送")
            return False
        
        import os
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return False
        
        file_name = os.path.basename(file_path)
        subject = title or f"A股每日复盘报告 - {file_name}"
        body = f"请查看附件中的复盘报告。\n\n文件: {file_name}"
        
        return self._push_with_attachments(subject, body, [file_path])
    
    def _push_with_attachments(self, 
                                subject: str, 
                                body: str, 
                                attachments: Optional[List[str]] = None) -> bool:
        """
        推送带附件的邮件
        
        Args:
            subject: 邮件主题
            body: 邮件正文
            attachments: 附件列表
            
        Returns:
            是否推送成功
        """
        try:
            # 创建邮件消息
            msg = self._create_message(
                subject=subject,
                body=body,
                to_emails=self.to_emails,
                attachments=attachments
            )
            
            # 发送邮件
            return self._send_email(msg, self.to_emails)
            
        except Exception as e:
            logger.error(f"推送邮件异常: {e}")
            return False
