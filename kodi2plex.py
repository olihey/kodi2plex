"""
Kodi2Plex

Simple server to access a Kodi instance from Plex clients
"""

import os
import sys
import json
import time
import struct
import socket
import pprint
import random
import logging
import asyncio
import argparse
import threading
import traceback
import collections
import http.server
import socketserver
import urllib.request
import xml.dom.minidom
import xml.etree.ElementTree

import aiohttp
import aiohttp.web


video_codec_map = {"avc1": "h264", "hev1": "hevc", "hevc": "hevc"}


def _xml_prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = xml.etree.ElementTree.tostring(elem)
    reparsed = xml.dom.minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


async def kodi_request(app, method, params):
    """
    Sends a JSON formatted message to the server
    returns the result as dictionary (from json response)
    """

    # create the request
    payload = {
        "method": method,
        "params": params,
        "jsonrpc": "2.0",
        "id": app["kodi_jsonrpc_counter"],
    }

    # increase the message counter
    app["kodi_jsonrpc_counter"] += 1

    if app["debug"]:
        logger.debug("Sending to %s\nDATA:\n%s", app["kodi_url"], pprint.pformat(payload))

    # fire up the request
    kodi_response = await app["client_session"].post(app["kodi_url"],
                                                     data=json.dumps(payload).encode("utf8"),
                                                     headers={'content-type': 'application/json'})
    kodi_json = await kodi_response.json()
    if app["debug"]:
        logger.debug("Result:\n%s", pprint.pformat(kodi_json))
    return kodi_json


async def init_kodi(app):
    pass
    # json_data = await app["client_session"].get(app["kodi_url"])
    # json_data = await json_data.json()
    # # json_data["methods"] = []
    # # json_data["notifications"] = []
    # # json_data["types"] = []
    # pprint.pprint(json_data["methods"]["VideoLibrary.GetEpisodes"])
    # pprint.pprint(json_data["types"]["List.Sort"])


def gdm_broadcast(gdm_socket, kodi2plex_app):
    """
    Function to send response for GDM requests from
    Plex clients
    """

    while gdm_socket.fileno() != -1:
        logger.debug('GDM: waiting to recieve')
        data, address = gdm_socket.recvfrom(1024)
        logger.debug('received %s bytes from %s', len(data), address)

        # discard message if header is not in right format
        if data == b'M-SEARCH * HTTP/1.1\r\n\r\n':
            mxpos = data.find(b'MX:')
            maxdelay = int(data[mxpos+4]) % 5   # Max value of this field is 5
            time.sleep(random.randrange(0, maxdelay+1, 1))  # wait for random 0-MX time until sending out responses using unicast.
            logger.info('Sending M Search response to - %s', address)

            # response as string
            response_message = """HTTP/1.1 200 OK\r
Content-Type: plex/media-server\r
Name: %s\r
Port: 32400\r
Resource-Identifier: 23f2d6867befb9c26f7b5f366d4dd84e9b2294c9\r
Updated-At: 1466340239\r
Version: 0.9.16.6.1993-5089475\r
\r\n""" % kodi2plex_app["server_ip"]

            logger.debug("GDM send: %s", response_message)

            gdm_socket.sendto(response_message.encode("utf8"), address)
        else:
            logger.warn('recieved wrong MSearch')

        time.sleep(5)


def IndexMiddleware(index='index.html'):
    """Middleware to serve index files (e.g. index.html) when static directories are requested.
    Usage:
    ::
        from aiohttp import web
        from aiohttp_index import IndexMiddleware
        app = web.Application(middlewares=[IndexMiddleware()])
        app.router.add_static('/', 'static')
    ``app`` will now serve ``static/index.html`` when ``/`` is requested.
    :param str index: The name of a directory's index file.
    :returns: The middleware factory.
    :rtype: function
    """
    async def middleware_factory(app, handler):
        """Middleware factory method.
        :type app: aiohttp.web.Application
        :type handler: function
        :returns: The retry handler.
        :rtype: function
        """
        async def index_handler(request):
            """Handler to serve index files (index.html) for static directories.
            :type request: aiohttp.web.Request
            :returns: The result of the next handler in the chain.
            :rtype: aiohttp.web.Response
            """
            try:
                filename = request.match_info['filename']
                if not filename:
                    filename = index
                if filename.endswith('/'):
                    filename += index
                request.match_info['filename'] = filename
            except KeyError:
                pass
            return await handler(request)
        return index_handler
    return middleware_factory


