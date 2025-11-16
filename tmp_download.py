from pathlib import Path
from api.catalog.internetarchive import InternetArchiveClient, MovieDownloadOptions

client = InternetArchiveClient()
dest = Path("/home/ethan/downloads")  # choose your path
bundle = client.download_movie(
    "fantastic-planet__1973",
    destination=dest,
    options=MovieDownloadOptions(include_subtitles=False),
)
print("Downloaded to:", bundle.video_path)
