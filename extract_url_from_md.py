# extract a list of urls from external_links.md
# inputs external_links.md (filename can be changed in code)
# outputs url.txt

import re
from pathlib import Path
from urllib.parse import urlparse


def is_valid_url(url):
    """
    Check if URL is valid for scraping:
    - Not a top-level domain
    - Not starting with 'scontent'
    - Has a path component

    Args:
        url (str): URL to validate

    Returns:
        bool: True if URL is valid for scraping
    """
    parsed = urlparse(url)

    # Check if URL starts with 'scontent'
    if parsed.netloc.startswith('scontent'):
        return False

    # Check if path exists and is more than just '/'
    if not parsed.path or parsed.path == '/':
        return False

    # Split path and check if it has meaningful segments
    path_segments = [seg for seg in parsed.path.split('/') if seg]
    if not path_segments:
        return False

    return True


def extract_urls(file_path):
    """
    Extract valid URLs from a formatted text file.

    Args:
        file_path (str): Path to the input file

    Returns:
        list: List of extracted URLs that meet the criteria
    """
    urls = []
    url_pattern = re.compile(r'^\s*- URL:\s*(https?://\S+)\s*$', re.MULTILINE)

    # Read the file content
    content = Path(file_path).read_text(encoding='utf-8')

    # Find all URLs using regex
    matches = url_pattern.finditer(content)
    for match in matches:
        url = match.group(1)
        if is_valid_url(url):
            urls.append(url)

    return urls


def main():
    # Example usage
    file_path = 'external_links.md'  # Replace with your file path
    try:
        extracted_urls = extract_urls(file_path)

        # Print extracted URLs
        print("Extracted URLs:")
        for i, url in enumerate(extracted_urls, 1):
            print(f"{i}. {url}")

        # Save to output file
        with open('urls.txt', 'w', encoding='utf-8') as f:
            for url in extracted_urls:
                f.write(f"\"{url}\"\n")

        print(f"\nFound {len(extracted_urls)} valid URLs")

    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found")
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()