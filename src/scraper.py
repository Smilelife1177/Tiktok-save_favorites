import asyncio
import os
from playwright.async_api import async_playwright

class TikTokScraper:
    def __init__(self, nickname):
        self.nickname = nickname
        self.base_url = f"https://www.tiktok.com/@{nickname}"
        self.user_data_dir = os.path.join(os.getcwd(), "browser_profile")

    async def get_favorite_urls(self, count=100):
        """
        Uses Playwright to scrape favorite video URLs.
        Requires the user to be logged in.
        """
        async with async_playwright() as p:
            # Using persistent context to keep login session
            context = await p.chromium.launch_persistent_context(
                self.user_data_dir,
                headless=False, # Keep it visible so user can log in if needed
                args=["--disable-blink-features=AutomationControlled"]
            )
            
            page = await context.new_page()
            print(f"[*] Navigating to {self.base_url}...")
            await page.goto(self.base_url)
            
            print("[!] Please log in if prompted. If you are already logged in, stay on the page.")
            print("[*] Monitoring page status...")

            # 1. Ensure we are on the Favorites tab
            try:
                # Try multiple ways to find the favorites tab
                fav_tab = None
                
                # Method A: data-e2e
                fav_tab = await page.query_selector('div[data-e2e="favorites-tab"]')
                
                # Method B: Text search (English)
                if not fav_tab:
                    fav_tab = await page.get_by_text("Favorites", exact=True).first
                    if await fav_tab.count() == 0: fav_tab = None
                
                # Method C: Text search (Ukrainian)
                if not fav_tab:
                    fav_tab = await page.get_by_text("Збережене", exact=True).first
                    if await fav_tab.count() == 0: fav_tab = None

                if fav_tab:
                    print("[*] Found Favorites tab. Clicking...")
                    try:
                        # If it's a Locator (Method B/C), we need to handle differently
                        if hasattr(fav_tab, "click"):
                            await fav_tab.click()
                        else:
                            await page.click('div[data-e2e="favorites-tab"]')
                    except:
                        pass
                    await asyncio.sleep(3)
                else:
                    print("[!] Could not auto-detect Favorites tab. PLEASE CLICK IT MANUALLY in the browser window.")
            except Exception as e:
                print(f"[*] Note: Auto-navigation to tab failed. Please ensure you are on the Favorites page.")

            # Increased timeout and more robust waiting logic
            urls = set()
            timeout_limit = 180 # 3 minutes
            start_time = asyncio.get_event_loop().time()
            
            print("[*] Waiting for you to be on the Favorites page and for videos to load...")
            
            while len(urls) < count:
                # Provide feedback every 15 seconds if nothing found
                elapsed = asyncio.get_event_loop().time() - start_time
                
                # 2. Focus strictly on the confirmed favorites selector
                print("[*] Searching for videos with data-e2e='favorites-item'...")
                
                # Primary search for the confirmed favorites items
                # Include video posts and photo/collage posts which may use different URL patterns
                video_elements = await page.query_selector_all(
                    'div[data-e2e="favorites-item"] a[href*="/video/"], '
                    'div[data-e2e="favorites-item"] a[href*="/photo/"], '
                    'div[data-e2e="favorites-item"] a[href*="/item/"]'
                )
                
                if not video_elements:
                    # Fallback to general favorites container if the items are nested differently
                    video_elements = await page.query_selector_all(
                        'div[data-e2e="favorites-list"] a[href*="/video/"], '
                        'div[data-e2e="favorites-list"] a[href*="/photo/"], '
                        'div[data-e2e="favorites-list"] a[href*="/item/"]'
                    )

                if video_elements:
                    for el in video_elements:
                        try:
                            href = await el.get_attribute("href")
                            if href and "/video/" in href:
                                full_url = f"https://www.tiktok.com{href}" if href.startswith("/") else href
                                clean_url = full_url.split('?')[0]
                                if clean_url not in urls:
                                    urls.add(clean_url)
                                    print(f"[+] Found ({len(urls)}/{count}): {clean_url}")
                                    if len(urls) >= count: break
                        except:
                            continue
                
                if len(urls) >= count:
                    break
                
                if not urls:
                    if int(elapsed) % 15 == 0:
                        print(f"[?] Still looking... Current URL: {page.url}")
                        print("[?] Make sure you are on the 'All favorites' tab. Try scrolling down.")
                    await asyncio.sleep(2)
                else:
                    # Scroll to load more
                    print(f"[*] Scrolling to load more favorites... (Current: {len(urls)}/{count})")
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(4)
                
                if elapsed > timeout_limit:
                    print("[-] Timeout: Reached limit.")
                    break

            print(f"[#] Total collected: {len(urls)}")
            
            # Before closing context, enrich photo/item links by extracting direct image URLs
            results = []
            for u in list(urls)[:count]:
                # If link looks like a photo or item (carousel), open it and gather image srcs
                if "/photo/" in u or "/item/" in u:
                    try:
                        print(f"[*] Opening photo/item page to extract images: {u}")
                        await page.goto(u)
                        await asyncio.sleep(1)
                        img_els = await page.query_selector_all('img')
                        img_urls = set()
                        for img in img_els:
                            src = await img.get_attribute('src')
                            if not src:
                                src = await img.get_attribute('data-src')
                            if not src:
                                srcset = await img.get_attribute('srcset')
                                if srcset:
                                    # pick first URL in srcset
                                    src = srcset.split(',')[0].strip().split(' ')[0]
                            if src and not src.startswith('data:'):
                                clean = src.split('?')[0]
                                if clean.startswith('//'):
                                    clean = 'https:' + clean
                                img_urls.add(clean)
                        if img_urls:
                            results.append({'type':'photo', 'page_url': u, 'images': list(img_urls)})
                            print(f"[+] Extracted {len(img_urls)} images from {u}")
                        else:
                            # fallback to returning the page URL for yt-dlp to try
                            results.append(u)
                    except Exception as e:
                        print(f"[-] Failed to extract images from {u}: {e}")
                        results.append(u)
                else:
                    results.append(u)

            # Extract cookies for yt-dlp
            cookies = await context.cookies()
            self.save_cookies_netscape(cookies)

            await context.close()
            return results

    def save_cookies_netscape(self, cookies):
        """Saves cookies in Netscape format for yt-dlp."""
        with open("tiktok_cookies.txt", "w", encoding="utf-8") as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.write("# http://curl.haxx.se/rfc/cookie_spec.html\n")
            f.write("# This is a generated file!  Do not edit.\n\n")
            
            for cookie in cookies:
                # domain, inclusion, path, secure, expiration, name, value
                domain = cookie['domain']
                flag = "TRUE" if domain.startswith(".") else "FALSE"
                path = cookie['path']
                secure = "TRUE" if cookie['secure'] else "FALSE"
                expiry = int(cookie.get('expires', 0))
                if expiry <= 0:
                    expiry = 2147483647
                name = cookie['name']
                value = cookie['value']
                
                f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n")
        print("[*] Cookies saved to tiktok_cookies.txt for yt-dlp.")
