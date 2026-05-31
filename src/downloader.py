import os
import asyncio
import yt_dlp
from src.scraper import TikTokScraper
from dotenv import load_dotenv

load_dotenv()

class TikTokDownloader:
    def __init__(self, nickname):
        self.nickname = nickname
        self.browser = os.getenv("BROWSER_FOR_COOKIES", "chrome")
        self.download_path = "downloads"

    async def get_favorite_urls(self, count=100):
        """Fetches favorite video URLs for the user using Playwright Scraper."""
        scraper = TikTokScraper(self.nickname)
        return await scraper.get_favorite_urls(count=count)

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
            'cookiefile': 'tiktok_cookies.txt',
            'quiet': False,
            'no_warnings': False,
            'ignoreerrors': True,
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
        print("[-] Could not retrieve favorite URLs. Check your login in the browser window.")
