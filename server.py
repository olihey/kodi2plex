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
import xml.etree.ElementTree

import aiohttp
import aiohttp.web


video_codec_map = {"avc1": "h264", "hev1": "hevc", "hevc": "hevc"}


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
        logger.debug("Sending to %s\nDATA:\n%s", app["kodi_url"], payload)

    # fire up the request
    kodi_response = await app["client_session"].post(app["kodi_url"],
                                                     data=json.dumps(payload).encode("utf8"),
                                                     headers={'content-type': 'application/json'})
    kodi_json = await kodi_response.json()
    if app["debug"]:
        logger.debug("Result:\n%s", kodi_json)
    return kodi_json


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


async def get_video_node(app, movie_id):
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
                                                       "duration": str(movie_info["runtime"] * 1000),
                                                       "thumb": movie_info['thumbnail']})

    part_node = None
    try:
        video_codec = movie_info["streamdetails"]["video"][0]["codec"]
        media_node = xml.etree.ElementTree.Element("Media",
                                                   attrib={"duration": str(movie_info["runtime"] * 1000),
                                                           "width": str(movie_info["streamdetails"]["video"][0]["width"]),
                                                           "height": str(movie_info["streamdetails"]["video"][0]["height"]),
                                                           "aspectRatio": str(movie_info["streamdetails"]["video"][0]["aspect"]),
                                                           "audioChannels": str(movie_info["streamdetails"]["audio"][0]["channels"]),
                                                           "container": "mp4",
                                                           "optimizedForStreaming": "1",
                                                           "audioCodec": movie_info["streamdetails"]["audio"][0]["codec"],
                                                           "videoCodec": video_codec_map.get(video_codec, video_codec)})
        video_node.append(media_node)

        download_info = await kodi_request(app, "Files.PrepareDownload", [movie_info["file"]])
        download_url = app["kodi"] + download_info['result']['details']['path']

        part_node = xml.etree.ElementTree.Element("Part",
                                                  attrib={"accessible": "1",
                                                          "id": str(movie_id),
                                                          "container": "mp4",
                                                          "optimizedForStreaming": "1",
                                                          "key": download_url})
        media_node.append(part_node)
    except:
        logger.error("Error while getting stream details for movie %d, error: %s", movie_id, traceback.format_exc())

    if part_node:
        stream_counter = 0
        for video in movie_info["streamdetails"]["video"]:
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

        for audio in movie_info["streamdetails"]["audio"]:
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

    for director in movie_info["director"]:
        director_node = xml.etree.ElementTree.Element("Director", attrib={"tag": director})
        video_node.append(director_node)
    for genre in movie_info["genre"]:
        genre_node = xml.etree.ElementTree.Element("Genre", attrib={"tag": genre})
        video_node.append(genre_node)
    for writer in movie_info["writer"]:
        writer_node = xml.etree.ElementTree.Element("Writer", attrib={"tag": writer})
        video_node.append(writer_node)
    for country in movie_info["country"]:
        country_node = xml.etree.ElementTree.Element("Country", attrib={"tag": country})
        video_node.append(country_node)
    for cast in movie_info["cast"]:
        cast_node = xml.etree.ElementTree.Element("Role", attrib={"tag": cast["name"],
                                                                  "role": cast["role"]})
        video_node.append(cast_node)

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
    result += """<Directory key="1" type="show" title="All TV Shows" />"""

    for index, video_playlist in enumerate(video_playlists):
        result += """<Directory allowSync="0" art="/:/resources/movie-fanart.jpg" filters="1" refreshing="0" thumb="/:/resources/movie.png"\
            key="%d" type="movie" title="%s" composite="/library/sections/6/composite/1423495904" agent="com.plexapp.agents.themoviedb"\
            scanner="Plex Movie Scanner" updatedAt="1423495904" createdAt="1413134298" />""" \
            % (index + 2, video_playlist["label"])
    result += "</MediaContainer>"

    if request.app["debug"]:
        logger.debug(result)

    return aiohttp.web.Response(body=b'<?xml version="1.0" encoding="UTF-8"?>' + result.encode("utf8"))


