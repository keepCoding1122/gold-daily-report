"""飞书群机器人推送"""

import hashlib
import hmac
import json
import time
from typing import Optional

import requests

from config import Config


class FeishuBot:
    """飞书自定义机器人推送"""

    WEBHOOK_URL = Config.FEISHU_WEBHOOK_URL
    SECRET = Config.FEISHU_SECRET

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def _sign(self, timestamp: int) -> Optional[str]:
        """签名算法（如开启了签名校验）"""
        if not self.SECRET:
            return None
        string_to_sign = f"{timestamp}\n{self.SECRET}"
        h = hmac.new(
            self.SECRET.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        )
        return h.hexdigest()

    def send(self, payload: dict) -> dict:
        """发送消息到飞书群"""
        if "your_token" in self.WEBHOOK_URL:
            print("⚠️  飞书 Webhook URL 未配置，跳过推送")
            print("   请先创建飞书群机器人，将 URL 填入 .env 的 FEISHU_WEBHOOK_URL")
            print(f"   消息内容预览（前 200 字）：")
            title = payload.get("content", {}).get("post", {}).get("zh_cn", {}).get("title", "")
            print(f"   {title}")
            return {"code": -1, "msg": "webhook not configured"}

        # 签名
        timestamp = int(time.time())
        sign = self._sign(timestamp)
        if sign:
            payload["timestamp"] = str(timestamp)
            payload["sign"] = sign

        # 发送
        resp = self.session.post(self.WEBHOOK_URL, json=payload, timeout=15)
        result = resp.json()

        if result.get("code") == 0:
            print(f"✅ 飞书推送成功")
        else:
            print(f"❌ 飞书推送失败: {result.get('msg', 'unknown')} (code={result.get('code')})")

        return result

    def send_text(self, text: str) -> dict:
        """发送纯文本消息"""
        payload = {
            "msg_type": "text",
            "content": {"text": text},
        }
        return self.send(payload)

    def send_rich_text(self, title: str, content_blocks: list) -> dict:
        """发送富文本消息"""
        payload = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": title,
                        "content": content_blocks,
                    }
                }
            },
        }
        return self.send(payload)
