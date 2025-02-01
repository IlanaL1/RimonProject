#import pandas

# craw4ai - uses playwright under hood to scrape website, uses browser under the hood
# getting started.
# Script scrapes several urls in parallel, accesses html, parses tags, into markdown format
# for one site - xml, - go to sitemap and get all pages in xml (all pages in navigation)
# Notes robots.txt (add it to url -tells you their rules for webscraping. agents can scrape youtube, but some pages not allow)

import asyncio
from typing import List
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

async def crawl_sequential(urls: List[str]):
    print("\n=== Sequential Crawling with Session Reuse ===")

    browser_config = BrowserConfig(
        headless=True,
        # For better performance in Docker or low-memory environments:
        extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
    )

    crawl_config = CrawlerRunConfig(
        markdown_generator=DefaultMarkdownGenerator()
    )

    # Create the crawler (opens the browser)
    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.start()

    try:
        session_id = "session1"  # Reuse the same session across all URLs
        for url in urls:
            result = await crawler.arun(
                url=url,
                config=crawl_config,
                session_id=session_id
            )
            if result.success:
                print(f"Successfully crawled: {url}")
                # E.g. check markdown length
                print(f"Markdown length: {len(result.markdown_v2.raw_markdown)}")
            else:
                print(f"Failed: {url} - Error: {result.error_message}")
    finally:
        # After all URLs are done, close the crawler (and the browser)
        await crawler.close()

async def main():
    #with open('urls.txt', 'r', encoding='utf-8') as f:
    #        urls = f.readlines().strip("\n")

# supabase client
#    import os
#    from supabase import create_client, Client

#    url: str = os.environ.get("SUPABASE_URL")
#    key: str = os.environ.get("SUPABASE_KEY")
#    supabase: Client = create_client(url, key)

    # supabase API keys
#    Project API: https://czjszavosopbpfcobxal.supabase.co
# API Key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN6anN6YXZvc29wYnBmY29ieGFsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzgxODM5NjksImV4cCI6MjA1Mzc1OTk2OX0.LRtDNwO-CGqQOhW1uM7Oy-9Y4PLv7js_9c-fgCSGtSc


    urls = [
        "https://forward.com/culture/678154/peter-yarrow-remembrance-peter-paul-mary-folk-music-civil-rights/"
        "https://www.theguardian.com/world/2025/jan/07/austrias-far-right-leader-to-invite-centre-right-for-coalition-talks"
        "https://www.haaretz.com/us-news/2025-01-06/ty-article/.premium/bidens-last-multi-billion-arms-sale-to-israel-leaves-an-explosive-legacy/00000194-3b56-d96e-a1d6-3bfe57c30000"
        "https://s2.washingtonpost.com/404a8f0/677d5db064c0860cbc220dec/5edcb490ade4e276b3d867cd/4/13/677d5db064c0860cbc220dec"
    ]
    await crawl_sequential(urls)

if __name__ == "__main__":
    asyncio.run(main())


