from googlesearch import search
import time
import requests

def get_websites(keyword):
    websites = []

    print("Searching Google...")

    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Add delay between requests to avoid rate limiting
            time.sleep(2)  # Initial delay before search
            
            for url in search(keyword, num_results=10):
                websites.append(url)
                print(f"Found: {url}")
                time.sleep(1)  # Delay between each result
            
            break  # Success, exit retry loop
            
        except requests.exceptions.HTTPError as e:
            if '429' in str(e):
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 5 * retry_count  # Exponential backoff
                    print(f"Rate limited. Waiting {wait_time} seconds before retry {retry_count}/{max_retries}...")
                    time.sleep(wait_time)
                else:
                    print("Failed after maximum retries. Try again later or reduce search frequency.")
                    return []
            else:
                print(f"Search error: {e}")
                return []
        except Exception as e:
            print(f"Unexpected error during search: {e}")
            return []
    
    print(f"Total websites found: {len(websites)}")
    return websites
