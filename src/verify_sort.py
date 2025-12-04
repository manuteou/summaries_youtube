
from downloader import YouTubeAudioProcessor
import sys

try:
    processor = YouTubeAudioProcessor(output_dir="./test_output", source=5)
    query = "news"
    print(f"Searching for '{query}' with sort by date...")
    videos = processor.search_subject(query)
    
    if not videos:
        print("No videos found!")
        sys.exit(1)
    
    print(f"Found {len(videos)} videos:")
    
    last_date = None
    is_sorted = True
    
    for v in videos:
        safe_title = v.title.encode('ascii', 'ignore').decode('ascii')
        print(f"- {safe_title} | Date: {v.publish_date}")
        if last_date and v.publish_date > last_date:
            is_sorted = False
            print(f"  ERROR: Not sorted! {v.publish_date} > {last_date}")
        last_date = v.publish_date

    if is_sorted:
        print("\nSUCCESS: Videos are sorted by date (newest first).")
    else:
        print("\nFAILURE: Videos are NOT sorted by date.")

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
