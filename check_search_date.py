from pytubefix import YouTube
from pytubefix.contrib.search import Search

s = Search("python programming")
if s.results:
    video = s.results[0]
    print(f"Title: {video.title}")
    print(f"Publish Date: {video.publish_date}")
else:
    print("No results found")