async def get_all_movies(request):
    root = xml.etree.ElementTree.Element("MediaContainer", attrib={"identifier": "com.plexapp.plugins.library",
                                                                   "viewGroup": "movie"})

    option = request.match_info["option"]
    logger.debug("Get all movies with open %s", option)

    if 'all' == option:
        start_item = int(request.GET["X-Plex-Container-Start"])
        end_item = start_item + int(request.GET["X-Plex-Container-Size"])
        logger.debug("Requested all Movies from %d to %d", start_item, end_item)

        all_movies = await kodi_request(request.app, "VideoLibrary.GetMovies",
                                        {"limits": {"start": start_item,
                                                    "end": end_item if end_item != start_item else start_item + 1},
                                         "properties": ["art", "rating", "thumbnail", "playcount", "file"],
                                         "sort": {"order": "ascending", "method": "label"}})

        root.attrib["totalSize"] = str(all_movies["result"]["limits"]["total"])

        if start_item != end_item:
            for movie in all_movies["result"]["movies"]:
                root.append(xml.etree.ElementTree.Element("Video",
                                                          attrib={"id": str(movie["movieid"]),
                                                                  "type": "movie",
                                                                  "title": movie['label'],
                                                                  "thumb": movie['thumbnail'],
                                                                  "key": "/library/metadata/movie/%d" % movie["movieid"]}))
    elif "firstCharacter" == option:
        all_movies = await kodi_request(request.app, "VideoLibrary.GetMovies", {})

        character_dict = collections.defaultdict(int)
        for movie in all_movies["result"]["movies"]:
            first_character = movie['label'].upper()[0]
            if first_character.isalpha():
                character_dict[first_character] += 1
            else:
                character_dict['#'] += 1

        for character in sorted(character_dict.keys()):
            root.append(xml.etree.ElementTree.Element("Directory", attrib={"size": str(character_dict[character]),
                                                                           "key": character,
                                                                           "title": character}))

    if request.app["debug"]:
        logger.debug(xml.etree.ElementTree.tostring(root))
    return aiohttp.web.Response(body=b'<?xml version="1.0" encoding="UTF-8"?>' + xml.etree.ElementTree.tostring(root))


def get_all_tvshows(request):
    root = xml.etree.ElementTree.Element("MediaContainer", attrib={})
    if request.app["debug"]:
        logger.debug(xml.etree.ElementTree.tostring(root))
    return aiohttp.web.Response(body=b'<?xml version="1.0" encoding="UTF-8"?>' + xml.etree.ElementTree.tostring(root))


async def get_library_section(request):
    """
    Returns the items for a sections
    """

    section_id = request.match_info['section_id']
    logger.debug("Request for library section %s", section_id)

    if "0" == section_id:
        return await get_all_movies(request)
    elif "1" == section_id:
        return get_all_tvshows(request)

    root = xml.etree.ElementTree.Element("MediaContainer", attrib={})
    if request.app["debug"]:
        logger.debug(xml.etree.ElementTree.tostring(root))
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
    root.append(await get_video_node(request.app, movie_id))

    if request.app["debug"]:
        logger.debug(xml.etree.ElementTree.tostring(root))
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
        logger.debug(xml.etree.ElementTree.tostring(root))

    return aiohttp.web.Response(body=b'<?xml version="1.0" encoding="UTF-8"?>' + xml.etree.ElementTree.tostring(root))


async def post_playqueues(request):
    movie_id = int(request.GET["uri"].split("%2F")[-1])

    root = xml.etree.ElementTree.Element("MediaContainer", attrib={"playQueueID": str(request.app["playqueuecounter"] + 1),
                                                                   "playQueueSelectedItemID": str(request.app["playqueuecounter"]),
                                                                   "playQueueSelectedMetadataItemID": str(movie_id),
                                                                   "playQueueSourceURI": "library://50956afc-8f35-435d-9643-4142a7232186/item/%2Flibrary%2Fmetadata%2F" + str(movie_id),
                                                                   "playQueueSelectedItemOffset": "0"})

    request.app["playqueuecounter"] += 1

    root.append(await get_video_node(request.app, movie_id))

    if request.app["debug"]:
        logger.debug(xml.etree.ElementTree.tostring(root))

    return aiohttp.web.Response(body=b'<?xml version="1.0" encoding="UTF-8"?>' + xml.etree.ElementTree.tostring(root))


async def get_empty(request):
    """
    Simple handler for unknown requests

    :returns: an empty MediaContainer
    """
    root = xml.etree.ElementTree.Element("MediaContainer", attrib={})
    if request.app["debug"]:
        logger.debug(xml.etree.ElementTree.tostring(root))
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
    kodi2plex_app["debug"] = args.debug
    kodi2plex_app["playqueuecounter"] = 0

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
    f = main_loop.create_server(handler, '0.0.0.0', 32400)
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