async def extract_kodi_info(app, video_node, kodi_info, stream_id):
    part_node = None
    try:
        video_codec = kodi_info["streamdetails"]["video"][0]["codec"]
        media_node = xml.etree.ElementTree.Element("Media",
                                                   attrib={"duration": str(kodi_info["runtime"] * 1000),
                                                           "width": str(kodi_info["streamdetails"]["video"][0]["width"]),
                                                           "height": str(kodi_info["streamdetails"]["video"][0]["height"]),
                                                           "aspectRatio": str(kodi_info["streamdetails"]["video"][0]["aspect"]),
                                                           "audioChannels": str(kodi_info["streamdetails"]["audio"][0]["channels"]),
                                                           "container": "mp4",
                                                           "optimizedForStreaming": "1",
                                                           "audioCodec": kodi_info["streamdetails"]["audio"][0]["codec"],
                                                           "videoCodec": video_codec_map.get(video_codec, video_codec)})
        video_node.append(media_node)

        download_info = await kodi_request(app, "Files.PrepareDownload", [kodi_info["file"]])
        download_url = app["kodi"] + download_info['result']['details']['path']

        part_node = xml.etree.ElementTree.Element("Part",
                                                  attrib={"accessible": "1",
                                                          "id": stream_id,
                                                          "container": "mp4",
                                                          "optimizedForStreaming": "1",
                                                          "key": download_url})
        media_node.append(part_node)
    except:
        logger.error("Error while getting stream details for error: %s", traceback.format_exc())

    if part_node:
        stream_counter = 0
        for video in kodi_info["streamdetails"]["video"]:
            stream_node = xml.etree.ElementTree.Element("Stream", attrib={"streamType": "1",
                                                                          "default": "1",
                                                                          "id": str(stream_counter + 1),
                                                                          "codec": video_codec_map[video["codec"]],
                                                                          "codecID": video_codec_map[video["codec"]],
                                                                          "duration": str(video["duration"] * 1000),
                                                                          "width": str(video["width"]),
                                                                          "height": str(video["height"]),
                                                                          "streamIdentifier": str(stream_counter + 1),
                                                                          "index": str(stream_counter)})
            part_node.append(stream_node)
            stream_counter += 1

        for audio in kodi_info["streamdetails"]["audio"]:
            stream_node = xml.etree.ElementTree.Element("Stream", attrib={"streamType": "2",
                                                                          "default": "1",
                                                                          "id": str(stream_counter + 1),
                                                                          "codec": audio["codec"],
                                                                          "languageCode": audio["language"],
                                                                          "channels": str(audio["channels"]),
                                                                          "streamIdentifier": str(stream_counter + 1),
                                                                          "index": str(stream_counter)})
            part_node.append(stream_node)
            stream_counter += 1

    for director in kodi_info["director"]:
        director_node = xml.etree.ElementTree.Element("Director", attrib={"tag": director})
        video_node.append(director_node)
    if "genre" in kodi_info:
        for genre in kodi_info["genre"]:
            genre_node = xml.etree.ElementTree.Element("Genre", attrib={"tag": genre})
            video_node.append(genre_node)
    for writer in kodi_info["writer"]:
        writer_node = xml.etree.ElementTree.Element("Writer", attrib={"tag": writer})
        video_node.append(writer_node)
    if "genre" in kodi_info:
        for country in kodi_info["country"]:
            country_node = xml.etree.ElementTree.Element("Country", attrib={"tag": country})
            video_node.append(country_node)
    for cast in kodi_info["cast"]:
        cast_node = xml.etree.ElementTree.Element("Role", attrib={"tag": cast["name"],
                                                                  "role": cast["role"]})
        video_node.append(cast_node)


async def get_movie_node(app, movie_id):
    movie_info = await kodi_request(app,
                                    "VideoLibrary.GetMovieDetails",
                                    {"movieid": movie_id,
                                     "properties": ["title",
                                                    "genre",
                                                    "year",
                                                    "rating",
                                                    "director",
                                                    "trailer",
                                                    "tagline",
                                                    "plot",
                                                    "plotoutline",
                                                    "originaltitle",
                                                    "lastplayed",
                                                    "playcount",
                                                    "writer",
                                                    "studio",
                                                    "mpaa",
                                                    "cast",
                                                    "country",
                                                    "imdbnumber",
                                                    "runtime",
                                                    "set",
                                                    "showlink",
                                                    "streamdetails",
                                                    "top250",
                                                    "votes",
                                                    "fanart",
                                                    "thumbnail",
                                                    "file",
                                                    "sorttitle",
                                                    "resume",
                                                    "setid",
                                                    "dateadded",
                                                    "tag",
                                                    "art"]})

    movie_info = movie_info["result"]["moviedetails"]
    video_node = xml.etree.ElementTree.Element("Video",
                                               attrib={"type": "movie",
                                                       "key": "/library/metadata/movie/%d" % movie_id,
                                                       "title": movie_info['label'],
                                                       "studio": "" if not movie_info['studio'] else movie_info['studio'][0],
                                                       "tagline": movie_info['tagline'],
                                                       "summary": movie_info['plot'],
                                                       "year": str(movie_info['year']),
                                                       "rating": str(movie_info["rating"]),
                                                       "art": movie_info["fanart"],
                                                       "viewCount": str(movie_info['playcount']),
                                                       "viewOffset": str(int(movie_info["resume"]["position"]*1000)),
                                                       "duration": str(movie_info["runtime"] * 1000),
                                                       "thumb": movie_info['thumbnail']})

    await extract_kodi_info(app, video_node, movie_info, str(movie_id))

    return video_node


