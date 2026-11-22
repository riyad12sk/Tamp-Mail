import aiohttp
from config import settings

class TempMailError(Exception):
    pass

class TempMailClient:
    def __init__(self):
        self.base = settings.tempmail_api_base.rstrip("/")

    async def create(self):
        url = f"{self.base}/email/new"
        payload = {"min_name_length": 10, "max_name_length": 10}
        timeout = aiohttp.ClientTimeout(total=20)
        headers = {"accept": "application/json", "content-type": "application/json"}
        try:
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.post(url, json=payload) as response:
                    if response.status >= 400:
                        raise TempMailError(f"Email provider returned HTTP {response.status}")
                    data = await response.json(content_type=None)
            email = data.get("email")
            token = data.get("token")
            if not email:
                raise TempMailError("Provider response did not contain an email address.")
            return email, token
        except (aiohttp.ClientError, TimeoutError, ValueError) as exc:
            raise TempMailError(f"Could not contact email provider: {exc}") from exc

    async def messages(self, email, token=None):
        url = f"{self.base}/email/{email}/messages"
        headers = {"accept": "application/json"}
        timeout = aiohttp.ClientTimeout(total=20)
        try:
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(url) as response:
                    if response.status == 404:
                        return []
                    if response.status >= 400:
                        raise TempMailError(f"Inbox provider returned HTTP {response.status}")
                    data = await response.json(content_type=None)
            return data if isinstance(data, list) else data.get("messages", [])
        except (aiohttp.ClientError, TimeoutError, ValueError) as exc:
            raise TempMailError(f"Could not fetch inbox: {exc}") from exc

client = TempMailClient()
