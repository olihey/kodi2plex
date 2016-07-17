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
import http.server
import socketserver
import urllib.request
import xml.etree.ElementTree

import aiohttp
import aiohttp.web


@asyncio.coroutine
def kodi_request(app, method, params):
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
    kodi_response = yield from app["client_session"].post(app["kodi_url"],
                                                          data=json.dumps(payload).encode("utf8"),
                                                          headers={'content-type': 'application/json'})
    kodi_json = yield from kodi_response.json()
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


@asyncio.coroutine
def get_root(request):
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

    for option in ["library"]:
        root.append(xml.etree.ElementTree.Element("Directory", attrib={"count": "1", "key": option, "title": option}))

    return aiohttp.web.Response(body=xml.etree.ElementTree.tostring(root))


@asyncio.coroutine
def get_library_sections(request):
    video_playlists = yield from kodi_request(request.app, "Files.GetDirectory",
                                              ["special://videoplaylists/", "video",
                                               ["title", "file", "mimetype", "thumbnail"],
                                               {"method": "label",
                                                "order": "ascending",
                                                "ignorearticle": True}])

    video_playlists = video_playlists["result"]["files"]
    video_playlists_count = len(video_playlists)
    result = """<MediaContainer size="%d" allowSync="0" identifier="com.plexapp.plugins.library" mediaTagPrefix="/system/bundle/media/flags/"\
        mediaTagVersion="1420847353" title1="Plex Library">""" % (video_playlists_count + 1)

    result += """<Directory allowSync="0" art="/:/resources/movie-fanart.jpg" filters="1" refreshing="0" thumb="/:/resources/movie.png"\
        key="0" type="movie" title="All Movies" composite="/library/sections/6/composite/1423495904" agent="com.plexapp.agents.themoviedb"\
        scanner="Plex Movie Scanner" language="de" uuid="4af6da95-dab8-4dcb-98d8-4f5cd0accc33" updatedAt="1423495904" createdAt="1413134298" />"""

    for index, video_playlist in enumerate(video_playlists):
        result += """<Directory allowSync="0" art="/:/resources/movie-fanart.jpg" filters="1" refreshing="0" thumb="/:/resources/movie.png"\
            key="%d" type="movie" title="%s" composite="/library/sections/6/composite/1423495904" agent="com.plexapp.agents.themoviedb"\
            scanner="Plex Movie Scanner" language="de" uuid="4af6da95-dab8-4dcb-98d8-4f5cd0accc33" updatedAt="1423495904" createdAt="1413134298" />""" \
            % (index + 1, video_playlist["label"])
    result += "</MediaContainer>"

    if request.app["debug"]:
        logger.debug(result)

    return aiohttp.web.Response(body=result.encode("utf8"))


@asyncio.coroutine
def get_prefs(request):
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

    return aiohttp.web.Response(body=xml.etree.ElementTree.tostring(root))


@asyncio.coroutine
def get_empty(request):
    """
    Simple handler for unknown requests

    :returns: an empty MediaContainer
    """
    root = xml.etree.ElementTree.Element("MediaContainer", attrib={})
    if request.app["debug"]:
        logger.debug(xml.etree.ElementTree.tostring(root))
    return aiohttp.web.Response(body=xml.etree.ElementTree.tostring(root))


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

    logger = logging.getLogger("kodi2plex")
    ch = logging.StreamHandler()
    logger.addHandler(ch)

    if args.verbose or args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug(args)

    # no host => no go
    if not args.kodi_host:
        logger.error("No kodi host defined")
        sys.exit(-1)

    main_loop = asyncio.get_event_loop()
    kodi2plex_app = aiohttp.web.Application(middlewares=[IndexMiddleware()], loop=main_loop, logger=logger)

    kodi2plex_app["title"] = args.name
    kodi2plex_app["kodi_url"] = "http://%s:%d/jsonrpc" % (args.kodi_host, args.kodi_port)
    kodi2plex_app["server_ip"] = socket.gethostbyname(socket.gethostname())
    kodi2plex_app["kodi_jsonrpc_counter"] = 0
    kodi2plex_app["client_session"] = aiohttp.ClientSession()
    kodi2plex_app["debug"] = args.debug

    if args.plex_web:
        # trye using it
        web_path = os.path.join(os.path.realpath(args.plex_web), "Contents", "Resources")

        # Does it exist?
        if not os.path.exists(web_path):
            logger.error("WebClient path does not exists: %s", web_path)
            sys.exit(-1)

        logger.info("Using WebClient from %s", web_path)

        kodi2plex_app.router.add_static('/web/', web_path)

    kodi2plex_app.router.add_route('GET', '/', get_root)
    kodi2plex_app.router.add_route('GET', '/library/sections', get_library_sections)
    kodi2plex_app.router.add_route('GET', '/:/prefs', get_prefs)

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