async def get_episode_node(app, episode_id):
    episode_info = await kodi_request(app,
                                      "VideoLibrary.GetEpisodeDetails",
                                      [episode_id,
                                       ["title",  "plot",  "votes",  "rating",  "writer",  "firstaired",  "playcount",
                                        "runtime", "director", "productioncode", "season", "episode", "originaltitle",
                                        "showtitle", "cast", "streamdetails", "lastplayed", "fanart", "thumbnail", "file",
                                        "resume", "tvshowid", "dateadded", "uniqueid", "art"]])
    episode_info = episode_info["result"]["episodedetails"]

    video_node = xml.etree.ElementTree.Element("Video",
                                               attrib={"type": "episode",
                                                       "key": "/library/metadata/episode/%d" % episode_id,
                                                       "title": episode_info['label'],
                                                       "summary": episode_info['plot'],
                                                       "rating": str(episode_info["rating"]),
                                                       "art": episode_info["fanart"],
                                                       "duration": str(episode_info["runtime"] * 1000),
                                                       "viewCount": str(episode_info['playcount']),
                                                       "viewOffset": str(int(episode_info["resume"]["position"]*1000)),
                                                       "thumb": episode_info['thumbnail']})

    await extract_kodi_info(app, video_node, episode_info, "episode%d" % episode_id)

    return video_node

async def get_root(request):
    root = xml.etree.ElementTree.Element("MediaContainer", attrib={})
    root.attrib["allowMediaDeletion"] = "1"
    root.attrib["friendlyName"] = "Kodi2Plex"
    root.attrib["machineIdentifier"] = "23f2d6867befb9c26f7b5f366d4dd84e9b2294c9"
    root.attrib["myPlex"] = "0"
    root.attrib["myPlexMappingState"] = "unknown"
    root.attrib["myPlexSigninState"] = "none"
    root.attrib["myPlexSubscription"] = "0"
    root.attrib["myPlexUsername"] = ""
    root.attrib["platform"] = "Linux"
    root.attrib["platformVersion"] = " (#3 SMP PREEMPT Wed Nov 19 08:28:34 CET 2014)"
    root.attrib["requestParametersInCookie"] = "0"
    root.attrib["sync"] = "1"
    root.attrib["transcoderActiveVideoSessions"] = "0"
    root.attrib["transcoderAudio"] = "1"
    root.attrib["transcoderVideo"] = "1"
    root.attrib["transcoderVideoBitrates"] = "64,96,208,320,720,1500,2000,3000,4000,8000,10000,12000,20000"
    root.attrib["transcoderVideoQualities"] = "0,1,2,3,4,5,6,7,8,9,10,11,12"
    root.attrib["transcoderVideoRemuxOnly"] = "1"
    root.attrib["transcoderVideoResolutions"] = "128,128,160,240,320,480,768,720,720,1080,1080,1080,1080"
    root.attrib["updatedAt"] = "1466340239"
    root.attrib["version"] = "0.9.16.6.1993-5089475"

    for index, option in enumerate(["channels", "clients", "hubs", "library", "music", "neighborhood",
                                    "playQueues", "player", "playlists", "resources", "search", "server", "servers",
                                    "statistics", "system", "transcode", "updater", "video"]):
        root.append(xml.etree.ElementTree.Element("Directory", attrib={"count": "1", "key": option, "title": option}))

    return aiohttp.web.Response(body=b'<?xml version="1.0" encoding="UTF-8"?>' + xml.etree.ElementTree.tostring(root))


async def get_library_sections(request):
    video_playlists = await kodi_request(request.app,
                                         "Files.GetDirectory",
                                         ["special://videoplaylists/",
                                          "video",
                                          ["title", "file", "mimetype", "thumbnail"],
                                          {"method": "label",
                                           "order": "ascending",
                                           "ignorearticle": True}])

    video_playlists = video_playlists["result"]["files"]
    video_playlists_count = len(video_playlists)
    result = """<MediaContainer size="%d" allowSync="0" identifier="com.plexapp.plugins.library" mediaTagPrefix="/system/bundle/media/flags/"\
        mediaTagVersion="1420847353" title1="Plex Library">""" % (video_playlists_count + 1)

    # All Movies
    result += """<Directory allowSync="0" art="/:/resources/movie-fanart.jpg" filters="1" refreshing="0" thumb="/:/resources/movie.png"\
        key="0" type="movie" title="All Movies" composite="/library/sections/6/composite/1423495904" agent="com.plexapp.agents.themoviedb"\
        scanner="Plex Movie Scanner" updatedAt="1423495904" createdAt="1413134298" />"""

    # All TV Shows
    result += """<Directory key="1" type="show" title="All TV Shows" filters="1" />"""

    request.app["playlists"] = video_playlists
    for index, video_playlist in enumerate(video_playlists):
        result += """<Directory allowSync="0" art="/:/resources/movie-fanart.jpg" filters="1" refreshing="0" thumb="/:/resources/movie.png"\
            key="%d" type="movie" title="%s" composite="/library/sections/6/composite/1423495904" agent="com.plexapp.agents.themoviedb"\
            scanner="Plex Movie Scanner" updatedAt="1423495904" createdAt="1413134298" />""" \
            % (index + 2, video_playlist["label"])
    result += "</MediaContainer>"

    if request.app["debug"]:
        logger.debug(result)

    return aiohttp.web.Response(body=b'<?xml version="1.0" encoding="UTF-8"?>' + result.encode("utf8"))


