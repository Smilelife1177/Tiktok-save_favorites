import os
import asyncio
import yt_dlp
from TikTokApi import TikTokApi
from dotenv import load_dotenv

load_dotenv()

class TikTokDownloader:
    def __init__(self, nickname):
        self.nickname = nickname
        self.ms_token = os.getenv("TIKTOK_MS_TOKEN")
        self.browser = os.getenv("BROWSER_FOR_COOKIES", "chrome")
        self.download_path = "downloads"

    async def get_favorite_urls(self, count=100):
        """Fetches favorite video URLs for the user."""
        print(f"[*] Fetching favorites for @{self.nickname}...")
        urls = []
        try:
            async with TikTokApi() as api:
                await api.create_sessions(ms_tokens=[self.ms_token], num_sessions=1, sleep_after=3)
                user = api.user(username=self.nickname)
                
                async for video in user.favorites(count=count):
                    url = f"https://www.tiktok.com/@{video.author.username}/video/{video.id}"
                    urls.append(url)
                    
            print(f"[+] Found {len(urls)} videos in favorites.")
            return urls
        except Exception as e:
            print(f"[-] Error fetching favorites: {e}")
            print("[!] Make sure your TIKTOK_MS_TOKEN is correct and you are logged in.")
            return []

    def download_videos(self, urls):
        """Downloads videos from a list of URLs using yt-dlp."""
        if not urls:
            print("[-] No URLs to download.")
            return

        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': f'{self.download_path}/%(uploader)s/%(title)s.%(ext)s',
            'cookiesfrombrowser': (self.browser,),
            'quiet': False,
            'no_warnings': False,
        }

        print(f"[*] Starting download of {len(urls)} videos...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download(urls)
        print("[+] Download complete.")

async def run_downloader(nickname, count=100):
    downloader = TikTokDownloader(nickname)
    urls = await downloader.get_favorite_urls(count=count)
    if urls:
        downloader.download_videos(urls)
    else:
        print("[-] Could not retrieve favorite URLs. Check your authentication.")
