from pytubefix import YouTube

url = "https://www.youtube.com/watch?v=jNQXAC9IVRw" # Me at the zoo
yt = YouTube(url)

print(f"Title: {yt.title}")
print(f"Publish Date: {yt.publish_date}")
try:
    print(f"Metadata: {yt.metadata}")
except Exception as e:
    print(f"Metadata error: {e}")