async def get_all_movies(request, result_field_name, method):
    root = xml.etree.ElementTree.Element("MediaContainer", attrib={"identifier": "com.plexapp.plugins.library",
                                                                   "viewGroup": "movie"})

    option = request.match_info["option"]
    logger.debug("Get all movies with open %s", option)

    if 'all' == option:
        start_item = int(request.GET["X-Plex-Container-Start"])
        end_item = start_item + int(request.GET["X-Plex-Container-Size"])

        logger.debug("Requested all Movies from %d to %d", start_item, end_item)

        all_movies = await method

        root.attrib["totalSize"] = str(all_movies["result"]["limits"]["total"])

        if start_item != end_item:
            for movie in all_movies["result"][result_field_name]:
                if "movieid" in movie:
                    movie_id = str(movie.get("movieid"))
                else:
                    movie_id = str(movie["id"])
                root.append(xml.etree.ElementTree.Element("Video",
                                                          attrib={"id": movie_id,
                                                                  "type": "movie",
                                                                  "title": movie['label'],
                                                                  "rating": str(movie['rating']),
                                                                  "year": str(movie['year']),
                                                                  "thumb": movie['thumbnail'],
                                                                  "key": "/library/metadata/movie/%s" % movie_id}))
    elif "firstCharacter" == option:
        all_movies = await method

        character_dict = collections.defaultdict(int)
        for movie in all_movies["result"][result_field_name]:
            first_character = movie['label'].upper()[0]
            if first_character.isalpha():
                character_dict[first_character] += 1
            else:
                character_dict['#'] += 1

        for character in sorted(character_dict.keys()):
            root.append(xml.etree.ElementTree.Element("Directory", attrib={"size": str(character_dict[character]),
                                                                           "key": character,
                                                                           "title": character}))

    elif "sorts" == option:
        sort_dict = {"Date Added": "dateadded",
                     "Date Viewed": "lastplayed",
                     "Year": "year",
                     "Name": "label",
                     "Rating": "rating"}
        for sort_name, sort_key in sort_dict.items():
            root.append(xml.etree.ElementTree.Element("Directory", attrib={"defaultDirection": "desc",
                                                                           "descKey": "%s:desc" % sort_key,
                                                                           "key": sort_key,
                                                                           "title": sort_name}))

    if request.app["debug"]:
        logger.debug(_xml_prettify(root))
    return aiohttp.web.Response(body=b'<?xml version="1.0" encoding="UTF-8"?>' + xml.etree.ElementTree.tostring(root))


async def get_all_tvshows(request):
    root = xml.etree.ElementTree.Element("MediaContainer", attrib={"identifier": "com.plexapp.plugins.library",
                                                                   "viewGroup": "show"})

    option = request.match_info["option"]
    logger.debug("Get all tv shows with open %s", option)

    if 'all' == option:
        start_item = int(request.GET["X-Plex-Container-Start"])
        end_item = start_item + int(request.GET["X-Plex-Container-Size"])
        view_type = int(request.GET.get("type", 2))
        sort_type, sort_direction = request.GET.get("sort", "label:asc").split(":")
        sort_direction = "ascending" if sort_direction == "asc" else "descending"
        logger.debug("Requested all TV shows from %d to %d, sort by %s direction %s", start_item, end_item, sort_type, sort_direction)

        all_tv_shows = await kodi_request(request.app,
                                          "VideoLibrary.GetTVShows",
                                          {"properties": ["art", "rating", "thumbnail", "playcount", "file", "plot", "watchedepisodes",
                                                          "episode", "season"],
                                           "sort": {"order": sort_direction, "method": sort_type}})

        if start_item == 0 and end_item == 0:
            # workaround for bug in KODI where the result from limits
            # can't be trusted
            request.app["kodi_tvshow_total"] = len(all_tv_shows["result"]["tvshows"])
        root.attrib["totalSize"] = str(request.app["kodi_tvshow_total"])

        if start_item != end_item:
            for tv_show in all_tv_shows["result"]["tvshows"][start_item:end_item]:
                root.append(xml.etree.ElementTree.Element("Video",
                                                          attrib={"type": "show",
                                                                  "title": tv_show['label'],
                                                                  "summary": tv_show['plot'],
                                                                  "thumb": tv_show['thumbnail'],
                                                                  "leafCount": str(tv_show['episode']),
                                                                  "viewedLeafCount": str(tv_show['watchedepisodes']),
                                                                  "childCount": str(tv_show['season']),
                                                                  "key": "/library/metadata/tvshow/%d/children" % tv_show["tvshowid"]}))
    elif "firstCharacter" == option:
        all_movies = await kodi_request(request.app, "VideoLibrary.GetTVShows", {})

        character_dict = collections.defaultdict(int)
        for movie in all_movies["result"]["tvshows"]:
            first_character = movie['label'].upper()[0]
            if first_character.isalpha():
                character_dict[first_character] += 1
            else:
                character_dict['#'] += 1

        for character in sorted(character_dict.keys()):
            root.append(xml.etree.ElementTree.Element("Directory", attrib={"size": str(character_dict[character]),
                                                                           "key": character,
                                                                           "title": character}))
    elif "sorts" == option:
        sort_dict = {"Date Added": "dateadded",
                     "Date Viewed": "lastplayed",
                     "Name": "label",
                     "Rating": "rating"}
        for sort_name, sort_key in sort_dict.items():
            root.append(xml.etree.ElementTree.Element("Directory", attrib={"defaultDirection": "desc",
                                                                           "descKey": "%s:desc" % sort_key,
                                                                           "key": sort_key,
                                                                           "title": sort_name}))
    if request.app["debug"]:
        logger.debug(_xml_prettify(root))
    return aiohttp.web.Response(body=b'<?xml version="1.0" encoding="UTF-8"?>' + xml.etree.ElementTree.tostring(root))


