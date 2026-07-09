import asyncio
import sys
import argparse
from src.downloader import run_downloader

def main():
    parser = argparse.ArgumentParser(description="TikTok Favorites Downloader")
    parser.add_argument("nickname", help="The TikTok nickname of the user")
    parser.add_argument("--count", type=int, default=100, help="Number of favorite videos to fetch (default: 100)")
    
    args = parser.parse_args()

    print("=== TikTok Favorites Downloader ===")
    print(f"User: {args.nickname}")
    print(f"Count: {args.count}")
    print("===================================")

    try:
        asyncio.run(run_downloader(args.nickname, args.count))
    except KeyboardInterrupt:
        print("\n[!] Process interrupted by user.")
    except Exception as e:
        print(f"\n[!] An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
