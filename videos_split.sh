#!/bin/bash

in_dir=$1
out_dir=$2

mkdir -p "$out_dir"
for video_file in "$in_dir"/*.video.mp4
do
  [ -f "$video_file" ] || continue
  base=${video_file%.video.mp4}
  video_id=${base##*/}
  audio_file=
  for candidate in "${base}".audio.*
  do
    if [ -f "$candidate" ]; then
      audio_file=$candidate
      break
    fi
  done

  if [ -z "$audio_file" ]; then
    echo "No audio track found for ${video_id}, skipping"
    continue
  fi

  ffmpeg -i "$video_file" -i "$audio_file" \
    -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac \
    -segment_time 00:01:00 -f segment "$out_dir/${video_id}_%04d.mp4"
done