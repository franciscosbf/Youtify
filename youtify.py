"""
Youtify is a script to download Spotify tracks through Youtube.
Copyright (C) 2021  Francisco Braço-Forte

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

#!/urs/bin/env python

__author__  = 'Francisco Braço-Forte'
__version__ = '0.0.1'

from typing import (
    Any,
    Callable, 
    Generator, 
    Union
)
import sys
import json
import base64
import re
import argparse
import logging
import os

import urllib3
import yaml
import youtube_dl

__log__ = logging.getLogger(__name__)

config = 'spotify.yml'

cookies = 'cookies.txt'

log = 'youtify.log'

"""
If a file containing Spotify urls is passed 
in arguments, the name goes here. 
"""
spotify_urls = None

"""Destination folder where the track(s) is(are) stored."""
dest = f'{os.getcwd()}/'

"""Validate spotify url syntax."""
spotify_re = re.compile(r"""
    ^(?:https:\/\/open\.spotify\.com)
     (?:\/)
     (?P<type>track|playlist|album)
     (?:\/)
     (?P<id>[a-zA-Z0-9]+)
     (?:.*)$""",
    re.VERBOSE
)

spotify_auth_url = 'https://accounts.spotify.com/api/token'

base_api_url = 'https://api.spotify.com/v1/'
spotify_tracks_url = base_api_url+'tracks/{id}'
spotify_albums_url = base_api_url+'albums/{id}/tracks?limit=50' # Unfortunately doesn't support fields.
playlist_fields = 'items(track(artists.name,external_urls.spotify,name)),next'
spotify_playlists_url = base_api_url+'playlists/{id}/tracks?fields='+playlist_fields

"""
Sub-functions.
"""

def _die(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)

def _decode_url(url: str) -> Union[tuple[str, str], None]:
    url_content = spotify_re.match(url)
    if url_content is None:
        __log__.error(
            f'Invalid url syntax: {url}'
        )

        return None

    type, id = url_content.groups()

    __log__.debug(
        f'Url {url} decoded: type - {type}; id - {id}.'
    )

    return type, id

def _build_youtube_query(track_info: dict[str, Any]) -> str:
    name = track_info['name']
    artists = ', '.join(
        artist['name'] 
        for artist in track_info['artists']
    )

    query = f'ytsearch: {name} {artists}'

    __log__.debug(
        f'Query "{query}" has been built. Track url: '
        f'{track_info["external_urls"]["spotify"]}.'
    )

    return query

def _request_resource(
        http: urllib3.PoolManager, 
        token: str,
        url: str) -> Union[dict[str, Any], None]:
    r = http.request(
        method='GET',
        url=url,
        headers={
            'Accept'        : 'application/json',
            'Content-Type'  : 'application/json',
            'Authorization' : f'Bearer {token}'
        }
    )

    data = r.data.decode('utf-8')
    content = json.loads(data)
    if r.status == 200:
        return content
    else:
        __log__.error(
            'While trying to get information about '
           f'track(s) from {url}: Status Code {r.status}; '
           f'Error Message {content["error"]["message"]}.'
        )

        return None

def _multiple_tracks(
        http: urllib3.PoolManager, 
        token: str, 
        url: str,
        get_track: Callable) -> Generator[str, None, None]:
    # While with a playlist each track information is
    # into a dict accessed by the key 'track', in an album 
    # its information is directly obtained - get_track.
    # See request_album and request_playlist func's.
    while url is not None:
        content = _request_resource(
            http=http,
            token=token,
            url=url
        )
        if content is None:
            break

        for item in content['items']:
            track = get_track(item)
            query = _build_youtube_query(track)
            yield query

        # Queries from previous url are 
        # preserved. Although, the offset is 
        # changed adding the limit to it.
        url = content['next']

"""
Main functions.
"""

def parse_args() -> None:
    parser = argparse.ArgumentParser(
        description='Downloads Spotify tracks through Youtube.',
        epilog=f'Author: {__author__}',
        add_help=False
    )

    parser.add_argument(
        '-h', '--help',
        action='help',
        default=argparse.SUPPRESS,
        help='Show this help message and exit.'
    )

    parser.add_argument(
        '-c', '--cookies', 
        dest='cookies', 
        metavar='FILE',
        help='Youtube cookies file for account authentication.'
    )

    parser.add_argument(
        '-u', '--urls', 
        dest='urls', 
        metavar='FILE',
        help='File containing Spotify urls (Blank lines are skipped).'
    )

    parser.add_argument(
        '-f', '--folder', 
        dest='folder', 
        metavar='DIR',
        help='Directory where tracks\'ll be stored.'
    )

    parser.add_argument(
        '-d', '--debugging',
        nargs='?',
        const=1,
        choices=(1, 2), # 1- logging.INFO; 2 - logging.DEBUG.
        type=int,
        dest='debugging', 
        metavar='LEVEL/NONE', 
        help='Outputs further information to stdout and to a log file. ' 
             'If the file doesn\'t exist, a new one is created. '
             'With level 1 (default or explicit) shows some info '
             'about execution and errors; level 2 is used for '
             'more technical elements.'
    )

    parser.add_argument(
        '-v', '--version', 
        action='version', 
        version=f'%(prog)s {__version__}',
        help='Show program\'s version and exit.'
    )

    args = vars(parser.parse_args())   

    cookies_filename = args.get('cookies') 
    if cookies_filename is not None:
        if not os.path.isfile(cookies_filename):
            _die(
                f'> {cookies_filename} isn\'t a file.'
            )
        global cookies
        cookies = cookies_filename
    
    urls_filename = args.get('urls')
    if urls_filename is not None:
        if not os.path.isfile(urls_filename):
            _die(
                f'> {urls_filename} isn\'t a file.'
            )
        global spotify_urls
        spotify_urls = urls_filename

    dest_folder = args.get('folder')
    if dest_folder is not None:
        if os.path.isfile(dest_folder):
            _die(
                f'> Destination can\'t be a file: {dest_folder}.'
            ) 
       
        global dest
        if os.path.islink(dest_folder):
            dest = os.path.realpath(dest_folder)
        if not os.path.isdir(dest_folder):
            os.mkdir(dest_folder)
            dest = os.path.abspath(dest_folder)
        else:
            dest = os.path.abspath(dest_folder)
        dest = f'{dest}/'

    debug_level = args.get('debugging')
    if debug_level is not None:
        chout = logging.StreamHandler(
            stream=sys.stdout
        )
        chfile = logging.FileHandler(
            filename=log,
            mode='a',
            encoding='utf-8'
        )

        formatter = logging.Formatter(
            fmt='%(asctime)s [%(levelname)s] (func %(funcName)s) %(message)s',
            datefmt='%I:%M:%S %p %m/%d/%Y'
        )
        chout.setFormatter(fmt=formatter)
        chfile.setFormatter(fmt=formatter)
        
        level = logging.INFO if debug_level == 1 else logging.DEBUG
        __log__.setLevel(level=level)
        __log__.addHandler(hdlr=chout)
        __log__.addHandler(hdlr=chfile)

def file_urls() -> Generator[str, None, None]:
    try:
        with open(spotify_urls, mode='r', encoding='utf-8') as f:
            while (line := f.readline()) != '':
                if line != '\n':
                    if line.endswith('\n'):
                        yield line[:-1]
                    else:
                        yield line
    except Exception as e:
        _die(f'An error occured with {spotify_urls}: {e}.')

def input_urls() -> list[str]:
    # Write line by line is the right approach (my 
    # opinion) to avoid long trains or have to put each 
    # url inside quotation marks when writing the 
    # command. Also an url may have some queries 
    # separated by &. POSIX-compliant shells recognizes 
    # & as running multiple commands in the background 
    # in a subshell. Shell on Windows OS's does almost the same.
    urls = []

    print('> Write bellow line by line the Spotify url(s):')
    while (url := input()) != '':
        urls.append(url)

    return urls

def request_token(http: urllib3.PoolManager) -> str:
    try:
        with open(config, mode='r', encoding='utf-8') as f:
            # Unlike load, safe_load restricts deserialization 
            # to only simple Python objects e.g: dict, list...
            # This way, it ensures a safely parsing of the file.
            settings = yaml.safe_load(f)
    except Exception as e:
        _die(f'> Something happened in settings: {e}.')
    
    spotify_id = settings.get('id')
    spotify_secret = settings.get('secret')
    
    if spotify_id is None or spotify_secret is None:
        _die('> You missed something in config file.')

    # Encoding the schema bellow with Base64 
    # is mandatory by Spotify Web API.
    auth_raw = f'{spotify_id}:{spotify_secret}'
    auth_utf8_encoded = auth_raw.encode(encoding='utf-8')
    auth_64encoded = base64.b64encode(auth_utf8_encoded)
    auth_raw_64encoded = auth_64encoded.decode(encoding='utf-8')
    
    __log__.debug(
        f'Spotify auth schema {auth_raw} encoded '
        f'with Base64: {auth_raw_64encoded}.'
    )

    r = http.request_encode_body(
        method='POST',
        url=spotify_auth_url,
        headers={
            'Authorization' : f'Basic {auth_raw_64encoded}'
        },
        fields={
            'grant_type' : 'client_credentials'
        },
        # Encodes the body with 'application/x-www-form-urlencoded' type.
        encode_multipart=False 
    )

    data = r.data.decode('utf-8')
    content = json.loads(data)
    if r.status != 200:
        _die(
            '> Something went wrong while '
            'trying to get access token: '
           f'{content["error_description"]}'
        )

    token = content['access_token']

    __log__.debug(
        f'Access token: {token}.'
    )

    return token

def request_track(
        http: urllib3.PoolManager, 
        token: str, 
        id: str) -> Union[list[str], None]:
    url = spotify_tracks_url.format(id=id)
    content = _request_resource(
        http=http,
        token=token,
        url=url
    )

    if content is not None:
        query = _build_youtube_query(content)
        return [query]
    else:
        return []
    
def request_album(
        http: urllib3.PoolManager, 
        token: str, 
        id: str) -> Generator[str, None, None]:
    url = spotify_albums_url.format(id=id)
    return _multiple_tracks(
        http=http,
        token=token,
        url=url,
        get_track=lambda item: item
    )

def request_playlist(
        http: urllib3.PoolManager, 
        token: str, 
        id: str) -> Generator[str, None, None]:
    url = spotify_playlists_url.format(id=id)
    return _multiple_tracks(
        http=http,
        token=token,
        url=url,
        get_track=lambda item: item['track']
    )

def download_through_youtube(queries: set[str]) -> None:
    params = {
        'format' : 'bestaudio/best',
        'outtmpl' : f'{dest}%(title)s.%(ext)s',
        'cookiefile' : cookies,
        'noplaylist' : True,
        'postprocessors' : [{
            'key' : 'FFmpegExtractAudio',
            'preferredcodec' : 'mp3',
            'preferredquality' : '192',
        }]
    }

    with youtube_dl.YoutubeDL(params=params) as ydl:
        ydl.download(queries)

def main() -> None:
    parse_args()
    
    http = urllib3.PoolManager(num_pools=2)

    token = request_token(http=http)

    if spotify_urls is None:
        urls = input_urls()
    else:
        urls = file_urls()

    # Ensure that there isn't any 
    # duplicated url or query.
    visited_urls = set()
    queries = set()

    callers = {
        'track' : request_track,
        'album' : request_album,
        'playlist' : request_playlist
    }
    
    for url in urls:
        if url in visited_urls:
            __log__.info(
                f'Url already used: {url}. Skipping to the next...'
            )

            continue
        else:
            visited_urls.add(url)

            __log__.info(
                f'Using url {url}...'
            )

        url_groups = _decode_url(url=url)
        if url_groups is None:
            continue
        type, id = url_groups
        
        new_queries = callers.get(type)(
            http=http, 
            token=token, 
            id=id
        )

        for query in new_queries:
            if query not in queries:
                queries.add(query)

                __log__.info(
                    f'Query "{query}" was added.'
                )
            else:
                __log__.info(
                    f'Query already exist: {query}.'
                )

    if not queries:
        _die('> No tracks were collected from Spotify.')

    __log__.info(
        f'Found {len(queries)} track(s).'
    )

    download_through_youtube(queries=queries)

if __name__ == '__main__':
    main()