async def get_library_section(request):
    """
    Returns the items for a sections
    """

    section_id = int(request.match_info['section_id'])
    sort_type, sort_direction = request.GET.get("sort", "label:asc").split(":")
    sort_direction = "ascending" if sort_direction == "asc" else "descending"
    logger.debug("Request for library section %s, sort type %s and direction %s", section_id, sort_type, sort_direction)

    if 0 == section_id:
        start_item = int(request.GET.get("X-Plex-Container-Start", 0))
        end_item = start_item + int(request.GET.get("X-Plex-Container-Size", 0))
        return await get_all_movies(request,
                                    "movies",
                                    kodi_request(request.app,
                                                 "VideoLibrary.GetMovies",
                                                 {"limits": {"start": start_item,
                                                             "end": end_item if end_item != start_item else start_item + 1},
                                                  "properties": ["rating", "thumbnail", "playcount", "file", "year"],
                                                  "sort": {"order": sort_direction, "method": sort_type}}))
    elif 1 == section_id:
        return await get_all_tvshows(request)
    else:
        section_id -= 2
        playlist = request.app["playlists"][section_id]
        pprint.pprint(playlist)
        return await get_all_movies(request,
                                    "files",
                                    kodi_request(request.app,
                                                 "Files.GetDirectory",
                                                 [playlist["file"],
                                                  "video",
                                                  ["rating", "thumbnail", "playcount", "file", "year"],
                                                  {"order": sort_direction, "method": sort_type}]))

    root = xml.etree.ElementTree.Element("MediaContainer", attrib={})
    if request.app["debug"]:
        logger.debug(_xml_prettify(root))
    return aiohttp.web.Response(body=b'<?xml version="1.0" encoding="UTF-8"?>' + xml.etree.ElementTree.tostring(root))


async def get_library_metadata_tvshow_info(request):
    tvshow_id = int(request.match_info["tvshow_id"])

    show_info = await kodi_request(request.app,
                                   "VideoLibrary.GetTVShowDetails",
                                   [tvshow_id,
                                    ["title", "genre", "year", "rating", "plot", "studio", "mpaa", "cast",
                                     "playcount", "episode", "imdbnumber", "premiered", "votes", "lastplayed",
                                     "fanart", "thumbnail",  "file", "originaltitle", "sorttitle", "episodeguide",
                                     "season", "watchedepisodes", "dateadded", "tag", "art"]])
    show_info = show_info["result"]["tvshowdetails"]

    root = xml.etree.ElementTree.Element("MediaContainer", attrib={"identifier": "com.plexapp.plugins.library"})

    video_node = xml.etree.ElementTree.Element("Directory",
                                               attrib={"type": "show",
                                                       "key": "/library/metadata/tvshow/%d/children" % tvshow_id,
                                                       "title": show_info['label'],
                                                       "studio": "" if not show_info['studio'] else show_info['studio'][0],
                                                       "summary": show_info['plot'],
                                                       "year": str(show_info['year']),
                                                       "rating": str(show_info["rating"]),
                                                       "art": show_info["fanart"],
                                                       "thumb": show_info['thumbnail']})
    root.append(video_node)

    if request.app["debug"]:
        logger.debug(_xml_prettify(root))
    return aiohttp.web.Response(body=b'<?xml version="1.0" encoding="UTF-8"?>' + xml.etree.ElementTree.tostring(root))

