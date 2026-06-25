import os
import asyncio
import yt_dlp
import requests
from src.scraper import TikTokScraper
from src.utils import sanitize_filename
from dotenv import load_dotenv

load_dotenv()

class TikTokDownloader:
    def __init__(self, nickname):
        self.nickname = nickname
        self.browser = os.getenv("BROWSER_FOR_COOKIES", "chrome")
        self.download_path = "downloads"

    async def get_favorite_urls(self, count=100):
        """Fetches favorite URLs (videos and photo posts) using Playwright Scraper."""
        scraper = TikTokScraper(self.nickname)
        return await scraper.get_favorite_urls(count=count)

    def _download_images_from_info(self, info, out_dir):
        """Download image thumbnails found in yt-dlp info dict."""
        thumbnails = info.get("thumbnails") or []
        if not thumbnails:
            return False

        title = info.get("title") or "untitled"
        for i, thumb in enumerate(thumbnails, start=1):
            img_url = thumb.get("url")
            if not img_url:
                continue
            img_url = img_url.split("?")[0]
            ext = os.path.splitext(img_url)[1] or ".jpg"
            filename = sanitize_filename(f"{title}_{i}{ext}")
            dest = os.path.join(out_dir, filename)
            try:
                with requests.get(img_url, stream=True, timeout=30) as r:
                    r.raise_for_status()
                    with open(dest, "wb") as f:
                        for chunk in r.iter_content(8192):
                            f.write(chunk)
                print(f"[+] Saved image: {dest}")
            except Exception as e:
                print(f"[-] Failed to download image {img_url}: {e}")
        return True

    def download_videos(self, urls):
        """Downloads videos and photo posts from a list of URLs using yt-dlp and fallback image download."""
        if not urls:
            print("[-] No URLs to download.")
            return

        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path, exist_ok=True)

        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': f'{self.download_path}/%(uploader)s/%(title)s.%(ext)s',
            'cookiefile': 'tiktok_cookies.txt',
            'quiet': False,
            'no_warnings': False,
            'ignoreerrors': True,
            # allow yt-dlp to extract info without immediately failing on thumbnails-only posts
            'skip_download': False,
        }

        print(f"[*] Starting processing of {len(urls)} items (videos and photos)...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for url in urls:
                try:
                    info = ydl.extract_info(url, download=False)
                except Exception as e:
                    print(f"[-] yt-dlp failed to extract info for {url}: {e}")
                    # attempt to download via yt-dlp directly as a fallback
                    try:
                        ydl.download([url])
                    except Exception as e2:
                        print(f"[-] yt-dlp fallback download also failed for {url}: {e2}")
                    continue

                # If the scraper returned a dict describing a photo/item post, handle directly
                if isinstance(url, dict) and url.get('type') == 'photo':
                    page_url = url.get('page_url')
                    images = url.get('images') or []
                    uploader = 'unknown'
                    # Try to infer uploader from the page_url: https://www.tiktok.com/@username/...
                    try:
                        parts = page_url.split('/')
                        for p in parts:
                            if p.startswith('@'):
                                uploader = p[1:]
                                break
                    except Exception:
                        pass
                    out_dir = os.path.join(self.download_path, sanitize_filename(uploader))
                    os.makedirs(out_dir, exist_ok=True)
                    if images:
                        print(f"[*] Downloading {len(images)} images from photo post: {page_url}")
                        for i, img_url in enumerate(images, start=1):
                            try:
                                ext = os.path.splitext(img_url)[1] or '.jpg'
                                filename = sanitize_filename(f"photo_{i}{ext}")
                                dest = os.path.join(out_dir, filename)
                                with requests.get(img_url, stream=True, timeout=30) as r:
                                    r.raise_for_status()
                                    with open(dest, 'wb') as f:
                                        for chunk in r.iter_content(8192):
                                            f.write(chunk)
                                print(f"[+] Saved image: {dest}")
                            except Exception as e:
                                print(f"[-] Failed to download image {img_url}: {e}")
                        continue
                    else:
                        print(f"[-] No direct images found for {page_url}, falling back to yt-dlp")
                        try:
                            ydl.download([page_url])
                        except Exception as e:
                            print(f"[-] yt-dlp fallback failed for {page_url}: {e}")
                        continue

                # Prepare output directory based on uploader
                uploader = info.get('uploader') or 'unknown'
                out_dir = os.path.join(self.download_path, sanitize_filename(uploader))
                os.makedirs(out_dir, exist_ok=True)

                # If the extracted info has thumbnails but no video formats, treat as photo/collage post
                formats = info.get('formats') or []
                if (not formats or all((f.get('vcodec') in (None, 'none') for f in formats))) and info.get('thumbnails'):
                    print(f"[*] Detected photo post: {url}. Downloading images...")
                    downloaded = self._download_images_from_info(info, out_dir)
                    if not downloaded:
                        print(f"[-] No image thumbnails found for {url}. Trying yt-dlp download as fallback.")
                        try:
                            ydl.download([url])
                        except Exception as e:
                            print(f"[-] yt-dlp failed for {url}: {e}")
                    continue

                # Otherwise, treat as a regular video post and download with yt-dlp
                try:
                    print(f"[*] Downloading video with yt-dlp: {url}")
                    ydl.download([url])
                except Exception as e:
                    print(f"[-] yt-dlp failed to download {url}: {e}")

        print("[+] Processing complete.")


async def run_downloader(nickname, count=100):
    downloader = TikTokDownloader(nickname)
    urls = await downloader.get_favorite_urls(count=count)
    if urls:
        downloader.download_videos(urls)
    else:
        print("[-] Could not retrieve favorite URLs. Check your login in the browser window.")
