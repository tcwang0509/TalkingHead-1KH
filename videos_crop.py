# Copyright (c) 2022, NVIDIA CORPORATION. All rights reserved.
#
# This script is licensed under the MIT License.

import argparse
import multiprocessing as mp
import os
from fractions import Fraction
from functools import partial
from time import time as timer

import ffmpeg
from tqdm import tqdm


parser = argparse.ArgumentParser()
parser.add_argument('--input_dir', type=str, required=True,
                    help='Dir containing youtube clips.')
parser.add_argument('--clip_info_file', type=str, required=True,
                    help='File containing clip information.')
parser.add_argument('--output_dir', type=str, required=True,
                    help='Location to dump outputs.')
parser.add_argument('--num_workers', type=int, default=8,
                    help='How many multiprocessing workers?')
args = parser.parse_args()


def get_media_info(filepath):
    probe = ffmpeg.probe(filepath)
    video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
    height = int(video_stream['height'])
    width = int(video_stream['width'])
    frame_rate = video_stream.get('avg_frame_rate', video_stream.get('r_frame_rate'))
    fps = float(Fraction(frame_rate))
    has_audio = any(stream['codec_type'] == 'audio' for stream in probe['streams'])
    return height, width, fps, has_audio


def trim_and_crop(input_dir, output_dir, clip_params):
    video_name, H, W, S, E, L, T, R, B = clip_params.strip().split(',')
    H, W, S, E, L, T, R, B = int(H), int(W), int(S), int(E), int(L), int(T), int(R), int(B)
    output_filename = '{}_S{}_E{}_L{}_T{}_R{}_B{}.mp4'.format(video_name, S, E, L, T, R, B)
    output_filepath = os.path.join(output_dir, output_filename)
    if os.path.exists(output_filepath):
        print('Output file %s exists, skipping' % (output_filepath))
        return

    input_filepath = os.path.join(input_dir, video_name + '.mp4')
    if not os.path.exists(input_filepath):
        print('Input file %s does not exist, skipping' % (input_filepath))
        return

    h, w, fps, has_audio = get_media_info(input_filepath)
    t = int(T / H * h)
    b = int(B / H * h)
    l = int(L / W * w)
    r = int(R / W * w)
    input_stream = ffmpeg.input(input_filepath)
    video_stream = ffmpeg.trim(input_stream.video, start_frame=S, end_frame=E+1)
    video_stream = ffmpeg.setpts(video_stream, 'PTS-STARTPTS')
    video_stream = ffmpeg.crop(video_stream, l, t, r-l, b-t)

    if has_audio:
        audio_stream = ffmpeg.filter(
            input_stream.audio, 'atrim', start=S / fps, end=(E + 1) / fps
        )
        audio_stream = ffmpeg.filter(audio_stream, 'asetpts', 'PTS-STARTPTS')
        stream = ffmpeg.output(
            video_stream, audio_stream, output_filepath, acodec='aac', shortest=None
        )
    else:
        stream = ffmpeg.output(video_stream, output_filepath)
    ffmpeg.run(stream)


if __name__ == '__main__':
    # Read list of videos.
    clip_info = []
    with open(args.clip_info_file) as fin:
        for line in fin:
            clip_info.append(line.strip())

    # Create output folder.
    os.makedirs(args.output_dir, exist_ok=True)

    # Download videos.
    downloader = partial(trim_and_crop, args.input_dir, args.output_dir)

    start = timer()
    pool_size = args.num_workers
    print('Using pool size of %d' % (pool_size))
    with mp.Pool(processes=pool_size) as p:
        _ = list(tqdm(p.imap_unordered(downloader, clip_info), total=len(clip_info)))
    print('Elapsed time: %.2f' % (timer() - start))