async def get_library_metadata_tvshow(request):
    tvshow_id = int(request.match_info["tvshow_id"])

    all_seasons = await kodi_request(request.app,
                                     "VideoLibrary.GetSeasons",
                                     [tvshow_id,
                                      ["season", "playcount", "watchedepisodes", "episode", "thumbnail", "tvshowid"]])

    root = xml.etree.ElementTree.Element("MediaContainer", attrib={"identifier": "com.plexapp.plugins.library",
                                                                   "viewGroup": "season",
                                                                   "key": str(tvshow_id)})

    for season in all_seasons["result"]["seasons"]:
        root.append(xml.etree.ElementTree.Element("Directory", attrib={"leafCount": str(season["episode"]),
                                                                       "type": "season",
                                                                       "title": season["label"],
                                                                       "index": str(season["season"]),
                                                                       "thumb": season['thumbnail'],
                                                                       "viewedLeafCount": str(season["watchedepisodes"]),
                                                                       "parentRatingKey": str(tvshow_id),
                                                                       "ratingKey": "tv%ds%d" % (tvshow_id, season['season']),
                                                                       "key": "/library/metadata/tvshow/%d/%d/children" % (tvshow_id, season['season'])}))
    if request.app["debug"]:
        logger.debug(_xml_prettify(root))
    return aiohttp.web.Response(body=b'<?xml version="1.0" encoding="UTF-8"?>' + xml.etree.ElementTree.tostring(root))


async def get_library_metadata_tvshow_season(request):
    tvshow_id = int(request.match_info["tvshow_id"])
    season = int(request.match_info["season"])

    if request.path.endswith("/children"):
        all_episodes = await kodi_request(request.app,
                                          "VideoLibrary.GetEpisodes",
                                          [tvshow_id,
                                           season,
                                           ["title", "plot", "votes", "rating", "writer", "firstaired", "playcount", "runtime",
                                            "director",  "productioncode",  "season",  "episode",  "originaltitle",  "showtitle",
                                            "cast",  "streamdetails",  "lastplayed",  "fanart",  "thumbnail",  "file",  "resume",
                                            "tvshowid",  "dateadded",  "uniqueid",  "art"]])

        root = xml.etree.ElementTree.Element("MediaContainer",
                                             attrib={"identifier": "com.plexapp.plugins.library",
                                                     "viewGroup": "episode",
                                                     "parentIndex": str(season),
                                                     "nocache": "1",
                                                     "key": str(tvshow_id)})

        for episode in all_episodes["result"]["episodes"]:
            root.append(xml.etree.ElementTree.Element("Video",
                                                      attrib={"type": "episode",
                                                              "title": episode["title"],
                                                              "index": str(episode["episode"]),
                                                              "thumb": episode['thumbnail'],
                                                              "summary": episode['plot'],
                                                              "viewCount": str(episode['playcount']),
                                                              "viewOffset": str(int(episode["resume"]["position"]*1000)),
                                                              "parentRatingKey": str(tvshow_id),
                                                              "key": "/library/metadata/episode/%d" % episode["episodeid"],
                                                              "parentKey": "/library/metadata/tvshow/%d/%d" % (tvshow_id, season)}))
    else:
        show_info = await kodi_request(request.app,
                                       "VideoLibrary.GetTVShowDetails",
                                       [tvshow_id,
                                        ["title", "genre", "year", "rating", "plot", "studio", "mpaa", "cast",
                                         "playcount", "episode", "imdbnumber", "premiered", "votes", "lastplayed",
                                         "fanart", "thumbnail",  "file", "originaltitle", "sorttitle", "episodeguide",
                                         "season", "watchedepisodes", "dateadded", "tag", "art"]])
        show_info = show_info["result"]["tvshowdetails"]

        root = xml.etree.ElementTree.Element("MediaContainer", attrib={"identifier": "com.plexapp.plugins.library"})
        root.append(xml.etree.ElementTree.Element("Directory",
                                                  attrib={"type": "season",
                                                          "parentRatingKey": str(tvshow_id),
                                                          "title": "Season %d" % season,
                                                          "parentTitle": show_info['label'],
                                                          "art": show_info["fanart"],
                                                          "thumb": show_info['thumbnail'],
                                                          "index": str(season),
                                                          "key": "/library/metadata/tvshow/%d/%d/children" % (tvshow_id, season)}))

    if request.app["debug"]:
        logger.debug(_xml_prettify(root))
    return aiohttp.web.Response(body=b'<?xml version="1.0" encoding="UTF-8"?>' + xml.etree.ElementTree.tostring(root))


async def get_library_metadata_episode(request):
    episode_id = int(request.match_info["episode_id"])

    root = xml.etree.ElementTree.Element("MediaContainer",
                                         attrib={"identifier": "com.plexapp.plugins.library"})
    root.append(await get_episode_node(request.app, episode_id))

    if request.app["debug"]:
        logger.debug(_xml_prettify(root))
    return aiohttp.web.Response(body=b'<?xml version="1.0" encoding="UTF-8"?>' + xml.etree.ElementTree.tostring(root))


async def get_library_metadata_movie(request):
    movie_id = int(request.match_info["movie_id"])
    return await _get_library_metadata_movie(request, movie_id)

async def _get_library_metadata_movie(request, movie_id):
    """
    Returns the metadata for a movie

    :returns: an empty MediaContainer
    """

    root = xml.etree.ElementTree.Element("MediaContainer", attrib={})
    root.append(await get_movie_node(request.app, movie_id))

    if request.app["debug"]:
        logger.debug(_xml_prettify(root))
    return aiohttp.web.Response(body=b'<?xml version="1.0" encoding="UTF-8"?>' + xml.etree.ElementTree.tostring(root))


