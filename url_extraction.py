# this code (claude.ai generated) extracts urls from a JSON file input.json
# input.json was output from appify - convert facebook groups to json
# output of this file is external_links.md and facebook_links.md
import json
from datetime import datetime
import argparse
from typing import Dict, List, Any, Union
import os
from urllib.parse import urlparse, unquote


def clean_url(url: str) -> str:
    """Clean URL by removing query parameters and unescaping characters."""
    if not url:
        return url

    # Don't clean Facebook CDN image URLs as they require all parameters
    if 'fbcdn.net' in url:
        return url

    # Unescape URL-encoded characters
    url = unquote(url)

    # Parse URL and remove query parameters
    parsed = urlparse(url)
    cleaned = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    return cleaned.strip()


def extract_image_info(item: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract image information including both CDN and permanent Facebook URLs."""
    images = []

    # Check for media array
    if 'media' in item:
        for media_item in item.get('media', []):
            if media_item.get('__typename') == 'Photo':
                image_info = {
                    'facebook_url': media_item.get('url'),  # Permanent Facebook photo.php URL
                    'cdn_url': media_item.get('photo_image', {}).get('uri'),  # Temporary CDN URL
                    'width': media_item.get('photo_image', {}).get('width'),
                    'height': media_item.get('photo_image', {}).get('height'),
                    'description': media_item.get('ocrText')
                }
                images.append(image_info)

    # Check shared post media
    if 'sharedPost' in item and 'media' in item['sharedPost']:
        for media_item in item['sharedPost'].get('media', []):
            if media_item.get('__typename') == 'Photo':
                image_info = {
                    'facebook_url': media_item.get('url'),
                    'cdn_url': media_item.get('photo_image', {}).get('uri'),
                    'width': media_item.get('photo_image', {}).get('width'),
                    'height': media_item.get('photo_image', {}).get('height'),
                    'description': media_item.get('ocrText')
                }
                images.append(image_info)

    return images


def get_post_date(item: Dict[str, Any]) -> str:
    """Extract the original post date, prioritizing the main post date over shared post date."""
    # First try to get the main post time
    if 'time' in item and item['time']:
        return item['time']

    # If no main post time, try to get shared post time
    if 'sharedPost' in item and isinstance(item['sharedPost'], dict):
        if 'time' in item['sharedPost'] and item['sharedPost']['time']:
            return item['sharedPost']['time']

    return None


def get_profiles(item: Dict[str, Any]) -> Dict[str, str]:
    """Extract both main profile and shared profile information."""
    profiles = {}

    # Get main poster's profile
    if 'user' in item and isinstance(item['user'], dict) and 'name' in item['user']:
        profiles['Profile'] = item['user']['name']

    # Get shared post profile if it exists
    if 'sharedPost' in item:
        shared = item['sharedPost']
        if isinstance(shared, dict):
            if 'user' in shared and isinstance(shared['user'], dict) and 'name' in shared['user']:
                profiles['ProfileShared'] = shared['user']['name']
            elif 'pageName' in shared and isinstance(shared['pageName'], dict) and 'name' in shared['pageName']:
                profiles['ProfileShared'] = shared['pageName']['name']

    return profiles


def is_clean_url(url: str) -> bool:
    """Determine if a URL is 'clean' (belongs to a known domain and isn't a CDN/media URL)."""
    if not url:
        return False

    # URLs to consider not clean
    unclean_patterns = [
        'fbcdn.net',
        'scontent',
        'amazonaws.com',
        'akamaized.net',
        'cloudfront.net',
        '/cdn-cgi/',
    ]

    return not any(pattern in url.lower() for pattern in unclean_patterns)


def find_value_in_dict(obj: Union[Dict, List, Any], key: str) -> List[Any]:
    """Recursively find all values for a given key in a nested structure."""
    results = []

    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                results.append(v)
            if isinstance(v, (dict, list)):
                results.extend(find_value_in_dict(v, key))
    elif isinstance(obj, list):
        for item in obj:
            results.extend(find_value_in_dict(item, key))

    return results


def find_urls_in_text(text: str) -> List[str]:
    """Extract URLs from text content."""
    if not isinstance(text, str):
        return []
    words = text.split()
    urls = [word for word in words if word.startswith('http')]
    return [clean_url(url) for url in urls]


def extract_all_urls(item: Dict[str, Any]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Extract all URLs from an item regardless of nesting level."""
    facebook_urls = []
    external_urls = []

    # Get profile information
    profiles = get_profiles(item)

    # Get image information
    images = extract_image_info(item)

    # Get post date
    post_date = get_post_date(item)

    # Find all possible URL-containing keys
    url_keys = ['url', 'link', 'uri', 'href', 'profileUrl']

    # Collect all URLs from all possible keys
    all_urls = []
    for key in url_keys:
        found_urls = find_value_in_dict(item, key)
        all_urls.extend(found_urls)

    # Find URLs in text content
    text_contents = find_value_in_dict(item, 'text')
    for text in text_contents:
        all_urls.extend(find_urls_in_text(text))

    # Get metadata
    metadata = {
        'date': post_date,
        'title': find_value_in_dict(item, 'title')[0] if find_value_in_dict(item, 'title') else None,
        'description': find_value_in_dict(item, 'previewDescription')[0] if find_value_in_dict(item,
                                                                                               'previewDescription') else None
    }

    # Add profile information to metadata
    metadata.update(profiles)

    # Add image information to metadata if present
    if images:
        metadata['images'] = images

    # Process each URL
    seen_urls = set()
    for url in all_urls:
        if url and isinstance(url, str) and url.startswith('http'):
            cleaned_url = clean_url(url)
            if cleaned_url not in seen_urls:
                seen_urls.add(cleaned_url)
                url_data = {
                    'url': cleaned_url,
                    **metadata
                }

                if 'facebook.com' in cleaned_url:
                    facebook_urls.append(url_data)
                else:
                    external_urls.append(url_data)

    return facebook_urls, external_urls


def merge_url_items(urls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge items that belong to the same post based on timestamp and select the cleanest URL."""
    # Group items by timestamp
    timestamp_groups = {}
    for item in urls:
        timestamp = item.get('date')
        if timestamp:
            if timestamp not in timestamp_groups:
                timestamp_groups[timestamp] = []
            timestamp_groups[timestamp].append(item)

    merged_items = []

    # Process each group of items with the same timestamp
    for timestamp, items in timestamp_groups.items():
        if len(items) == 1:
            merged_items.append(items[0])
            continue

        # Find the cleanest URL among the items
        clean_urls = [item for item in items if is_clean_url(item['url'])]
        if clean_urls:
            base_item = clean_urls[0]  # Use the first clean URL item as base
        else:
            base_item = items[0]  # If no clean URLs, use the first item

        # Merge image information from all items
        all_images = []
        for item in items:
            if 'images' in item:
                for img in item['images']:
                    if img not in all_images:  # Avoid duplicate images
                        all_images.append(img)

        if all_images:
            base_item['images'] = all_images

        merged_items.append(base_item)

    # Add any items without timestamps
    undated_items = [item for item in urls if not item.get('date')]
    merged_items.extend(undated_items)

    return merged_items


def write_markdown_file(filename: str, urls: List[Dict[str, Any]], is_facebook: bool):
    """Write extracted URLs to a markdown file."""
    print(f"\nWriting {'Facebook' if is_facebook else 'external'} links to {filename}")
    print(f"Number of URLs before merging: {len(urls)}")

    # Merge items from the same post before writing
    merged_urls = merge_url_items(urls)
    print(f"Number of URLs after merging: {len(merged_urls)}")

    with open(filename, 'w', encoding='utf-8') as f:
        if is_facebook:
            f.write("# Facebook Links (Newest First)\n\n")
        else:
            f.write("# External Links (Newest First)\n\n")

        # Sort URLs by date (newest first)
        dated_urls = [u for u in merged_urls if u['date']]
        undated_urls = [u for u in merged_urls if not u['date']]

        dated_urls.sort(key=lambda x: x['date'], reverse=True)

        # Write dated URLs
        for i, item in enumerate(dated_urls, 1):
            f.write(f"{i}. Date: {item['date']}\n")
            f.write(f"   - URL: {item['url']}\n")
            if 'Profile' in item:
                f.write(f"   - Profile: {item['Profile']}\n")
            if 'ProfileShared' in item:
                f.write(f"   - ProfileShared: {item['ProfileShared']}\n")
            if item.get('title'):
                f.write(f"   - Title: \"{item['title']}\"\n")
            if item.get('description'):
                f.write(f"   - Description: \"{item['description']}\"\n")

            # Add image information if present
            if 'images' in item and item['images']:
                f.write("   - Images:\n")
                for img in item['images']:
                    f.write(f"     * Facebook URL: {img['facebook_url']}\n")
                    if img.get('description'):
                        f.write(f"       Description: {img['description']}\n")
                    if img.get('width') and img.get('height'):
                        f.write(f"       Dimensions: {img['width']}x{img['height']}\n")
            f.write("\n")

        # Write undated URLs if any
        if undated_urls:
            f.write("\nAdditional URLs (No Date):\n")
            for item in undated_urls:
                f.write(f"- {item['url']}")
                if 'Profile' in item:
                    f.write(f" (Profile: {item['Profile']})")
                if 'ProfileShared' in item:
                    f.write(f" (ProfileShared: {item['ProfileShared']})")
                f.write("\n")


def main():
    parser = argparse.ArgumentParser(description='Extract Facebook and external links from JSON data')
    parser.add_argument('input_file', help='Input JSON file path')
    parser.add_argument('--output-dir', default='.', help='Output directory for markdown files')

    args = parser.parse_args()

    try:
        if not os.path.exists(args.input_file):
            raise FileNotFoundError(f"Input file not found: {args.input_file}")

        os.makedirs(args.output_dir, exist_ok=True)

        with open(args.input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            data = [data]

        facebook_urls = []
        external_urls = []

        for item in data:
            fb_urls, ext_urls = extract_all_urls(item)
            facebook_urls.extend(fb_urls)
            external_urls.extend(ext_urls)

        # Remove duplicates while preserving order
        facebook_urls = list({url['url']: url for url in facebook_urls}.values())
        external_urls = list({url['url']: url for url in external_urls}.values())

        write_markdown_file(
            os.path.join(args.output_dir, 'facebook_links.md'),
            facebook_urls,
            True
        )
        write_markdown_file(
            os.path.join(args.output_dir, 'external_links.md'),
            external_urls,
            False
        )

        print("\nProcessing completed successfully!")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()