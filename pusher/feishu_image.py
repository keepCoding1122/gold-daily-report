"""飞书图片上传 — 通过 Open API 将图表上传到飞书"""

import hashlib
import hmac
import json
import time
from pathlib import Path
from typing import Optional

import requests

from config import Config


class FeishuImageUploader:
    """
    飞书图片上传（需飞书自建应用）

    流程：
      app_id + app_secret → tenant_access_token → upload image → image_key
    然后在 post 消息中用 {"tag": "img", "image_key": "xxx"} 引用
    """

    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self):
        self.app_id = Config.FEISHU_APP_ID
        self.app_secret = Config.FEISHU_APP_SECRET
        self._token: Optional[str] = None
        self._token_expires: float = 0

    @property
    def available(self) -> bool:
        return bool(self.app_id and self.app_secret)

    def _get_tenant_token(self) -> Optional[str]:
        """获取 tenant_access_token"""
        if self._token and time.time() < self._token_expires:
            return self._token

        url = f"{self.BASE_URL}/auth/v3/tenant_access_token/internal"
        resp = requests.post(url, json={
            "app_id": self.app_id,
            "app_secret": self.app_secret,
        }, timeout=10)
        data = resp.json()
        if data.get("code") != 0:
            print(f"  ⚠ 飞书 token 获取失败: {data.get('msg', '')}")
            return None
        self._token = data["tenant_access_token"]
        self._token_expires = time.time() + data.get("expire", 6000) - 60
        return self._token

    def upload_image(self, image_path: str) -> Optional[str]:
        """
        上传图片到飞书

        Args:
            image_path: 本地图片文件路径

        Returns:
            image_key 或 None
        """
        token = self._get_tenant_token()
        if not token:
            return None

        path = Path(image_path)
        if not path.exists():
            print(f"  ⚠ 图片不存在: {image_path}")
            return None

        url = f"{self.BASE_URL}/im/v1/images"
        headers = {"Authorization": f"Bearer {token}"}

        with open(path, "rb") as f:
            resp = requests.post(url, headers=headers, files={
                "image": (path.name, f, "image/png"),
                "image_type": (None, "message"),
            }, timeout=30)

        data = resp.json()
        if data.get("code") != 0:
            print(f"  ⚠ 图片上传失败: {data.get('msg', '')}")
            return None

        image_key = data.get("data", {}).get("image_key", "")
        if image_key:
            print(f"  ✓ 图片已上传: {path.name} → {image_key}")
        return image_key

    def upload_charts(self, chart_paths: list[str]) -> list[str]:
        """批量上传图表，返回 image_key 列表"""
        keys = []
        for path in chart_paths:
            key = self.upload_image(path)
            if key:
                keys.append(key)
        return keys