async def get_prefs(request):
    root = xml.etree.ElementTree.Element("MediaContainer", attrib={})
    root.append(xml.etree.ElementTree.Element("Setting",
                                              attrib={"id": "FriendlyName",
                                                      "label": "Friendly name",
                                                      "default": "",
                                                      "summary": "This name will be used to identify this media server to other computers on your network."
                                                                 "If you leave it blank, your computer&apos;s name will be used instead.",
                                                      "type": "text",
                                                      "value": "",
                                                      "hidden": "0",
                                                      "advanced": "0",
                                                      "group": "general"}))

    if request.app["debug"]:
        logger.debug(_xml_prettify(root))

    return aiohttp.web.Response(body=b'<?xml version="1.0" encoding="UTF-8"?>' + xml.etree.ElementTree.tostring(root))


async def post_playqueues(request):
    play_uri = request.GET["uri"].split("%2F")
    video_id = int(play_uri[-1])

    print(request.GET["uri"])

    root = xml.etree.ElementTree.Element("MediaContainer",
                                         attrib={"playQueueID": str(request.app["playqueuecounter"] + 1),
                                                 "playQueueSelectedItemID": str(request.app["playqueuecounter"]),
                                                 "playQueueSelectedMetadataItemID": str(video_id),
                                                 "playQueueSourceURI": "library://50956afc-8f35-435d-9643-4142a7232186/item/%2Flibrary%2Fmetadata%2F"
                                                 + str(video_id),
                                                 "playQueueSelectedItemOffset": "0"})

    request.app["playqueuecounter"] += 1

    if "movie" == play_uri[-2]:
        root.append(await get_movie_node(request.app, video_id))
    elif "episode" == play_uri[-2]:
        pass
        root.append(await get_episode_node(request.app, video_id))

    if request.app["debug"]:
        logger.debug(_xml_prettify(root))

    return aiohttp.web.Response(body=b'<?xml version="1.0" encoding="UTF-8"?>' + xml.etree.ElementTree.tostring(root))


async def get_empty(request):
    """
    Simple handler for unknown requests

    :returns: an empty MediaContainer
    """
    root = xml.etree.ElementTree.Element("MediaContainer", attrib={})
    if request.app["debug"]:
        logger.debug(_xml_prettify(root))
    return aiohttp.web.Response(body=b'<?xml version="1.0" encoding="UTF-8"?>' + xml.etree.ElementTree.tostring(root))


async def get_kodidownload(request):
    """
    Downloads a file from KODI

    :returns: returns the file
    """

    download_info = await kodi_request(request.app, "Files.PrepareDownload", [request.GET["url"]])
    download_url = request.app["kodi"] + download_info['result']['details']['path']

    kodi_response = await request.app["client_session"].get(download_url)
    logger.debug("Download URL: %s", download_url)
    return aiohttp.web.Response(body=await kodi_response.read())


async def send_websocket_notification(app):
    for ws in app['websockets']:
        ws.send_str("""{
    "_elementType": "NotificationContainer",
    "type": "timeline",
    "size": 1,
    "_children": [
        {
            "_elementType": "TimelineEntry",
            "sectionID": 1,
            "itemID": 8,
            "type": 1,
            "title": "Life of Crime",
            "state": 5,
            "mediaState": "analyzing",
            "updatedAt": 1467101125
        }
    ]
}""")


async def websocket_handler(request):
    # Create response
    resp = aiohttp.web.WebSocketResponse()

    # try to uypdate
    ok, protocol = resp.can_prepare(request)
    if not ok:
        logger.error("Couldn't upgrade to WebSocket")
        return None

    # repare
    await resp.prepare(request)

    # add to clients
    request.app['websockets'].append(resp)
    logger.debug("WebSocket connected")

    # keep the connections
    async for msg in resp:
        # just loop for now
        pass

    # we are done => disconnect and remove
    request.app['websockets'].remove(resp)
    logger.debug('WebSocket disconnected')

    # return
    return resp

