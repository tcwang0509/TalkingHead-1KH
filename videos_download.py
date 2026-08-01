import argparse
import glob
import multiprocessing as mp
import os
from functools import partial
from time import time as timer

from pytubefix import YouTube
from tqdm import tqdm

parser = argparse.ArgumentParser()
parser.add_argument('--input_list', type=str, required=True,
                    help='List of youtube video ids')
parser.add_argument('--output_dir', type=str, default='data/youtube_videos',
                    help='Location to download videos')
parser.add_argument('--num_workers', type=int, default=8,
                    help='How many multiprocessing workers?')
args = parser.parse_args()


def download_video(output_dir, video_id):
    r"""Download highest-quality video and audio tracks as paired files."""
    video_path = os.path.join(output_dir, '%s.video.mp4' % video_id)
    audio_paths = glob.glob(os.path.join(output_dir, '%s.audio.*' % video_id))
    if not (os.path.isfile(video_path) and audio_paths):
        try:
            yt = YouTube('https://www.youtube.com/watch?v=%s' % (video_id))
            video_stream = yt.streams.filter(
                subtype='mp4', only_video=True, adaptive=True
            ).order_by('resolution').desc().first()
            audio_stream = yt.streams.filter(
                only_audio=True
            ).order_by('abr').desc().first()

            if video_stream is None or audio_stream is None:
                raise RuntimeError('No adaptive video or audio stream found')

            # Preserve separate tracks; videos_split.sh muxes them into clips.
            video_stream.download(output_path=output_dir,
                                  filename=os.path.basename(video_path))
            audio_extension = audio_stream.subtype or 'audio'
            audio_only_path = os.path.join(
                output_dir, '%s.audio.%s' % (video_id, audio_extension)
            )
            audio_stream.download(output_path=output_dir,
                                  filename=os.path.basename(audio_only_path))
        except Exception as e:
            print(e)
            print('Failed to download %s' % (video_id))
    else:
        print('File exists: %s' % (video_id))


if __name__ == '__main__':
    # Read list of videos.
    video_ids = []
    with open(args.input_list) as fin:
        for line in fin:
            video_ids.append(line.strip())

    # Create output folder.
    os.makedirs(args.output_dir, exist_ok=True)

    # Download videos.
    downloader = partial(download_video, args.output_dir)

    start = timer()
    pool_size = args.num_workers
    print('Using pool size of %d' % (pool_size))
    with mp.Pool(processes=pool_size) as p:
        _ = list(tqdm(p.imap_unordered(downloader, video_ids), total=len(video_ids)))
    print('Elapsed time: %.2f' % (timer() - start))
