import os
import asyncio
import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget
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

        ydl_opts_no_cookies = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': f'{self.download_path}/%(uploader)s/%(title)s.%(ext)s',
            'quiet': False,
            'no_warnings': False,
            'ignoreerrors': True,
            # allow yt-dlp to extract info without immediately failing on thumbnails-only posts
            'skip_download': False,
            'impersonate': ImpersonateTarget.from_str('chrome'),
        }

        ydl_opts_with_cookies = ydl_opts_no_cookies.copy()
        ydl_opts_with_cookies['cookiefile'] = 'tiktok_cookies.txt'

        successful_count = 0
        downloaded_folders = set()

        print(f"[*] Starting processing of {len(urls)} items (videos and photos)...")
        with yt_dlp.YoutubeDL(ydl_opts_no_cookies) as ydl, yt_dlp.YoutubeDL(ydl_opts_with_cookies) as ydl_cookies:
            for url in urls:
                info = None
                active_ydl = ydl
                
                # Attempt to extract info without cookies first
                try:
                    info = ydl.extract_info(url, download=False)
                except Exception as e:
                    print(f"[-] yt-dlp failed to extract info without cookies for {url}: {e}")
                    info = None

                # Fallback to cookies if first attempt failed
                if info is None:
                    print(f"[*] Retrying extraction with cookies for {url}...")
                    try:
                        info = ydl_cookies.extract_info(url, download=False)
                        active_ydl = ydl_cookies
                    except Exception as e:
                        print(f"[-] yt-dlp failed to extract info with cookies for {url}: {e}")
                        info = None

                # Fallback directly to download if extraction completely failed
                if info is None:
                    # attempt to download via yt-dlp directly as a fallback
                    print(f"[-] Failed to extract info for {url}, attempting direct download...")
                    uploader = 'unknown'
                    try:
                        parts = url.split('/')
                        for p in parts:
                            if p.startswith('@'):
                                uploader = p[1:]
                                break
                    except Exception:
                        pass
                    
                    download_success = False
                    try:
                        if ydl.download([url]) == 0:
                            download_success = True
                    except Exception as e2:
                        print(f"[-] Direct download without cookies failed for {url}: {e2}. Trying with cookies...")
                        try:
                            if ydl_cookies.download([url]) == 0:
                                download_success = True
                        except Exception as e3:
                            print(f"[-] Direct download with cookies also failed for {url}: {e3}")
                    
                    if download_success:
                        successful_count += 1
                        downloaded_folders.add(sanitize_filename(uploader))
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
                        saved_any = False
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
                                saved_any = True
                            except Exception as e:
                                print(f"[-] Failed to download image {img_url}: {e}")
                        if saved_any:
                            successful_count += 1
                            downloaded_folders.add(sanitize_filename(uploader))
                        continue
                    else:
                        print(f"[-] No direct images found for {page_url}, falling back to yt-dlp")
                        try:
                            if active_ydl.download([page_url]) == 0:
                                successful_count += 1
                                downloaded_folders.add(sanitize_filename(uploader))
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
                    if downloaded:
                        successful_count += 1
                        downloaded_folders.add(sanitize_filename(uploader))
                    else:
                        print(f"[-] No image thumbnails found for {url}. Trying yt-dlp download as fallback.")
                        try:
                            if active_ydl.download([url]) == 0:
                                successful_count += 1
                                downloaded_folders.add(sanitize_filename(uploader))
                        except Exception as e:
                            print(f"[-] yt-dlp failed for {url}: {e}")
                    continue

                # Otherwise, treat as a regular video post and download with yt-dlp
                try:
                    print(f"[*] Downloading video with yt-dlp: {url}")
                    if active_ydl.download([url]) == 0:
                        successful_count += 1
                        downloaded_folders.add(sanitize_filename(uploader))
                except Exception as e:
                    print(f"[-] yt-dlp failed to download {url}: {e}")

        print("\n===================================")
        print("[+] Processing complete.")
        print(f"[+] Total successfully downloaded: {successful_count}")
        if downloaded_folders:
            print("[+] Downloaded folders (users):")
            for folder in sorted(downloaded_folders):
                print(f"  - {folder}")
        else:
            print("[-] No folders were created/downloaded.")
        print("===================================")


async def run_downloader(nickname, count=100):
    downloader = TikTokDownloader(nickname)
    urls = await downloader.get_favorite_urls(count=count)
    if urls:
        downloader.download_videos(urls)
    else:
        print("[-] Could not retrieve favorite URLs. Check your login in the browser window.")