if __name__ == "__main__":
    # parse the command line arguments
    parser = argparse.ArgumentParser(description='Kodi2Plex')
    parser.add_argument('-kp', '--kodi-port', metavar='port', type=int, help='Port if the kodi web interface', default=8080)
    parser.add_argument('-kh', '--kodi-host', metavar='ip/hostname', type=str, help='Name or IP of the kodi machine')
    parser.add_argument('-pp', '--plex-port', metavar='port', type=int, help='Port of the plex interface (default=32400)', default=32400)
    parser.add_argument('-pw', '--plex-web', metavar='location of WebClient.bundle', type=str,
                        help='location of the WebClient.bundle to activate the Plex Web Client')
    parser.add_argument('-gdm', action='store_true', help="Broadcast the server via GDM (Good day mate) so Plex client can find the server automatically")
    parser.add_argument('-n', '--name', metavar='display name', type=str, help='Name for display in Plex', default="Kodi2Plex")
    parser.add_argument('-v', '--verbose', action='store_true', help="Shows a lot of messages")
    parser.add_argument('-d', '--debug', action='store_true', help="Shows a lot of DEBUG messages!!!!")

    args = parser.parse_args()

    # create the logegr
    logger = logging.getLogger("kodi2plex")
    # add a stream handler
    ch = logging.StreamHandler()
    logger.addHandler(ch)

    # set logging.DEBUG if the user has specified -v or -d
    if args.verbose or args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug(args)

    # no host => no go
    if not args.kodi_host:
        logger.error("No kodi host defined")
        sys.exit(-1)

    # the MAIN LOOP we are living in
    main_loop = asyncio.get_event_loop()
    # the aiohttp Application instance (subclass of dict)
    kodi2plex_app = aiohttp.web.Application(middlewares=[IndexMiddleware()],  # the middleware is required to
                                                                              # convert */ to */index.html
                                            loop=main_loop,
                                            logger=logger)

    # set some settings
    kodi2plex_app["title"] = args.name
    kodi2plex_app["kodi"] = "http://%s:%d/" % (args.kodi_host, args.kodi_port)
    kodi2plex_app["kodi_url"] = "http://%s:%d/jsonrpc" % (args.kodi_host, args.kodi_port)
    kodi2plex_app["server_ip"] = socket.gethostbyname(socket.gethostname())
    kodi2plex_app["kodi_jsonrpc_counter"] = 0
    kodi2plex_app["client_session"] = aiohttp.ClientSession()
    kodi2plex_app["playlists"] = []
    kodi2plex_app["debug"] = args.debug
    kodi2plex_app["playqueuecounter"] = 0

    main_loop.run_until_complete(init_kodi(kodi2plex_app))

    # Has the user defined a path to the WebClient.bundle from Plex?
    if args.plex_web:
        # try using it
        web_path = os.path.join(os.path.realpath(args.plex_web), "Contents", "Resources")

        # Does it exist?
        if not os.path.exists(web_path):
            logger.error("WebClient path does not exists: %s", web_path)
            sys.exit(-1)

        logger.info("Using WebClient from %s", web_path)

        # add a route to the directory
        kodi2plex_app.router.add_static('/web/', web_path)

    kodi2plex_app.router.add_route('GET', '/', get_root)
    kodi2plex_app.router.add_route('GET', '/library/sections', get_library_sections)
    kodi2plex_app.router.add_route('GET', '/library/sections/{section_id:\d+}/{option}', get_library_section)
    kodi2plex_app.router.add_route('GET', '/library/metadata/movie/{movie_id:\d+}', get_library_metadata_movie)
    kodi2plex_app.router.add_route('GET', '/library/metadata/tvshow/{tvshow_id:\d+}', get_library_metadata_tvshow_info)
    kodi2plex_app.router.add_route('GET', '/library/metadata/tvshow/{tvshow_id:\d+}/children', get_library_metadata_tvshow)
    kodi2plex_app.router.add_route('GET', '/library/metadata/tvshow/{tvshow_id:\d+}/{season:\d+}', get_library_metadata_tvshow_season)
    kodi2plex_app.router.add_route('GET', '/library/metadata/tvshow/{tvshow_id:\d+}/{season:\d+}/children', get_library_metadata_tvshow_season)
    kodi2plex_app.router.add_route('GET', '/library/metadata/episode/{episode_id:\d+}', get_library_metadata_episode)
    kodi2plex_app.router.add_route('GET', '/:/prefs', get_prefs)

    kodi2plex_app.router.add_route('POST', '/playQueues', post_playqueues)

    kodi2plex_app.router.add_route('GET', '/photo/:/transcode', get_kodidownload)

    kodi2plex_app['websockets'] = []
    kodi2plex_app.router.add_route('GET', '/:/websockets/{path:.*}', websocket_handler)

    # per default we return an empty MediaContainer
    # !!!!! NEEDS TO BE THE LAST ROUTE
    kodi2plex_app.router.add_route('GET', '/{tail:.*}', get_empty)

    # setup gdm?
    if args.gdm:
        GDM_ADDR = '239.0.0.250'
        GDM_PORT = 32414

        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('', GDM_PORT))
        # add the socket to the multicast group on all interfaces.
        group = socket.inet_aton(GDM_ADDR)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        gdm_thread = threading.Thread(target=gdm_broadcast, args=(sock, kodi2plex_app))
        gdm_thread.start()

    handler = kodi2plex_app.make_handler(debug=args.debug, access_log=logger if args.debug or args.verbose else None)
    f = main_loop.create_server(handler, '0.0.0.0', args.plex_port)
    srv = main_loop.run_until_complete(f)
    logger.debug('serving on %s', srv.sockets[0].getsockname())
    try:
        main_loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.close()
        main_loop.run_until_complete(srv.wait_closed())
        main_loop.run_until_complete(kodi2plex_app.shutdown())
        main_loop.run_until_complete(handler.finish_connections(60.0))
        main_loop.run_until_complete(kodi2plex_app.cleanup())
    main_loop.close()

    # shut down GDM nicely
    if args.gdm:
        sock.close()
        gdm_thread.join()
