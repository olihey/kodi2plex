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
import argparse
import threading
import http.server
import socketserver
import urllib.request
import xml.etree.ElementTree

kodi_jsonrpc_headers = {'content-type': 'application/json'}
kodi_jsonrpc_counter = 0

# dictionary holding settings for this instance
settings = {}


def kodi_request(method, params):
    """
    Sends a JSON formatted message to the server
    returns the result as dictionary (from json response)
    """
    global kodi_jsonrpc_counter

    # create the request
    payload = {
        "method": method,
        "params": params,
        "jsonrpc": "2.0",
        "id": kodi_jsonrpc_counter,
    }

    # increase the message counter
    kodi_jsonrpc_counter += 1

    # fire up the request
    req = urllib.request.Request(settings["kodi_url"], data=json.dumps(payload).encode("utf8"), headers=kodi_jsonrpc_headers)
    response = urllib.request.urlopen(req)
    return json.loads(response.read().decode("utf8"))


def gdm_broadcast(gdm_socket):
    """
    Function to send response for GDM requests from
    Plex clients
    """

    # response as string
    response_message = """HTTP/1.1 200 OK\r
Content-Type: plex/media-server\r
Name: %s\r
Port: 32400\r
Resource-Identifier: 23f2d6867befb9c26f7b5f366d4dd84e9b2294c9\r
Updated-At: 1466340239\r
Version: 0.9.16.6.1993-5089475\r
Parameters: playerAdd=192.168.2.102\r\n""" % settings["title"]

    # convert to bytes
    response_message = response_message.encode("utf8")

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
            gdm_socket.sendto(response_message, address)
        else:
            logger.warn('recieved wrong MSearch')

        time.sleep(5)


class Kodi2Plex(http.server.BaseHTTPRequestHandler):
    """
    Main request handler
    """
    web_path = None

    def do_POST(self):
        logger.debug("POST %s", self.path)
        return

    def do_PUT(self):
        logger.debug("PUT %s", self.path)
        return

    def do_GET(self):
        """
        Respond to GET request
        """
        path = self.path

        # first check for service static WebClient files
        if web_path and path.startswith("/web/"):
            web_filename = path[5:]
            if not web_filename:
                web_filename = "index.html"

            web_filename = os.path.join(web_path, web_filename)
            if not os.path.exists(web_filename):
                self.send_error(404)

            send_reply = False
            if web_filename.endswith(".html"):
                mimetype = 'text/html'
                send_reply = True
            elif web_filename.endswith(".jpg"):
                mimetype = 'image/jpg'
                send_reply = True
            elif web_filename.endswith(".gif"):
                mimetype = 'image/gif'
                send_reply = True
            elif web_filename.endswith(".js"):
                mimetype = 'application/javascript'
                send_reply = True
            elif web_filename.endswith(".css"):
                mimetype = 'text/css'
                send_reply = True

            if send_reply:
                self.send_response(200)
                self.send_header('Content-type', mimetype)
                self.end_headers()

                with open(web_filename, "rb") as web_file:
                    self.wfile.write(web_file.read())

        elif path == "/":
            # root
            root = xml.etree.ElementTree.Element("MediaContainer", attrib={})
            root.attrib["allowMediaDeletion"] = "1"
            root.attrib["friendlyName"] = settings["title"]
            root.attrib["machineIdentifier"] = "XXXXXXXX"
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
            root.attrib["updatedAt"] = "1423682517"
            root.attrib["version"] = "0.9.12.0"

            for option in ["library"]:
                root.append(xml.etree.ElementTree.Element("Directory", attrib={"count": "1", "key": option, "title": option}))

            self.send_response(200)
            self.send_header('Content-type', "application/xml")
            self.end_headers()

            self.wfile.write(xml.etree.ElementTree.tostring(root))

        elif path == '/library/sections':
            video_playlists = kodi_request("Files.GetDirectory",
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

            self.send_response(200)
            self.send_header('Content-type', "application/xml")
            self.end_headers()

            self.wfile.write(result.encode("utf8"))

        elif path == '/:/prefs':
            root = xml.etree.ElementTree.Element("MediaContainer", attrib={})
            root.append(xml.etree.ElementTree.Element("Setting",
                                                      attrib={"id": "FriendlyName",
                                                              "label": "Friendly name",
                                                              "default": "",
                                                              "summary": "This name will be used to identify this media server to other computers on your network. If you leave it blank, your computer&apos;s name will be used instead.",
                                                              "type": "text",
                                                              "value": "",
                                                              "hidden": "0",
                                                              "advanced": "0",
                                                              "group": "general"}))

            self.send_response(200)
            self.send_header('Content-type', "application/xml")
            self.end_headers()

            self.wfile.write(xml.etree.ElementTree.tostring(root))
        else:
            # return error on everything we don't know :)'
            self.send_response(200)
            self.send_header('Content-type', "application/xml")
            self.end_headers()

            self.wfile.write(b'<MediaContainer size="0" />')


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """Handle requests in a separate thread."""

if __name__ == "__main__":
    logger = logging.getLogger("kodi2plex")
    ch = logging.StreamHandler()
    logger.addHandler(ch)

    # parse the command line arguments
    parser = argparse.ArgumentParser(description='Kodi2Plex')
    parser.add_argument('-kp', '--kodi-port', metavar='port', type=int, help='Port if the kodi web interface', default=8080)
    parser.add_argument('-kh', '--kodi-host', metavar='ip/hostname', type=str, help='Name or IP of the kodi machine')
    parser.add_argument('-pp', '--plex-port', metavar='port', type=int, help='Port of the plex interface (default=32400)', default=32400)
    parser.add_argument('-pw', '--plex-web', metavar='location of WebClient.bundle', type=str,
                        help='location of the WebClient.bundle to activate the Plex Web Client')
    parser.add_argument('-gdm', action='store_true', help="Broadcast the server via GDM (Good day mate) so Plex client can find the server automatically")
    parser.add_argument('-n', '--name', metavar='display name', type=str, help='Name for display in Plex', default="Kodi2Plex")
    parser.add_argument('-v', '--verbose', action='store_true', help="Shows a lot of debug messages")

    args = parser.parse_args()

    # no host => no go
    if not args.kodi_host:
        logger.error("No kodi host defined")
        sys.exit(-1)

    # user wants debug messages?
    if args.verbose:
        # Sure, here we go
        logger.setLevel(logging.DEBUG)

    # setup the settings accorsing to the users wishes
    settings["title"] = args.name
    settings["kodi_url"] = "http://%s:%d/jsonrpc" % (args.kodi_host, args.kodi_port)

    # if there is a web client defined
    if args.plex_web:
        # trye using it
        web_path = os.path.join(os.path.realpath(args.plex_web), "Contents", "Resources")

        # Does it exist?
        if not os.path.exists(web_path):
            logger.error("WebClient path does not exists: %s", web_path)
            sys.exit(-1)

        logger.info("Using WebClient from %s", web_path)

        settings["web_path"] = web_path

    server = ThreadedHTTPServer(('0.0.0.0', args.plex_port), Kodi2Plex)

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
        gdm_thread = threading.Thread(target=gdm_broadcast, args=(sock,))
        gdm_thread.start()

    logger.info('Starting Kodi2Plex, use <Ctrl-C> to stop')

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")

    if args.gdm:
        sock.close()
        gdm_thread.join()
