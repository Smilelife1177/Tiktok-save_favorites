import asyncio
import os
from playwright.async_api import async_playwright

class TikTokScraper:
    def __init__(self, nickname):
        self.nickname = nickname
        self.base_url = f"https://www.tiktok.com/@{nickname}/video/favorites"
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
                # Wait for the tab to be available
                fav_tab_selector = 'div[data-e2e="favorites-tab"]'
                await page.wait_for_selector(fav_tab_selector, timeout=30000)
                
                # Check if it's already selected (usually has a specific class or underline)
                # If not, click it
                print("[*] Clicking Favorites tab to be sure...")
                await page.click(fav_tab_selector)
                await asyncio.sleep(2)
            except Exception as e:
                print(f"[*] Could not find/click Favorites tab explicitly: {e}. Hope we are already there.")

            # Increased timeout and more robust waiting logic
            urls = set()
            timeout_limit = 120 # 2 minutes
            start_time = asyncio.get_event_loop().time()
            
            while len(urls) < count:
                current_url = page.url
                if "login" in current_url:
                    print("[!] Current page: Login. Waiting for you to finish login...")
                else:
                    # Look for the grid specifically under the favorites section
                    # Sometimes the container ID or class changes when a tab is clicked
                    print("[*] Searching for videos in Favorites grid...")

                # 2. Focus strictly on the active video grid
                # The favorites videos are usually in a div with data-e2e="user-post-item-list"
                # but we want to make sure it's the one under the favorites section.
                # We'll use a more specific selector if possible.
                video_elements = await page.query_selector_all('div[data-e2e="user-post-item-list"] a[href*="/video/"]')
                
                if not video_elements:
                    # Fallback to general item but filtered
                    all_items = await page.query_selector_all('div[data-e2e="user-post-item"]')
                    video_elements = []
                    for item in all_items:
                        # Check if this item is in a "recommend" or "related" section
                        is_bad = await item.evaluate('''(el) => {
                            let p = el.parentElement;
                            while(p) {
                                if(p.innerText.includes("You may like") || p.innerText.includes("Recommended")) return true;
                                p = p.parentElement;
                            }
                            return false;
                        }''')
                        if not is_bad:
                            link = await item.query_selector('a[href*="/video/"]')
                            if link:
                                video_elements.append(link)

                if video_elements:
                    for el in video_elements:
                        href = await el.get_attribute("href")
                        if href and "/video/" in href:
                            # Prepend domain if it's a relative path
                            full_url = href
                            if href.startswith("/"):
                                full_url = f"https://www.tiktok.com{href}"
                            
                            clean_url = full_url.split('?')[0]
                            if clean_url not in urls:
                                urls.add(clean_url)
                                print(f"[+] Found: {clean_url}")
                                
                                # Optimization: check count inside inner loop
                                if len(urls) >= count:
                                    break
                
                if len(urls) >= count:
                    break
                
                # Check for timeout if no videos found at all
                if not urls and (asyncio.get_event_loop().time() - start_time) > timeout_limit:
                    print("[-] Timeout: No favorites found after 2 minutes.")
                    break

                if urls:
                    # Scroll to load more
                    print(f"[*] Collected {len(urls)}/{count}. Scrolling down...")
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(3) # Wait for content to load
                    
                    # Check if we reached the bottom
                    new_height = await page.evaluate("document.body.scrollHeight")
                    # We can store last_height outside to be more precise, but this loop is fine
                else:
                    # Just wait and check again
                    await asyncio.sleep(5)

            print(f"[#] Final count of unique URLs collected: {len(urls)}")
            
            # Extract cookies for yt-dlp
            cookies = await context.cookies()
            self.save_cookies_netscape(cookies)

            await context.close()
            return list(urls)[:count]

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
                name = cookie['name']
                value = cookie['value']
                
                f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}\n")
        print("[*] Cookies saved to tiktok_cookies.txt for yt-dlp.")
