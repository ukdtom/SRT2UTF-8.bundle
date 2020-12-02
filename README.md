SRT2UTF-8.bundle
================
[![GitHub issues](https://img.shields.io/github/issues/ukdtom/SRT2UTF-8.bundle.svg?style=flat)](https://github.com/ukdtom/SRT2UTF-8.bundle/issues)
[![master](https://img.shields.io/badge/master-stable-green.svg?maxAge=2592000)]()
![Maintenance](https://img.shields.io/badge/Maintained-Yes-green.svg)

***

A Plex Agent that will convert sidecar subtitle files into UTF-8, if not already; and rename subtitle file names by appending a language code to the end. 

The language code that is appended can be configured in the settings of the Plex Agent. Additionally, both the encoding to UTF-8 and the subtitle file renaming can be optionally turned off in the settings.

Please read the Wiki for futher information:

https://github.com/ukdtom/SRT2UTF-8.bundle/wiki

## Note

The renaming of subtitle files is disabled by default. This can be enabled in the Agent's settings for your Plex Server.

Please select your preferred language before enabling the renaming of subtitle files. If the renaming is enabled and the language is not selected, the subtitle file names will remain unchanged.

Subtitle file renaming is also impacted by the "Remove the original subtitle file" option which is enabled by default. If disabled, the agent will copy the subtitle file instead of moving (renaming) it, leaving the original file in place.

WARNING!!!!!

It is important that you read the Wiki, since this agent will do what no other agent does in the Plex Universe, and that's changing your media files.

Use at own risk.

## License

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
