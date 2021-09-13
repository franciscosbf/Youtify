## Youtipy

Python script which downloads Spotify tracks, playlists or albums through embedded _youtube-dl_, converting them to MP3 format. 

## Interpreter Version

Use Python >= 3.9.

## Requirements

Youtipy requires the following modules:

- [urrlib3](https://urllib3.readthedocs.io/en/stable/): HTTP client used to interact with [Spotify Web API](https://developer.spotify.com/documentation/web-api/).
- [pyyaml](https://pyyaml.org/wiki/PyYAMLDocumentation): yaml parser necessary for configs file.
- [youtube-dl](https://github.com/ytdl-org/youtube-dl): video downloader and format converter. 

You can install on Windows or in some Linux Distribution this way:

    python -m pip install --upgrade urrlib3 pyyaml youtube-dl

or

    pip install --upgrade urrlib3 pyyaml youtube-dl

## Installation

Simply do this:

    git clone https://github.com/franciscosbf/Youtify

## Arguments

> -h, --help            
                        Show this help message and exit.

> -c, --cookies FILE
                        Youtube cookies file for account authentication.
  
> -u, --urls FILE  File containing Spotify urls (blank lines are skipped).
  
> -f, --folder DIR  Directory where tracks'll be stored.
  
> -d, --debugging [LEVEL/NONE]
                        Outputs further information to stdout and to a log file. If the file doesn't exist, a new one is created. With level 1 (implicit or explicit) shows some info about execution and errors; level 2 is used for more technical elements.
  
> -v, --version         
                        Show program's version and exit.

## Notes

###### Setup Process

First things first, you need to go to [Spotify for Developers](https://developer.spotify.com/), click on DashBoard, log in and create an App (since we just need to collect tracks information, a non-Premium account works). Then choose a name and description (whatever you want) and agreed with the terms. Once created, just pick up the client ID and the Secret Key to write in youtify.yaml settings file.

###### Cookies

Some Youtube videos require user authentication (e.g. age verification). _youtube-dl_ has an option to pass user email and password. However, this process may not be enough since `Unable to log in: HTTP Error 400` can happen. 
In order to avoid this, _youtube-dl_ recommends the creation of a cookies file from Youtube while you are logged in. You do this using one of this extensions:
- Google - [Get cookies.txt](https://chrome.google.com/webstore/detail/get-cookiestxt/bgaddhkoddajcdgocldbbfleckgcbcid/)
-  Firefox - [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)

Just place this file in the same folder of the script named by `cookies.txt` or indicate the location via command line: `-c/--cookies <path>`.   

###### Aside

If you gonna digit the links via command line and don't have more links, just put an empty line (click Enter).

## Version log

#### 0.0.1 - 13/9/2021 
- First release.