dataset=$1

# Download the videos.
python videos_download.py --input_list data_list/${dataset}_video_ids.txt --output_dir ${dataset}/raw_videos

# Split the videos into 1-min chunks.
./videos_split.sh ${dataset}/raw_videos ${dataset}/1min_clips

# Extract the talking head clips.
python videos_crop.py --input_dir ${dataset}/1min_clips/ --output_dir ${dataset}/cropped_clips --clip_info_file data_list/${dataset}_video_tubes.txt