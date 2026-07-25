import httpx
from typing import Optional, List
import asyncio

class ExternalAPI:
    def __init__(self, base_url: str, candidate_id: Optional[str] = None):
        self.base_url = base_url
        self.candidate_id = candidate_id
    async def get_names(self):
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/files/names",
                    headers={"X-Candidate-Id": self.candidate_id}
                )
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    print(f"429, {retry_after} секунд")
                    await asyncio.sleep(retry_after)
                    return await self.get_names()
                
                if response.status_code == 403:
                    retry_after = int(response.headers.get("Retry-After", 1800))
                    print(f"заблокирован на {retry_after} секунд")
                    await asyncio.sleep(retry_after)
                    return await self.get_names()
                
                response.raise_for_status()
                data = response.json()
                return data.get("file_names", [])
                
            except httpx.HTTPStatusError as e:
                print(f"Ошибка HTTP: {e}")
                raise

    async def download_files(self, file_names: List[str]) -> bytes:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{self.base_url}/api/files/download", json={"file_names": file_names})
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    print(f"429, {retry_after} секунд")
                    await asyncio.sleep(retry_after)
                    return await self.get_names()
                                
                if response.status_code == 403:
                    retry_after = int(response.headers.get("Retry-After", 1800))
                    print(f"заблокирован на {retry_after} секунд")
                    await asyncio.sleep(retry_after)
                    return await self.get_names()
                return response.content
            except httpx.HTTPStatusError as e:
                print(f"Ошибка HTTP: {e}")
                raise

    async def mark_files(self, file_names: List[str]):
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{self.base_url}/api/files/downloaded", json={"file_names": file_names})
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    print(f"429, {retry_after} секунд")
                    await asyncio.sleep(retry_after)
                    return await self.get_names()
                                                
                if response.status_code == 403:
                    retry_after = int(response.headers.get("Retry-After", 1800))
                    print(f"заблокирован на {retry_after} секунд")
                    await asyncio.sleep(retry_after)
                    return await self.get_names()
                response.raise_for_status()
                return response.json
            except httpx.HTTPStatusError as e:
                 print(f"Ошибка HTTP: {e}")
                 raise