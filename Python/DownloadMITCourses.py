import requests
import re
import os
import sys
from bs4 import BeautifulSoup

mit_lecture_videos = "https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/resources/lecture-videos/"

res = requests.get(mit_lecture_videos)

soup = BeautifulSoup(res.content, "html.parser")

links = soup.find_all("a", attrs={"aria-label": "Download file"})

for link in links:
	video_link = link.get("href")
	folder_name = video_link.split('/')[-2]
	file_name = video_link.split('/')[-1]
	
	if not os.path.exists(folder_name):
		os.mkdir(folder_name)

	with open(f"{folder_name}/{file_name}", "wb") as fh:
		print(f"\nDownloading: {file_name}")
		video_data = requests.get(video_link, stream=True)
		total_length = video_data.headers.get("content-length")
		if total_length is None:
			fh.write(video_data.content)
		else:
			dl = 0
			total_length = int(total_length)
			for data in video_data.iter_content(chunk_size=4096):
				dl += len(data)
				fh.write(data)
				done = int(50 * dl / total_length)
				sys.stdout.write("\r[%s%s] %dMB/%dMB" % ('=' * done, ' ' * (50-done), (dl/1000)/1000, (total_length/1000)/1000))
				sys.stdout.flush()