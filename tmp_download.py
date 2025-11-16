from pathlib import Path
from api.internetarchive import InternetArchiveClient

client = InternetArchiveClient()
dest = Path("/home/ethan/downloads")  # choose your path
client.download("fantastic-planet__1973", destination=dest, glob_pattern="*.mp4")
print("Downloaded to:", dest)
