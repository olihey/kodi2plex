import os
import sys
import json
import urllib.request
import threading

import bottle

web_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "WebClient.bundle", "Contents", "Resources")

kodi_jsonrpc_url = "http://192.168.2.2:8080/jsonrpc"
kodi_jsonrpc_headers = {'content-type': 'application/json'}
kodi_jsonrpc_counter = 0

settings = {"title": "kodi2plex"}


def kodi_request(method, params):
    global kodi_jsonrpc_counter
    # Example echo method
    payload = {
        "method": method,
        "params": params,
        "jsonrpc": "2.0",
        "id": kodi_jsonrpc_counter,
    }
    kodi_jsonrpc_counter += 1
    # return requests.post(kodi_jsonrpc_url, data=json.dumps(payload), headers=kodi_jsonrpc_headers).json()
    req = urllib.request.Request(kodi_jsonrpc_url, data=json.dumps(payload).encode("utf8"), headers=kodi_jsonrpc_headers)
    response = urllib.request.urlopen(req)
    return json.loads(response.read().decode("utf8"))


@bottle.route('/')
def root():
    return """<MediaContainer size="12" allowMediaDeletion="1" friendlyName="kodi2plex" machineIdentifier="sdfsdf" myPlex="1" myPlexMappingState="unknown" myPlexSigninState="none" myPlexSubscription="0" myPlexUsername="" platform="Linux" platformVersion=" (#3 SMP PREEMPT Wed Nov 19 08:28:34 CET 2014)" requestParametersInCookie="1" sync="1" transcoderActiveVideoSessions="0" transcoderAudio="1" transcoderVideo="1" transcoderVideoBitrates="64,96,208,320,720,1500,2000,3000,4000,8000,10000,12000,20000" transcoderVideoQualities="0,1,2,3,4,5,6,7,8,9,10,11,12" transcoderVideoRemuxOnly="1" transcoderVideoResolutions="128,128,160,240,320,480,768,720,720,1080,1080,1080,1080" updatedAt="1423682517" version="0.9.12.0">
	<Directory count="1" key="butler" title="butler" />
	<Directory count="1" key="channels" title="channels" />
	<Directory count="1" key="clients" title="clients" />
	<Directory count="1" key="library" title="library" />
	<Directory count="1" key="playQueues" title="playQueues" />
	<Directory count="1" key="player" title="player" />
	<Directory count="1" key="playlists" title="playlists" />
	<Directory count="1" key="search" title="search" />
	<Directory count="1" key="servers" title="servers" />
	<Directory count="1" key="system" title="system" />
	<Directory count="1" key="transcode" title="transcode" />
	<Directory count="1" key="video" title="video" />
</MediaContainer>"""


@bottle.route('/library/sections')
def library_sections():
    video_playlists = kodi_request("Files.GetDirectory", ["special://videoplaylists/", "video",
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
        print(video_playlist)
        result += """<Directory allowSync="0" art="/:/resources/movie-fanart.jpg" filters="1" refreshing="0" thumb="/:/resources/movie.png"\
         key="%d" type="movie" title="%s" composite="/library/sections/6/composite/1423495904" agent="com.plexapp.agents.themoviedb"\
          scanner="Plex Movie Scanner" language="de" uuid="4af6da95-dab8-4dcb-98d8-4f5cd0accc33" updatedAt="1423495904" createdAt="1413134298" />""" \
          % (index + 1, video_playlist["label"])
    result += "</MediaContainer>"
    return result


@bottle.route('/library/sections/<id:int>')
@bottle.route('/library/sections/<id:int>/<addon>')
def library_sections_id(id, addon=None):
    if "all" == addon:
        return """<MediaContainer size="50" totalSize="56" allowSync="1" art="/:/resources/movie-fanart.jpg" identifier="com.plexapp.plugins.library" librarySectionID="6" librarySectionTitle="Ina Filme" librarySectionUUID="4af6da95-dab8-4dcb-98d8-4f5cd0accc33" mediaTagPrefix="/system/bundle/media/flags/" mediaTagVersion="1420847353" offset="0" thumb="/:/resources/movie.png" title1="Ina Filme" title2="All Ina Filme" viewGroup="movie" viewMode="65592">
	<Video ratingKey="3139" key="/library/metadata/3139" studio="Annapurna Pictures" type="movie" title="American Hustle" contentRating="NR" summary="A con man, Irving Rosenfeld, along with his seductive partner Sydney Prosser, is forced to work for a wild FBI agent, Richie DiMaso, who pushes them into a world of Jersey powerbrokers and mafia." rating="7.0999999046325701" year="2014" thumb="/library/metadata/3139/thumb/1413152421" art="/library/metadata/3139/art/1413152421" duration="8274047" originallyAvailableAt="2014-02-13" addedAt="1413152276" updatedAt="1413152421">
		<Media videoResolution="1080" id="2911" duration="8274047" bitrate="8317" width="1920" height="800" aspectRatio="2.35" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="1">
			<Part id="2911" key="/library/parts/2911/file.mp4" duration="8274047" file="/mnt/media/Ina Filme/American Hustle (2014).mp4" size="8602250728" container="mp4" has64bitOffsets="1" hasChapterTextStream="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Drama" />
		<Writer tag="David O. Russell" />
		<Writer tag="Eric Singer" />
		<Director tag="David O. Russell" />
		<Country tag="USA" />
		<Role tag="Christian Bale" />
		<Role tag="Bradley Cooper" />
		<Role tag="Amy Adams" />
	</Video>
	<Video ratingKey="3140" key="/library/metadata/3140" studio="Smokehouse Pictures" type="movie" title="Argo" contentRating="R" summary="Auf dem Höhepunkt der iranischen Revolution wird am 4. November 1979 die US- Botschaft in Teheran gestürmt - militante Studenten nehmen 52 Amerikaner als Geiseln. Doch mitten in diesem Chaos gelingt es sechs Amerikanern, sich davon zu schleichen und in das Haus des kanadischen Botschafters zu fliehen. Es ist nur eine Frage der Zeit, bis der Verbleib der sechs bekannt wird - ihr Leben steht auf dem Spiel. Deshalb entwirft der auf das &quot;Ausfiltern&quot;spezialisierte CIA-Agent Tony Mendez einen riskanten Plan, um die Flüchtlinge außer Landes und in Sicherheit zu bringen. Dieser Plan ist so unglaublich, dass er sich nur im Kino abspielen kann..." rating="6.6999998092651403" year="2012" tagline="Der Film war gestellt, die Mission eine Meisterleistung" thumb="/library/metadata/3140/thumb/1413152446" art="/library/metadata/3140/art/1413152446" duration="7775648" originallyAvailableAt="2012-10-12" addedAt="1413152276" updatedAt="1413152446">
		<Media videoResolution="1080" id="2912" duration="7775648" bitrate="9608" width="1920" height="800" aspectRatio="2.35" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="1">
			<Part id="2912" key="/library/parts/2912/file.mp4" duration="7775648" file="/mnt/media/Ina Filme/Argo.mp4" size="9338784050" container="mp4" has64bitOffsets="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Drama" />
		<Writer tag="Chris Terrio" />
		<Director tag="Ben Affleck" />
		<Country tag="USA" />
		<Role tag="Ben Affleck" />
		<Role tag=" Bryan Cranston" />
		<Role tag=" John Goodman" />
	</Video>
	<Video ratingKey="3144" key="/library/metadata/3144" studio="Constantin Film Production" type="movie" title="Carnage" originalTitle="Carnage" contentRating="R" summary="In Brooklyn Bridge Park, eleven year old Zachary Cowan strikes his eleven year old classmate Ethan Longstreet across the face with a stick after an argument. Among the more serious of Ethan&apos;s injuries is a permanently missing tooth and the possibility of a second tooth also being lost. Their respective parents learn of the altercation through Ethan&apos;s parents questioning him about his injuries. The Longstreet parents invite the Cowan parents to their Brooklyn apartment to deal with the incident in a civilized manner. They are: Penelope Longstreet, whose idea it was to invite the Cowans, she whose priorities in life include human rights and justice; Michael Longstreet, who tries to be as accommodating as possible to retain civility in any situation; Nancy Cowan, a nervous and emotionally stressed woman; and Alan Cowan, who is married more to his work as evidenced by the attachment he has to his cell phone and taking work calls at the most inopportune times." rating="7" year="2011" thumb="/library/metadata/3144/thumb/1413152562" art="/library/metadata/3144/art/1413152562" duration="4771029" originallyAvailableAt="2011-12-16" addedAt="1413152276" updatedAt="1413152562">
		<Media videoResolution="1080" id="2916" duration="4771029" bitrate="5276" width="1920" height="816" aspectRatio="2.35" audioChannels="2" audioCodec="aac" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="1">
			<Part id="2916" key="/library/parts/2916/file.mp4" duration="4771029" file="/mnt/media/Ina Filme/Der Gott des Gemetzels.mp4" size="3146399473" container="mp4" has64bitOffsets="1" hasChapterTextStream="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Comedy" />
		<Writer tag="Yasmina Reza" />
		<Writer tag="Roman Polanski" />
		<Director tag="Roman Polanski" />
		<Country tag="USA" />
		<Role tag="Kate Winslet" />
		<Role tag=" Jodie Foster" />
		<Role tag=" Christoph Waltz" />
	</Video>
	<Video ratingKey="3141" key="/library/metadata/3141" type="movie" title="Cest La Vie" summary="" thumb="/library/metadata/3141/thumb/1423495906" art="/library/metadata/3141/art/1423495906" duration="6507040" addedAt="1413152276" updatedAt="1423495906">
		<Media videoResolution="sd" id="2913" duration="6507040" bitrate="1335" width="496" height="208" aspectRatio="2.35" audioChannels="2" audioCodec="aac" videoCodec="h264" container="mp4" videoFrameRate="PAL" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="2913" key="/library/parts/2913/file.mp4" duration="6507040" file="/mnt/media/Ina Filme/Cest la vie.mp4" size="1086259375" container="mp4" has64bitOffsets="0" hasChapterTextStream="1" optimizedForStreaming="1" />
		</Media>
	</Video>
	<Video ratingKey="3142" key="/library/metadata/3142" studio="Cloud Atlas Productions" type="movie" title="Cloud Atlas" contentRating="R" summary="A set of six nested stories spanning time between the 19th century and a distant post-apocalyptic future., Cloud Atlas explores how the actions and consequences of individual lives impact one another throughout the past, the present and the future. Action, mystery and romance weave through the story as one soul is shaped from a killer into a hero and a single act of kindness ripples across centuries to inspire a revolution in the distant future.  Based on the award winning novel by David Mitchell. Directed by Tom Tykwer and the Wachowskis." rating="6.4000000953674299" year="2012" tagline="Alles ist verbunden" thumb="/library/metadata/3142/thumb/1413152509" art="/library/metadata/3142/art/1413152509" duration="10317088" originallyAvailableAt="2012-10-24" addedAt="1413152276" updatedAt="1413152509">
		<Media videoResolution="1080" id="2914" duration="10317088" bitrate="11501" width="1920" height="800" aspectRatio="2.35" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="1">
			<Part id="2914" key="/library/parts/2914/file.mp4" duration="10317088" file="/mnt/media/Ina Filme/Cloud Atlas.mp4" size="14831873965" container="mp4" has64bitOffsets="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Drama" />
		<Writer tag="Lana Wachowski" />
		<Writer tag="Tom Tykwer" />
		<Director tag="Tom Tykwer" />
		<Director tag=" Andy Wachowski" />
		<Director tag="Lana Wachowski" />
		<Country tag="Germany" />
		<Country tag="Hong Kong" />
		<Role tag="Tom Hanks" />
		<Role tag=" Halle Berry" />
		<Role tag=" Hugo Weaving" />
	</Video>
	<Video ratingKey="3147" key="/library/metadata/3147" studio="DEFA" type="movie" title="Die Architekten" originalTitle="Die Architekten" summary="No overview found." year="1990" thumb="/library/metadata/3147/thumb/1413152583" art="/library/metadata/3147/art/1413152583" duration="6150878" originallyAvailableAt="1990-05-27" addedAt="1413152277" updatedAt="1413152583">
		<Media videoResolution="480" id="2919" duration="6150878" bitrate="1092" width="704" height="480" aspectRatio="1.78" audioChannels="2" audioCodec="aac" videoCodec="h264" container="mp4" videoFrameRate="NTSC" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="2919" key="/library/parts/2919/file.mp4" duration="6150878" file="/mnt/media/Ina Filme/Die Architekten.mp4" size="839609438" container="mp4" has64bitOffsets="0" hasChapterTextStream="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Drama" />
		<Genre tag="Foreign" />
		<Writer tag="Thomas Knauf" />
		<Writer tag="Peter Kahane" />
		<Director tag="Peter Kahane" />
		<Country tag="Germany" />
		<Role tag="Kurt Naumann" />
		<Role tag="Rita Feldmeier" />
		<Role tag="Uta Eisold" />
	</Video>
	<Video ratingKey="3148" key="/library/metadata/3148" studio="Bleiberg Entertainment" type="movie" title="Die Band von Nebenan" originalTitle="Bikur Ha-Tizmoret" summary="Once-not long ago-a small Egyptian police band arrived in Israel. Not many remember this... It wasn&apos;t that important. A band comprised of members of the Egyptian police force head to Israel to play at the inaugural ceremony of an Arab arts center, only to find themselves lost in the wrong town." year="2007" thumb="/library/metadata/3148/thumb/1413152589" art="/library/metadata/3148/art/1413152589" duration="5001000" originallyAvailableAt="2007-04-19" addedAt="1413152277" updatedAt="1413152589">
		<Media videoResolution="480" id="2920" duration="5001000" bitrate="1090" width="720" height="400" aspectRatio="1.78" audioChannels="2" audioCodec="aac" videoCodec="h264" container="mp4" videoFrameRate="PAL" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="2920" key="/library/parts/2920/file.mp4" duration="5001000" file="/mnt/media/Ina Filme/Die Band von Nebenan.mp4" size="681618122" container="mp4" has64bitOffsets="0" hasChapterTextStream="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Komödie" />
		<Genre tag="Drama" />
		<Writer tag="Eran Kolirin" />
		<Director tag="Eran Kolirin" />
		<Country tag="France" />
		<Country tag="Israel" />
		<Role tag="Sasson Gabai" />
		<Role tag="Ronit Elkabetz" />
		<Role tag="Khalifa Natour" />
	</Video>
	<Video ratingKey="3150" key="/library/metadata/3150" studio="Canal+" type="movie" title="Die fabelhafte Welt der Amélie" originalTitle="Le fabuleux destin d&apos;Amélie Poulain" contentRating="FSK 0" summary="Im Herzen von Paris arbeitet die schüchterne Amelie als Kellnerin in einem kleinen Straßencafe. Eine Wendung nimmt das vergleichsweise ereignisarme, von kuriosen Alltagsbeobachtungen gewürzte Leben der jungen Frau, als sie eine Schachtel mit Kindheitserinnerungen eines Fremden entdeckt und dem ursprünglichen Besitzer damit große Freude bereitet. Fortan macht es sich Amelie zur Lebensaufgabe, helfend in das Schicksal ihrer Mitmenschen einzugreifen. Nur als es um das eigene Liebesglück geht, scheint ihr Talent zu versagen." rating="7.4000000953674299" year="2001" thumb="/library/metadata/3150/thumb/1413152601" art="/library/metadata/3150/art/1413152601" duration="7294000" originallyAvailableAt="2001-11-02" addedAt="1413152279" updatedAt="1413152601">
		<Media videoResolution="1080" id="2922" duration="7294000" bitrate="6615" width="1920" height="816" aspectRatio="2.35" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="1">
			<Part id="2922" key="/library/parts/2922/file.mp4" duration="7294000" file="/mnt/media/Ina Filme/Die fabelhafte Welt der Amélie.mp4" size="6031513888" container="mp4" has64bitOffsets="1" hasChapterTextStream="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Drama" />
		<Director tag="Jean-Pierre Jeunet" />
		<Country tag="Germany" />
		<Country tag="France" />
		<Role tag="Audrey Tautou" />
		<Role tag=" Rufus" />
		<Role tag=" Jamel Debbouze" />
	</Video>
	<Video ratingKey="3149" key="/library/metadata/3149" studio="Constantin Film Produktion" type="movie" title="Die Welle" contentRating="FSK 12" summary="Der ambitionierte Lehrer Rainer Wenger ist ein geistiges Kind der 68er. Natürlich sieht er es als seine Pflicht an, den Schülern in der politischen Projektwoche die Anarchie zu erklären. Aber der ehemalige Hausbesetzer bekommt das Thema „Autokratie“ zugewiesen. Doch die erste Stunde gestaltet sich sehr schwierig. Die Schüler sind sich sicher dass eine Autokratie oder ihre Spielart, die Diktatur, keine Chance mehr in Deutschland hätte. Zu aufgeklärt sei man heute. Wenger ist entsetzt über die Sorglosigkeit seiner Schüler in dieser Frage und beginnt ein Experiment ..." rating="7.6999998092651403" year="2008" tagline="Inspiriert von einer wahren Geschichte." thumb="/library/metadata/3149/thumb/1413152596" art="/library/metadata/3149/art/1413152596" duration="6144800" originallyAvailableAt="2008-01-18" addedAt="1413152279" updatedAt="1413152596">
		<Media videoResolution="480" id="2921" duration="6144800" bitrate="1091" width="720" height="304" aspectRatio="2.35" audioChannels="2" audioCodec="aac" videoCodec="h264" container="mp4" videoFrameRate="PAL" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="2921" key="/library/parts/2921/file.mp4" duration="6144800" file="/mnt/media/Ina Filme/Die Welle.mp4" size="837721987" container="mp4" has64bitOffsets="0" hasChapterTextStream="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Sci-Fi &amp; Fantasy" />
		<Country tag="Germany" />
	</Video>
	<Video ratingKey="3181" key="/library/metadata/3181" studio="Distant Horizons" type="movie" title="The Dish" titleSort="Dish" contentRating="PG-13" summary="The Dish is a 2000 Australian film that tells the story of how the Parkes Observatory was used to relay the live television of man&apos;s first steps on the moon, during the Apollo 11 mission in 1969. It was the top grossing film in Australia in 2000." year="2000" thumb="/library/metadata/3181/thumb/1423495909" art="/library/metadata/3181/art/1423495909" duration="5810040" originallyAvailableAt="2000-09-15" addedAt="1413152284" updatedAt="1423495909">
		<Media videoResolution="480" id="2953" duration="5810040" bitrate="1237" width="704" height="384" aspectRatio="1.85" audioChannels="2" audioCodec="aac" videoCodec="h264" container="mp4" videoFrameRate="PAL" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="2953" key="/library/parts/2953/file.mp4" duration="5810040" file="/mnt/media/Ina Filme/The Dish.mp4" size="898479491" container="mp4" has64bitOffsets="0" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Comedy" />
		<Director tag="Rob Sitch" />
		<Role tag="Sam Neill" />
		<Role tag="Billy Mitchell" />
		<Role tag="Roz Hammond" />
	</Video>
	<Video ratingKey="3151" key="/library/metadata/3151" studio="The Weinstein Company" type="movie" title="Django Unchained" contentRating="R" summary="A slave-turned-bounty hunter sets out to rescue his wife from the brutal Calvin Candie, a Mississippi plantation owner." rating="7.3000001907348597" year="2012" tagline="Leben, Freiheit und die Verfolgung von Rache" thumb="/library/metadata/3151/thumb/1413152625" art="/library/metadata/3151/art/1413152625" duration="9922912" originallyAvailableAt="2012-12-25" addedAt="1413152279" updatedAt="1413152625">
		<Media videoResolution="1080" id="2923" duration="9922912" bitrate="6136" width="1920" height="800" aspectRatio="2.35" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="1">
			<Part id="2923" key="/library/parts/2923/file.mp4" duration="9922912" file="/mnt/media/Ina Filme/Django Unchained.mp4" size="7611323637" container="mp4" has64bitOffsets="1" hasChapterTextStream="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Drama" />
		<Writer tag="Quentin Tarantino" />
		<Director tag="Quentin Tarantino" />
		<Country tag="USA" />
		<Role tag="Jamie Foxx" />
		<Role tag=" Christoph Waltz" />
		<Role tag=" Leonardo DiCaprio" />
	</Video>
	<Video ratingKey="3152" key="/library/metadata/3152" type="movie" title="Easy Virtue" contentRating="PG-13" summary="A young Englishman marries a glamorous American. When he brings her home to meet the parents, she arrives like a blast from the future - blowing their entrenched British stuffiness out the window." year="2008" thumb="/library/metadata/3152/thumb/1423495910" art="/library/metadata/3152/art/1423495910" duration="5560576" originallyAvailableAt="2008-01-01" addedAt="1413152279" updatedAt="1423495910">
		<Media videoResolution="480" id="2924" duration="5560576" bitrate="1614" width="704" height="304" aspectRatio="2.35" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="PAL" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="2924" key="/library/parts/2924/file.mp4" duration="5560576" file="/mnt/media/Ina Filme/Easy Virtue (2008).mp4" size="1121969133" container="mp4" has64bitOffsets="0" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Comedy" />
		<Genre tag="Drama" />
		<Director tag="Stephen Elliott" />
		<Role tag="Jessica Biel" />
		<Role tag="Ben Barnes" />
		<Role tag="Kristin Scott Thomas" />
	</Video>
	<Video ratingKey="3143" key="/library/metadata/3143" studio="Twentieth Century Fox Film Corporation" type="movie" title="Das erstaunliche Leben des Walter Mitty" titleSort="erstaunliche Leben des Walter Mitty" originalTitle="The Secret Life of Walter Mitty" contentRating="NR" summary="Walter Mitty führt ein zurückgezogenes Leben. Seit Jahren arbeitet er schon im Fotoarchiv des renommierten &quot;Life!&quot;-Magazins. Dem grauen Alltag versucht Walter durch Tagträume zu entfliehen, in denen er heldenhafte Abenteuer erlebt und die ganz große Liebe findet. Doch dann begegnet er seiner neuen Kollegin Cheryl und plötzlich ist die große Liebe Realität geworden. Doch Walter traut sich nicht, Cheryl anzusprechen. Als bekanntgegeben wird, dass das Magazin nur noch online erscheinen wird, läuft Walter Gefahr, auch noch seinen Job zu verlieren. Die letzte Print-Ausgabe des Magazins soll das Bild des bekannten &quot;Life!&quot;-Fotografen Sean O‘Connell zieren, doch ausgerechnet dieses Foto ist verschwunden. Walter nimmt seinen ganzen Mut zusammen und begibt sich für seinen Job und seine große Liebe auf ein Abenteuer, von dem er sonst immer nur geträumt hat." rating="7.1999998092651403" year="2013" tagline="Hör auf zu Träumen und beginne zu Leben" thumb="/library/metadata/3143/thumb/1413152544" art="/library/metadata/3143/art/1413152544" duration="6874911" originallyAvailableAt="2013-12-31" addedAt="1413152276" updatedAt="1413152544">
		<Media videoResolution="1080" id="2915" duration="6874911" bitrate="8376" width="1920" height="800" aspectRatio="2.35" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="1">
			<Part id="2915" key="/library/parts/2915/file.mp4" duration="6874911" file="/mnt/media/Ina Filme/Das erstaunliche Leben des Walter Mitty (2013).mp4" size="7198249314" container="mp4" has64bitOffsets="1" hasChapterTextStream="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Drama" />
		<Writer tag="Steve Conrad" />
		<Director tag="Ben Stiller" />
		<Country tag="USA" />
		<Role tag="Ben Stiller" />
		<Role tag="Kristen Wiig" />
		<Role tag="Patton Oswalt" />
	</Video>
	<Video ratingKey="3153" key="/library/metadata/3153" studio="Constantin Film Produktion" type="movie" title="Fack ju Göhte" contentRating="NR" summary="Kleinganove Zeki Müller landet bei der Suche nach seiner Diebesbeute als Aushilfslehrer an einer Schule. Den Lehrerberuf führt er laut eigener Aussage nur nebenberuflich aus und das merkt man schnell: Er bedient sich unkonventioneller Methoden, wie beispielsweise seiner an Schülern erprobten Paintball-Pädagogik, und hat auch sonst keinen blassen Schimmer von den Unterrichtsthemen. Als Neuer an der Schule bekommt er gleich die Problemklasse aufs Auge gedrückt. Mit seinen rabiaten Mitteln und ungewöhnlichen Lehrmethoden mischt er die Chaosklasse und auch die Lehrerschaft ordentlich auf. Und schließlich ist da noch die Referendarin Lisi Schnabelstedt, die ihm nicht nur dank ihrer pädagogischen Ratschläge etwas bedeutet... Zeki muss sich entscheiden, ob er die Chance auf ein anständiges Leben und die große Liebe ergreifen will." rating="7.6999998092651403" viewCount="1" lastViewedAt="1423344091" year="2013" thumb="/library/metadata/3153/thumb/1423338967" art="/library/metadata/3153/art/1423338967" duration="7028958" originallyAvailableAt="2013-11-07" addedAt="1413152279" updatedAt="1423338967">
		<Media videoResolution="480" id="2925" duration="7028958" bitrate="1178" width="720" height="304" aspectRatio="2.35" audioChannels="2" audioCodec="aac" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="0" has64bitOffsets="1">
			<Part id="2925" key="/library/parts/2925/file.mp4" duration="7028958" file="/mnt/media/Ina Filme/Fack ju Goehte.mp4" size="1035336517" container="mp4" has64bitOffsets="1" optimizedForStreaming="0" />
		</Media>
		<Genre tag="Komödie" />
		<Writer tag="Bora Dağtekin" />
		<Director tag="Bora Dağtekin" />
		<Country tag="Germany" />
		<Role tag="Bora Dağtekin" />
	</Video>
	<Video ratingKey="3154" key="/library/metadata/3154" studio="Universal Pictures" type="movie" title="Fast verheiratet" originalTitle="The Five-Year Engagement" contentRating="R" summary="Verliebt, verlobt, verplant: Tom (Jason Segel) und Victoria (Emily Blunt) wollen heiraten und so schön und vielversprechend die Verlobungsfeier auch ist, so anders wollen es die Lebensumstände. Victoria bekommt ein zweijähriges Jobangebot in einer anderen Stadt. Doch aus den zwei Jahren werden vier und so zieht sich der Gang zum Traualtar nach der Verlobung immer mehr in die Länge. Fünf Jahre um genau zu sein. In dieser Zeit sieht sich das Paar den Erwartungshaltungen der Familien, der Religionen, der Mortalität von Großeltern und nicht zuletzt den eigenen Selbstzweifeln ausgesetzt. Kurz, Tom und Victoria durchleben die Höhen und Tiefen einer Beziehung. Dabei kommen beide am Ende zu der Erkenntnis, dass die Reise zum verheißungsvollen Glück oft anders verläuft als geplant und es doch immer auch auf jene glücklichen Momente am Rande des Weges ankommt." rating="5.6999998092651403" year="2012" tagline="Verliebt. Verlobt. Verschoben." thumb="/library/metadata/3154/thumb/1413152672" art="/library/metadata/3154/art/1413152672" duration="7460480" originallyAvailableAt="2012-04-27" addedAt="1413152279" updatedAt="1413152672">
		<Media videoResolution="1080" id="2926" duration="7460480" bitrate="9139" width="1920" height="1040" aspectRatio="1.85" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="1">
			<Part id="2926" key="/library/parts/2926/file.mp4" duration="7460480" file="/mnt/media/Ina Filme/Fast verheiratet.mp4" size="8522697879" container="mp4" has64bitOffsets="1" hasChapterTextStream="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Name=Komödie" />
		<Genre tag="Name=Lovestory" />
		<Writer tag="Jason Segel" />
		<Writer tag="Nicholas Stoller" />
		<Director tag="Nicholas Stoller" />
		<Country tag="USA" />
		<Role tag="Emily Blunt" />
		<Role tag=" Alison Brie" />
		<Role tag=" Jason Segel" />
	</Video>
	<Video ratingKey="3146" key="/library/metadata/3146" studio="The Weinstein Company" type="movie" title="Der ganz normale Wahnsinn - Working Mum" titleSort="ganz normale Wahnsinn - Working Mum" originalTitle="I Don&apos;t Know How She Does It" contentRating="PG-13" summary="Kate Reddy hat einen stressigen Job, wunderbare Kinder und einen liebevollen Mann. Ihr tägliches Leben ist ein Balance-Akt zwischen Familie und ihrem Beruf in einem Bostoner Finanzunternehmen. Als ihr ein neuer Kunde zugeteilt wird, erfordert dies eine Reisetätigkeit, so dass sie in ihrem Privatleben weitere Abstriche machen muss. Zu allem Überfluss aber erhält ihr Ehemann Richard auch ein verlockendes Jobangebot. Für das Paar wird die Situation zur Zerreißprobe und zusätzlich verkompliziert, da Kate von ihrem charmanten Kollegen Jack Abelhammer bezirzt wird." rating="5.5999999046325701" year="2011" tagline="Wenn es einfach wäre, könnten Männer es ja auch..." thumb="/library/metadata/3146/thumb/1413152569" art="/library/metadata/3146/art/1413152569" duration="5372608" originallyAvailableAt="2011-09-16" addedAt="1413152277" updatedAt="1413152569">
		<Media videoResolution="480" id="2918" duration="5372608" bitrate="2019" width="720" height="416" aspectRatio="1.78" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="2918" key="/library/parts/2918/file.mp4" duration="5372608" file="/mnt/media/Ina Filme/Der ganz normale Wahnsinn - Working Mum.mp4" size="1356003199" container="mp4" has64bitOffsets="0" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Comedy" />
		<Writer tag="Aline Brosh McKenna" />
		<Director tag="Douglas McGrath" />
		<Country tag="USA" />
		<Role tag="Christina Hendricks" />
		<Role tag=" Sarah Jessica Parker" />
		<Role tag=" Pierce Brosnan" />
	</Video>
	<Video ratingKey="3182" key="/library/metadata/3182" studio="Medienboard Berlin-Brandenburg GmbH" type="movie" title="The Ghost Writer" titleSort="Ghost Writer" originalTitle="The Ghost Writer" contentRating="PG-13" summary="A ghostwriter hired to complete the memoirs of a former British prime minister uncovers secrets that put his own life in jeopardy." rating="6.4000000953674299" year="2010" thumb="/library/metadata/3182/thumb/1413153094" art="/library/metadata/3182/art/1413153094" duration="7677984" originallyAvailableAt="2010-02-12" addedAt="1413152284" updatedAt="1413153094">
		<Media videoResolution="480" id="2954" duration="7677984" bitrate="963" width="720" height="304" aspectRatio="2.35" audioChannels="2" audioCodec="aac" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="2954" key="/library/parts/2954/file.mp4" duration="7677984" file="/mnt/media/Ina Filme/The Ghost Writer.mp4" size="924549637" container="mp4" has64bitOffsets="0" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Drama" />
		<Writer tag="Roman Polanski" />
		<Director tag="Roman Polanski" />
		<Country tag="Germany" />
		<Country tag="United Kingdom" />
		<Role tag="Ewan McGregor" />
		<Role tag="Pierce Brosnan" />
		<Role tag="Jon Bernthal" />
	</Video>
	<Video ratingKey="3183" key="/library/metadata/3183" studio="20th Century Fox" type="movie" title="The Heat" titleSort="Heat" originalTitle="The Heat" contentRating="NR" summary="Uptight and straight-laced, FBI Special Agent Sarah Ashburn is a methodical investigator with a reputation for excellence--and hyper-arrogance. Shannon Mullins, one of Boston P.D.&apos;s &quot;finest,&quot; is foul-mouthed and has a very short fuse, and uses her gut instinct and street smarts to catch the most elusive criminals. Neither has ever had a partner, or a friend for that matter. When these two wildly incompatible law officers join forces to bring down a ruthless drug lord, they become the last thing anyone expected: Buddies." rating="6.6999998092651403" year="2013" tagline="Guter Bulle. Irrer Bulle." thumb="/library/metadata/3183/thumb/1413153117" art="/library/metadata/3183/art/1413153117" duration="7220096" originallyAvailableAt="2013-07-04" addedAt="1413152284" updatedAt="1413153117">
		<Media videoResolution="1080" id="2955" duration="7220096" bitrate="10449" width="1920" height="800" aspectRatio="2.35" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="0" has64bitOffsets="1">
			<Part id="2955" key="/library/parts/2955/file.mp4" duration="7220096" file="/mnt/media/Ina Filme/The Heat (2013).mp4" size="9430391776" container="mp4" has64bitOffsets="1" hasChapterTextStream="1" optimizedForStreaming="0" />
		</Media>
		<Genre tag="Action &amp; Adventure" />
		<Writer tag="Katie Dippold" />
		<Director tag="Paul Feig" />
		<Country tag="USA" />
		<Role tag="Sandra Bullock" />
		<Role tag="Melissa McCarthy" />
		<Role tag="Taran Killam" />
	</Video>
	<Video ratingKey="3155" key="/library/metadata/3155" type="movie" title="Here Comes the Boom" contentRating="PG" summary="A high school biology teacher moonlights as a mixed-martial arts fighter in an effort to raise money to save the school&apos;s music program." year="2012" thumb="/library/metadata/3155/thumb/1423495908" art="/library/metadata/3155/art/1423495908" duration="6295296" originallyAvailableAt="2012-10-12" addedAt="1413152279" updatedAt="1423495908">
		<Media videoResolution="1080" id="2927" duration="6295296" bitrate="8833" width="1920" height="1040" aspectRatio="1.85" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="1">
			<Part id="2927" key="/library/parts/2927/file.mp4" duration="6295296" file="/mnt/media/Ina Filme/Here Comes the Boom.mp4" size="6951053624" container="mp4" has64bitOffsets="1" hasChapterTextStream="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Action &amp; Adventure" />
		<Director tag="Frank Coraci" />
		<Role tag="Salma Hayek" />
		<Role tag=" Kevin James" />
		<Role tag=" Henry Winkler" />
	</Video>
	<Video ratingKey="3145" key="/library/metadata/3145" studio="Road Movies Filmproduktion GmbH" type="movie" title="Der Himmel über Berlin" titleSort="Himmel über Berlin" contentRating="PG-13" summary="Wings of Desire is Wim Wender’s artistically beautiful film about the lonely and immortal life of angles during a post-war Berlin. It’s a poetic journey from the perspective of the angles of which one falls in love with a living woman and wants to become " rating="7.5" year="1987" thumb="/library/metadata/3145/thumb/1413152565" art="/library/metadata/3145/art/1413152565" duration="7337000" originallyAvailableAt="1987-09-23" addedAt="1413152277" updatedAt="1413152565">
		<Media videoResolution="sd" id="2917" duration="7337000" bitrate="1060" width="640" height="352" aspectRatio="1.85" audioChannels="2" audioCodec="aac" videoCodec="h264" container="mp4" videoFrameRate="PAL" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="2917" key="/library/parts/2917/file.mp4" duration="7337000" file="/mnt/media/Ina Filme/Der Himmel über Berlin.mp4" size="971963797" container="mp4" has64bitOffsets="0" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Drama" />
		<Genre tag="Fantasy" />
		<Writer tag="Peter Handke" />
		<Writer tag="Richard Reitinger" />
		<Director tag="Wim Wenders" />
		<Country tag="Germany" />
		<Country tag="France" />
		<Role tag="Bruno Ganz" />
		<Role tag="Otto Sander" />
		<Role tag="Solveig Dommartin" />
	</Video>
	<Video ratingKey="3156" key="/library/metadata/3156" type="movie" title="Identity Thief" contentRating="R" summary="When a mild-mannered businessman learns his identity has been stolen, he hits the road in an attempt to foil the thief -- a trip that puts him in the path of a deceptively harmless-looking woman." year="2013" thumb="/library/metadata/3156/thumb/1423495910" art="/library/metadata/3156/art/1423495910" duration="6687712" originallyAvailableAt="2013-02-07" addedAt="1413152280" updatedAt="1423495910">
		<Media videoResolution="1080" id="2928" duration="6687712" bitrate="6558" width="1920" height="816" aspectRatio="2.35" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="1">
			<Part id="2928" key="/library/parts/2928/file.mp4" duration="6687712" file="/mnt/media/Ina Filme/Identity Thief.mp4" size="5482462921" container="mp4" has64bitOffsets="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Comedy" />
		<Director tag="Seth Gordon" />
		<Role tag="Jason Bateman" />
		<Role tag=" Jon Favreau" />
		<Role tag=" Maggie Elizabeth Jones" />
	</Video>
	<Video ratingKey="3184" key="/library/metadata/3184" studio="Cross Creek Pictures" type="movie" title="The Ides of March" titleSort="Ides of March" originalTitle="The Ides of March" contentRating="R" summary="An idealistic staffer for a newbie presidential candidate gets a crash course on dirty politics during his stint on the campaign trail. Based on the play by Beau Willimon." rating="6.1999998092651403" year="2011" thumb="/library/metadata/3184/thumb/1413153136" art="/library/metadata/3184/art/1413153136" duration="6057634" originallyAvailableAt="2011-10-07" addedAt="1413152284" updatedAt="1413153136">
		<Media videoResolution="720" id="2956" duration="6057634" bitrate="5699" width="1280" height="528" aspectRatio="2.35" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="1">
			<Part id="2956" key="/library/parts/2956/file.mp4" duration="6057634" file="/mnt/media/Ina Filme/The Ides of March (2011).mp4" size="4315368745" container="mp4" has64bitOffsets="1" hasChapterTextStream="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Drama" />
		<Writer tag="Beau Willimon" />
		<Writer tag="George Clooney" />
		<Director tag="George Clooney" />
		<Country tag="USA" />
		<Role tag="George Clooney" />
		<Role tag=" Ryan Gosling" />
		<Role tag=" Evan Rachel Wood" />
	</Video>
	<Video ratingKey="3157" key="/library/metadata/3157" studio="Imagine Entertainment" type="movie" title="J. Edgar" contentRating="R" summary="As the face of law enforcement in America for almost 50 years, J. Edgar Hoover was feared and admired, reviled and revered. But behind closed doors, he held secrets that would have destroyed his image, his career and his life" rating="5.6999998092651403" year="2011" tagline="Der mächtigste Mann der Welt." thumb="/library/metadata/3157/thumb/1413152732" art="/library/metadata/3157/art/1413152732" duration="8214240" originallyAvailableAt="2011-11-09" addedAt="1413152280" updatedAt="1413152732">
		<Media videoResolution="1080" id="2929" duration="8214240" bitrate="5057" width="1920" height="800" aspectRatio="2.35" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="1">
			<Part id="2929" key="/library/parts/2929/file.mp4" duration="8214240" file="/mnt/media/Ina Filme/J. Edgar.mp4" size="5192077912" container="mp4" has64bitOffsets="1" hasChapterTextStream="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Drama" />
		<Writer tag="Dustin Lance Black" />
		<Director tag="Clint Eastwood" />
		<Country tag="USA" />
		<Role tag="Leonardo DiCaprio" />
		<Role tag=" Geoff Pierson" />
		<Role tag=" Naomi Watts" />
	</Video>
	<Video ratingKey="3158" key="/library/metadata/3158" studio="Overture Films" type="movie" title="Jack Goes Boating" originalTitle="Jack Goes Boating" contentRating="R" summary="A limo driver&apos;s blind date sparks a tale of love, betrayal, friendship, and grace centered around two working-class New York City couples." rating="6.6999998092651403" year="2010" thumb="/library/metadata/3158/thumb/1413152743" art="/library/metadata/3158/art/1413152743" duration="5225000" originallyAvailableAt="2010-09-23" addedAt="1413152280" updatedAt="1413152743">
		<Media videoResolution="576" id="2930" duration="5225000" bitrate="1833" width="720" height="554" aspectRatio="1.85" audioChannels="2" audioCodec="aac" videoCodec="h264" container="mp4" videoFrameRate="PAL" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="2930" key="/library/parts/2930/file.mp4" duration="5225000" file="/mnt/media/Ina Filme/Jack Goes Boating.mp4" size="1197249150" container="mp4" has64bitOffsets="0" hasChapterTextStream="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Comedy" />
		<Writer tag="Robert Glaudini" />
		<Director tag="Philip Seymour Hoffman" />
		<Country tag="USA" />
		<Role tag="Philip Seymour Hoffman" />
		<Role tag="Lola Glaudini" />
		<Role tag="Amy Ryan" />
	</Video>
	<Video ratingKey="3159" key="/library/metadata/3159" studio="Paramount Pictures" type="movie" title="Jack Reacher" contentRating="PG-13" summary="In an innocent heartland city, five are shot dead by an expert sniper. The police quickly identify and arrest the culprit, and build a slam-dunk case. But the accused man claims he&apos;s innocent and says &quot;Get Jack Reacher.&quot; Reacher himself sees the news report and turns up in the city. The defense is immensely relieved, but Reacher has come to bury the guy. Shocked at the accused&apos;s request, Reacher sets out to confirm for himself the absolute certainty of the man&apos;s guilt, but comes up with more than he bargained for." rating="6" year="2012" tagline="Das Gesetz hat Grenzen - Er kennt keine." thumb="/library/metadata/3159/thumb/1413152763" art="/library/metadata/3159/art/1413152763" duration="7824384" originallyAvailableAt="2012-12-21" addedAt="1413152280" updatedAt="1413152763">
		<Media videoResolution="1080" id="2931" duration="7824384" bitrate="8974" width="1920" height="816" aspectRatio="2.35" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="1">
			<Part id="2931" key="/library/parts/2931/file.mp4" duration="7824384" file="/mnt/media/Ina Filme/Jack Reacher.mp4" size="8777173197" container="mp4" has64bitOffsets="1" hasChapterTextStream="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Drama" />
		<Writer tag="Christopher McQuarrie" />
		<Director tag="Christopher McQuarrie" />
		<Country tag="USA" />
		<Role tag="Tom Cruise" />
		<Role tag=" Rosamund Pike" />
		<Role tag=" Robert Duvall" />
	</Video>
	<Video ratingKey="24707" key="/library/metadata/24707" type="movie" title="The Judge" titleSort="Judge" contentRating="NR" summary="A successful lawyer returns to his hometown for his mother&apos;s funeral only to discover that his estranged father, the town&apos;s judge, is suspected of murder." year="2014" thumb="/library/metadata/24707/thumb/1423495926" art="/library/metadata/24707/art/1423495926" duration="8492651" originallyAvailableAt="2014-10-15" addedAt="1422645934" updatedAt="1423495926">
		<Media videoResolution="1080" id="22087" duration="8492651" bitrate="2081" width="1920" height="800" aspectRatio="2.35" audioChannels="2" audioCodec="aac" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="22116" key="/library/parts/22116/file.mp4" duration="8492651" file="/mnt/media/Ina Filme/The Judge (2014).mp4" size="2209528309" container="mp4" has64bitOffsets="0" hasChapterTextStream="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Drama" />
		<Director tag="David Dobkin" />
		<Role tag="Robert Downey Jr." />
		<Role tag="Robert Duvall" />
		<Role tag="Vera Farmiga" />
	</Video>
	<Video ratingKey="3161" key="/library/metadata/3161" studio="Franchise Pictures" type="movie" title="Keine halben Sachen" originalTitle="The Whole Nine Yards" contentRating="R" summary="Der Zahnarzt Nicholas Oseransky hat ja eigentlich schon genug unter seiner Ehefrau und seiner Schwiegermutter zu leiden, aber jetzt zieht auch noch ein neuer Nachbar ein, den er schnell als den Killer Jimmy Tudeski identifiziert. Mal sehen, wie er mit dieser Situation fertig wird." rating="6.1999998092651403" year="2000" tagline="Früher ließ er andere ins Gras beißen - Heute mäht er es lieber selbst ... und beides sehr gründlich" thumb="/library/metadata/3161/thumb/1413152794" art="/library/metadata/3161/art/1413152794" duration="5931360" originallyAvailableAt="2000-04-20" addedAt="1413152280" updatedAt="1413152794">
		<Media videoResolution="720" id="2933" duration="5931360" bitrate="7349" width="1280" height="720" aspectRatio="1.78" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="1">
			<Part id="2933" key="/library/parts/2933/file.mp4" duration="5931360" file="/mnt/media/Ina Filme/Keine halben Sachen.mp4" size="5448487178" container="mp4" has64bitOffsets="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Action &amp; Adventure" />
		<Writer tag="Mitchell Kapner" />
		<Director tag="Jonathan Lynn" />
		<Country tag="Canada" />
		<Country tag="USA" />
		<Role tag="Bruce Willis" />
		<Role tag=" Matthew Perry" />
		<Role tag=" Rosanna Arquette" />
	</Video>
	<Video ratingKey="3160" key="/library/metadata/3160" studio="Warner Bros." type="movie" title="Keine halben Sachen 2 - Jetzt erst recht" originalTitle="The Whole Ten Yards" contentRating="PG-13" summary="Frieden ist eingekehrt im Haus von Ex-Mafioso Jimmy &quot;Die Tulpe&quot; Tudeski (Bruce Willis). Seit er mit Jill (Amanda Peet) verheiratet ist, kümmert er sich ausschließlich um den Haushalt, während Jill in der Ausbildung zur perfekten Killerin ist. Doch die Ruhe hält nicht lang: Oz (Matthew Perry), der Jimmys Tarnexistenz abgesichert hatte, steht vor seiner Tür und bittet um Hilfe, da seine Cynthia (Natasha Henstridge) von einer ungarischen Gangsterbande entführt wurde. Und Jimmy wird mit hineingezogen, denn geführt werden die Gegner von Laszlo Gogolak (Kevin Pollak), dem Vater seines Gegners aus dem ersten Teil ..." rating="5.8000001907348597" year="2004" thumb="/library/metadata/3160/thumb/1413152778" art="/library/metadata/3160/art/1413152778" duration="5676512" originallyAvailableAt="2004-04-09" addedAt="1413152280" updatedAt="1413152778">
		<Media videoResolution="720" id="2932" duration="5676512" bitrate="6127" width="1280" height="720" aspectRatio="1.78" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="PAL" optimizedForStreaming="1" has64bitOffsets="1">
			<Part id="2932" key="/library/parts/2932/file.mp4" duration="5676512" file="/mnt/media/Ina Filme/Keine halben Sachen 2 - Jetzt erst recht.mp4" size="4347453121" container="mp4" has64bitOffsets="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Action &amp; Adventure" />
		<Writer tag="George Gallo" />
		<Director tag="Howard Deutch" />
		<Country tag="USA" />
		<Role tag="Bruce Willis" />
		<Role tag=" Matthew Perry" />
		<Role tag=" Amanda Peet" />
	</Video>
	<Video ratingKey="3162" key="/library/metadata/3162" studio="Plan B Entertainment" type="movie" title="Killing Them Softly" contentRating="R" summary="Kleingstadtanove Frankie (Scoot McNairy) und sein Kumpel, der heroinabhängige Russell (Ben Mendelsohn), sind pleite. Um schnell wieder an Geld zu kommen, sind sie für den heißen Tipp des Geschäftsmanns Johnny Amato (Vincent Curatola) dankbar: In New Orleans soll ein Pokerspiel in Mobsterkreisen stattfinden, bei dem besonders hohe Geldsummen zum Einsatz kommen. Das lassen sich Frankie und Russell nicht zweimal sagen und es gelingt ihnen tatsächlich, bei dem Raub den gesamten Preispool von 30.000 Dollar zu erbeuten. Eine Schmach, die Veranstalter und Mafioso Markie Trattman (Ray Liotta), nicht lange auf sich sitzen lassen kann: er engagiert den berüchtigten Auftragskiller Jackie Cogan (Brad Pitt) und dessen New Yorker Kollegen Mickey (James Gandolfini). Frankie und Russell müssen sich warm anziehen, denn die beiden Auftragskiller haben ihre ganz eigenen Methoden, um die Täter ihrer &quot;gerechten&quot; Strafe zuzuführen." rating="5.5999999046325701" year="2012" thumb="/library/metadata/3162/thumb/1413152815" art="/library/metadata/3162/art/1413152815" duration="5833744" originallyAvailableAt="2012-11-30" addedAt="1413152280" updatedAt="1413152815">
		<Media videoResolution="1080" id="2934" duration="5833744" bitrate="10133" width="1920" height="804" aspectRatio="2.35" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="1">
			<Part id="2934" key="/library/parts/2934/file.mp4" duration="5833744" file="/mnt/media/Ina Filme/Killing Them Softly.mp4" size="7388861087" container="mp4" has64bitOffsets="1" hasChapterTextStream="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Thriller" />
		<Writer tag="Andrew Dominik" />
		<Director tag="Andrew Dominik" />
		<Country tag="USA" />
		<Role tag="Brad Pitt" />
		<Role tag="  Ray Liotta" />
		<Role tag="  James Gandolfini" />
	</Video>
	<Video ratingKey="3163" key="/library/metadata/3163" studio="American Zoetrope" type="movie" title="Lost in Translation" contentRating="R" summary="The widely successful sophomore film by Sofia Coppola. Set in Tokyo under the bustling city life and lights, the two main characters from different generations build a surprising friendship on the common bond that they don’t have anything to do while they are in Tokyo. The film is a slow, dreamy and at times hilarious look at a relationship and the big city they move unknowingly." rating="7" year="2003" thumb="/library/metadata/3163/thumb/1413152832" art="/library/metadata/3163/art/1413152832" duration="5861984" originallyAvailableAt="2003-08-29" addedAt="1413152280" updatedAt="1413152832">
		<Media videoResolution="576" id="2935" duration="5861984" bitrate="2900" width="720" height="544" aspectRatio="1.85" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="PAL" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="2935" key="/library/parts/2935/file.mp4" duration="5861984" file="/mnt/media/Ina Filme/Lost in Translation.mp4" size="2125147511" container="mp4" has64bitOffsets="0" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Comedy" />
		<Writer tag="Sofia Coppola" />
		<Director tag="Sofia Coppola" />
		<Country tag="Japan" />
		<Country tag="USA" />
		<Role tag="Bill Murray" />
		<Role tag="Scarlett Johansson" />
		<Role tag="Anna Faris" />
	</Video>
	<Video ratingKey="3164" key="/library/metadata/3164" type="movie" title="Love Actually" contentRating="R" summary="A British romantic comedy which follows seemingly unrelated people as their lives begin to intertwine while they fall in - and out - of love.  Affections grow and develop as Christmas draws near." year="2003" thumb="/library/metadata/3164/thumb/1423495926" art="/library/metadata/3164/art/1423495926" duration="7756192" originallyAvailableAt="2003-09-07" addedAt="1413152280" updatedAt="1423495926">
		<Media videoResolution="480" id="2936" duration="7756192" bitrate="3058" width="720" height="432" aspectRatio="2.35" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="PAL" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="2936" key="/library/parts/2936/file.mp4" duration="7756192" file="/mnt/media/Ina Filme/Love Actually.mp4" size="2965088765" container="mp4" has64bitOffsets="0" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Comedy" />
		<Director tag="Richard Curtis" />
		<Role tag="Bill Nighy" />
		<Role tag="Gregor Fisher" />
		<Role tag="Rory MacGregor" />
	</Video>
	<Video ratingKey="3165" key="/library/metadata/3165" type="movie" title="Moloko - 11,000 Clicks" contentRating="Unrated" summary="After a year of touring, Moloko had director Dick Carruthers film their final UK show of 2003 at the Brixton Academy on November 22nd. The result brilliantly captures the energy of Moloko&apos;s live performances." year="2004" thumb="/library/metadata/3165/thumb/1413152858" art="/library/metadata/3165/art/1413152858" duration="6679340" originallyAvailableAt="2004-04-26" addedAt="1413152280" updatedAt="1413152858">
		<Media videoResolution="576" id="2937" duration="6679340" bitrate="1467" width="720" height="576" aspectRatio="1.78" audioChannels="2" audioCodec="aac" videoCodec="h264" container="mp4" videoFrameRate="PAL" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="2937" key="/library/parts/2937/file.mp4" duration="6679340" file="/mnt/media/Ina Filme/Moloko - 11,000 Clicks.mp4" size="1224494615" container="mp4" has64bitOffsets="0" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Music" />
		<Director tag="Dick Carruthers" />
		<Role tag="Roisin Murphy" />
		<Role tag="Mark Brydon" />
		<Role tag="David Cooke" />
	</Video>
	<Video ratingKey="3185" key="/library/metadata/3185" type="movie" title="The Monuments Men" titleSort="Monuments Men" contentRating="NR" summary="Based on the true story of the greatest treasure hunt in history, The Monuments Men is an action drama focusing on seven over-the-hill, out-of-shape museum directors, artists, architects, curators, and art historians who went to the front lines of WWII to rescue the world’s artistic masterpieces from Nazi thieves and return them to their rightful owners.  With the art hidden behind enemy lines, how could these guys hope to succeed?  But as the Monuments Men found themselves in a race against time to avoid the destruction of 1000 years of culture, they would risk their lives to protect and defend mankind’s greatest achievements.  From director George Clooney, the film stars George Clooney, Matt Damon, Bill Murray, John Goodman, Jean Dujardin, Bob Balaban, Hugh Bonneville, and Cate Blanchett.  The screenplay is by George Clooney &amp; Grant Heslov, based on the book by Robert M. Edsel with Bret Witter. Produced by Grant Heslov and George Clooney." year="2014" thumb="/library/metadata/3185/thumb/1423495929" art="/library/metadata/3185/art/1423495929" duration="7102106" originallyAvailableAt="2014-01-23" addedAt="1413152284" updatedAt="1423495929">
		<Media videoResolution="1080" id="2957" duration="7102106" bitrate="5991" width="1920" height="800" aspectRatio="2.35" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="1">
			<Part id="2957" key="/library/parts/2957/file.mp4" duration="7102106" file="/mnt/media/Ina Filme/The Monuments Men (2014).mp4" size="5318550668" container="mp4" has64bitOffsets="1" hasChapterTextStream="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Action &amp; Adventure" />
		<Director tag="George Clooney" />
		<Role tag="Matt Damon" />
		<Role tag="Cate Blanchett" />
		<Role tag="George Clooney" />
	</Video>
	<Video ratingKey="3166" key="/library/metadata/3166" studio="Scott Rudin Productions" type="movie" title="Moonrise Kingdom" contentRating="PG-13" summary="Set in the 1960s, a pair of young lovers flee their New England island town, prompting a local search party led by the Sheriff (Willis) and the girl&apos;s parents (Murray, McDormand) to fan out to find them." rating="7.3000001907348597" year="2012" thumb="/library/metadata/3166/thumb/1413152875" art="/library/metadata/3166/art/1413152875" duration="5618720" originallyAvailableAt="2012-05-25" addedAt="1413152280" updatedAt="1413152875">
		<Media videoResolution="1080" id="2938" duration="5618720" bitrate="13091" width="1920" height="1040" aspectRatio="1.85" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="1">
			<Part id="2938" key="/library/parts/2938/file.mp4" duration="5618720" file="/mnt/media/Ina Filme/Moonrise Kingdom.mp4" size="9194607009" container="mp4" has64bitOffsets="1" hasChapterTextStream="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Drama" />
		<Writer tag="Wes Anderson" />
		<Writer tag="Roman Coppola" />
		<Director tag="Wes Anderson" />
		<Country tag="USA" />
		<Role tag="Bruce Willis" />
		<Role tag=" Bill Murray" />
		<Role tag=" Frances McDormand" />
	</Video>
	<Video ratingKey="3167" key="/library/metadata/3167" studio="Lou Yi Inc." type="movie" title="My Blueberry Nights" contentRating="PG-13" summary="Elizabeth (Jones) has just been through a particularly nasty breakup, and now she&apos;s ready to leave her friends and memories behind as she chases her dreams across the country. In order to support herself on her journey, Elizabeth picks up a series of waitress jobs along the way. As Elizabeth crosses paths with a series of lost souls." rating="6.3000001907348597" year="2007" thumb="/library/metadata/3167/thumb/1413152887" art="/library/metadata/3167/art/1413152887" duration="5411424" originallyAvailableAt="2007-05-16" addedAt="1413152281" updatedAt="1413152887">
		<Media videoResolution="sd" id="2939" duration="5411424" bitrate="1623" width="624" height="268" aspectRatio="2.35" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="2939" key="/library/parts/2939/file.mp4" duration="5411424" file="/mnt/media/Ina Filme/My Blueberry Nights.mp4" size="1097998485" container="mp4" has64bitOffsets="0" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Drama" />
		<Writer tag="Wong Kar-Wai" />
		<Writer tag="Lawrence Block" />
		<Director tag="Wong Kar-Wai" />
		<Country tag="China" />
		<Country tag="France" />
		<Role tag="Norah Jones" />
		<Role tag="Jude Law" />
		<Role tag="David Strathairn" />
	</Video>
	<Video ratingKey="3168" key="/library/metadata/3168" studio="StudioCanal" type="movie" title="Nathalie küsst" originalTitle="La délicatesse" contentRating="NR" summary="Für die junge Nathalie hängt der Himmel voller Geigen. Sie ist jung und hübsch, glücklich verheiratet und hat einen tollen Job. Von einem Tag auf dem anderen wirft sie das Schicksal aus der Bahn. Nach dem Unfalltod ihres Mannes kniet sie sich in die Arbeit, macht Karriere und beisst die Zähne zusammen, verbringt ihre Zeit allein. Bis sie aus einem Impuls heraus den nicht gerade attraktiven Quotenschweden in der Firma küsst und sich fast unfreiwillig auf eine emotionale Reise begibt und eine zaghaft eine neue Liebe wagt." rating="7.5999999046325701" year="2012" thumb="/library/metadata/3168/thumb/1413152894" art="/library/metadata/3168/art/1413152894" duration="6567000" originallyAvailableAt="2012-03-16" addedAt="1413152281" updatedAt="1413152894">
		<Media videoResolution="720" id="2940" duration="6567000" bitrate="3737" width="1280" height="696" aspectRatio="1.85" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="2940" key="/library/parts/2940/file.mp4" duration="6567000" file="/mnt/media/Ina Filme/Nathalie küsst.mp4" size="3068221251" container="mp4" has64bitOffsets="0" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Drama" />
		<Writer tag="David Foenkinos" />
		<Director tag="David Foenkinos" />
		<Director tag="Stéphane Foenkinos" />
		<Country tag="France" />
		<Role tag="David Foenkinos" />
	</Video>
	<Video ratingKey="3169" key="/library/metadata/3169" studio="Road Movies Filmproduktion GmbH" type="movie" title="Paris, Texas" contentRating="R" summary="German director Wim Wenders won the Golden Palme at Cannes for his 1984 film Paris, Texas. The film reflects the landscape and people of the United States from the perspective of European cinema." rating="7.8000001907348597" year="1984" thumb="/library/metadata/3169/thumb/1413152907" art="/library/metadata/3169/art/1413152907" duration="8339800" originallyAvailableAt="1984-05-19" addedAt="1413152281" updatedAt="1413152907">
		<Media videoResolution="sd" id="2941" duration="8339800" bitrate="1064" width="640" height="352" aspectRatio="1.85" audioChannels="2" audioCodec="aac" videoCodec="h264" container="mp4" videoFrameRate="PAL" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="2941" key="/library/parts/2941/file.mp4" duration="8339800" file="/mnt/media/Ina Filme/Paris, Texas.mp4" size="1108838968" container="mp4" has64bitOffsets="0" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Drama" />
		<Writer tag="Sam Shepard" />
		<Director tag="Wim Wenders" />
		<Country tag="Germany" />
		<Country tag="France" />
		<Role tag="Harry Dean Stanton" />
		<Role tag="Nastassja Kinski" />
		<Role tag="Dean Stockwell" />
	</Video>
	<Video ratingKey="3170" key="/library/metadata/3170" studio="Muskat Filmed Properties" type="movie" title="Prince Avalanche" contentRating="NR" summary="Two highway road workers spend the summer of 1988 away from their city lives. The isolated landscape becomes a place of misadventure as the men find themselves at odds with each other and the women they left behind." rating="6.5999999046325701" year="2013" thumb="/library/metadata/3170/thumb/1413152937" art="/library/metadata/3170/art/1413152937" duration="5622042" originallyAvailableAt="2013-09-27" addedAt="1413152281" updatedAt="1413152937">
		<Media videoResolution="1080" id="2942" duration="5622042" bitrate="5739" width="1920" height="800" aspectRatio="2.35" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="2942" key="/library/parts/2942/file.mp4" duration="5622042" file="/mnt/media/Ina Filme/Prince Avalanche (2013).mp4" size="4033315723" container="mp4" has64bitOffsets="0" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Comedy" />
		<Director tag="David Gordon Green" />
		<Country tag="USA" />
		<Role tag="Emile Hirsch" />
		<Role tag="Paul Rudd" />
		<Role tag="Lance LeGault" />
	</Video>
	<Video ratingKey="3172" key="/library/metadata/3172" studio="Fox Searchlight Pictures" type="movie" title="Ruby Sparks - Meine fabelhafte Freundin" originalTitle="Ruby Sparks" contentRating="R" summary="Calvin (Paul Dano) ist ein junger aufstrebender Schriftsteller. Allerdings plagt er sich zurzeit mit dem Fluch eines jeden Autoren: der Schreibblockade. Eines Tages jedoch – wie aus dem Nichts – erscheint ihm eine weibliche Gestalt namens Ruby Sparks vor seinem geistigen Auge. Die Figur nimmt immer mehr Konturen an, Calvin erfüllt sie wie im Rausch mit Leben – und Liebe für ihren Schöpfer. Mit ungeahnten, wahnwitzigen Folgen. Denn plötzlich steht Ruby Sparks (Zoe Kazan) vor ihm – in Fleisch und Blut. Nach anfänglichem Schock beginnt Calvin seine Schöpfung zu nehmen, wie er sie geschrieben hat. Er ist glücklich. Und wie sich zeigt, kann Calvin kraft seiner Worte Ruby Sparks auch nachträglich Eigenschaften zuschreiben. Doch kann Ruby so eine eigene Identität entwickeln? Probleme sind vorprogrammiert. Findet die Liebe ihren Weg weg von der fiktionalisierten Idee? Wird die Geschichte ein gutes Ende nehmen?" rating="6.9000000953674299" year="2012" thumb="/library/metadata/3172/thumb/1413152968" art="/library/metadata/3172/art/1413152968" duration="6246304" originallyAvailableAt="2012-07-25" addedAt="1413152281" updatedAt="1413152968">
		<Media videoResolution="1080" id="2944" duration="6246304" bitrate="10106" width="1920" height="1040" aspectRatio="1.85" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="1">
			<Part id="2944" key="/library/parts/2944/file.mp4" duration="6246304" file="/mnt/media/Ina Filme/Ruby Sparks - Meine fabelhafte Freundin.mp4" size="7890275408" container="mp4" has64bitOffsets="1" hasChapterTextStream="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Sci-Fi &amp; Fantasy" />
		<Writer tag="Zoe Kazan" />
		<Director tag="Jonathan Dayton" />
		<Director tag="Valerie Faris" />
		<Country tag="USA" />
		<Role tag="Antonio Banderas" />
		<Role tag=" Alia Shawkat" />
		<Role tag=" Paul Dano" />
	</Video>
	<Video ratingKey="3173" key="/library/metadata/3173" type="movie" title="Satte Farben vor Schwarz" summary="Im Mittelpunkt des Films stehen Anita und Fred. Sie sind seit 50 Jahren ein Paar und fast genauso lange glücklich verheiratet. Die Beiden haben zwei erwachsene Kinder und die Enkelin steht kurz vor dem Abitur. Anita und Fred können nicht nur auf ein erfülltes Leben zurückblicken – sie sind noch mittendrin. Bei Fred wurde Prostatakrebs diagnostiziert. Erstmals in all den Jahren nimmt Fred sich nun Freiheiten heraus, wodurch er seine Frau vor den Kopf stößt." year="2010" thumb="/library/metadata/3173/thumb/1413152979" art="/library/metadata/3173/art/1413152979" duration="5071531" originallyAvailableAt="2010-10-12" addedAt="1413152281" updatedAt="1413152979">
		<Media videoResolution="576" id="2945" duration="5071531" bitrate="3608" width="720" height="544" aspectRatio="1.85" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="PAL" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="2945" key="/library/parts/2945/file.mp4" duration="5071531" file="/mnt/media/Ina Filme/Satte Farben vor Schwarz.mp4" size="2287120511" container="mp4" has64bitOffsets="0" hasChapterTextStream="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Drama" />
		<Director tag="Sophie Heldman" />
		<Country tag="Germany" />
		<Role tag="Bruno Ganz" />
		<Role tag="Senta Berger" />
	</Video>
	<Video ratingKey="3174" key="/library/metadata/3174" studio="Village Roadshow Pictures" type="movie" title="Sex and the City 2" contentRating="R" summary="Carrie, Charlotte, Miranda und Samantha sind zurück, mit mehr Problemen, Sex und Fashion Gucci Täschchen. Zusammen mit Carries Eheproblemen, Bürostress und einer kleinen Menopause geht’s diesmal nicht nur in New York sondern auch im Orient zur Sache. Vielleicht zumindest, schließlich ist da ja noch Aiden - Carries Ex." rating="5.4000000953674299" year="2010" thumb="/library/metadata/3174/thumb/1413152987" art="/library/metadata/3174/art/1413152987" duration="8423900" originallyAvailableAt="2010-05-27" addedAt="1413152281" updatedAt="1413152987">
		<Media videoResolution="480" id="2946" duration="8423900" bitrate="1325" width="720" height="400" aspectRatio="1.78" audioChannels="2" audioCodec="aac" videoCodec="h264" container="mp4" videoFrameRate="PAL" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="2946" key="/library/parts/2946/file.mp4" duration="8423900" file="/mnt/media/Ina Filme/Sex and the city 2.mp4" size="1395662924" container="mp4" has64bitOffsets="0" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Drama" />
		<Director tag="Michael Patrick King" />
		<Country tag="USA" />
		<Role tag="Sarah Jessica Parker" />
		<Role tag=" Kristin Davis" />
		<Role tag=" Cynthia Nixon" />
	</Video>
	<Video ratingKey="3186" key="/library/metadata/3186" type="movie" title="The Shipping News" titleSort="Shipping News" summary="Based on the book by Annie Proulx.  A man returns with his daughter to his ancestral home of Newfoundland for a new beginning.  He obtains work as a reporter, and is asked to document the shipping news, arrivals and departures from the local port." year="2001" thumb="/library/metadata/3186/thumb/1423495929" art="/library/metadata/3186/art/1423495929" duration="6399893" originallyAvailableAt="2001-12-18" addedAt="1413152284" updatedAt="1423495929">
		<Media videoResolution="480" id="2958" duration="6399893" bitrate="2560" width="720" height="448" aspectRatio="2.35" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="PAL" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="2958" key="/library/parts/2958/file.mp4" duration="6399893" file="/mnt/media/Ina Filme/The Shipping News.mp4" size="2048134332" container="mp4" has64bitOffsets="0" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Drama" />
		<Role tag="Lasse Hallstr&amp;#246;m" />
	</Video>
	<Video ratingKey="3175" key="/library/metadata/3175" studio="Ignite Entertainment" type="movie" title="Shrink" contentRating="R" summary="Unable to cope with a recent personal tragedy, LA&apos;s top celebrity shrink turns into a pothead with no concern for his appearance and a creeping sense of his inability to help his patients." year="2009" thumb="/library/metadata/3175/thumb/1423495930" art="/library/metadata/3175/art/1423495930" duration="6281115" originallyAvailableAt="2009-06-08" addedAt="1413152281" updatedAt="1423495930">
		<Media videoResolution="480" id="2947" duration="6281115" bitrate="1060" width="640" height="368" aspectRatio="1.78" audioChannels="2" audioCodec="aac" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="2947" key="/library/parts/2947/file.mp4" duration="6281115" file="/mnt/media/Ina Filme/Shrink.mp4" size="832457905" container="mp4" has64bitOffsets="0" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Sci-Fi &amp; Fantasy" />
		<Director tag="Jonas Pate" />
		<Role tag="Kevin Spacey" />
		<Role tag="Mark Webber" />
		<Role tag="Keke Palmer" />
	</Video>
	<Video ratingKey="3176" key="/library/metadata/3176" studio="StudioCanal" type="movie" title="Sightseers" contentRating="NR" summary="Chris wants to show girlfriend Tina his world, but events soon conspire against the couple and their dream caravan holiday takes a very wrong turn." rating="5.8000001907348597" year="2013" tagline="Killers on Tour!" thumb="/library/metadata/3176/thumb/1413153010" art="/library/metadata/3176/art/1413153010" duration="5073344" originallyAvailableAt="2013-05-09" addedAt="1413152283" updatedAt="1413153010">
		<Media videoResolution="1080" id="2948" duration="5073344" bitrate="5343" width="1920" height="804" aspectRatio="2.35" audioChannels="2" audioCodec="aac" videoCodec="h264" container="mp4" videoFrameRate="PAL" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="2948" key="/library/parts/2948/file.mp4" duration="5073344" file="/mnt/media/Ina Filme/Sightseers (2013).mp4" size="3388280027" container="mp4" has64bitOffsets="0" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Comedy" />
		<Writer tag="Steve Oram" />
		<Writer tag="Alice Lowe" />
		<Director tag="Ben Wheatley" />
		<Country tag="United Kingdom" />
		<Role tag="Alice Lowe" />
		<Role tag="Steve Oram" />
		<Role tag="Jonathan Aris" />
	</Video>
	<Video ratingKey="3177" key="/library/metadata/3177" studio="The Weinstein Company" type="movie" title="Silver Linings Playbook" originalTitle="Silver Linings Playbook" contentRating="R" summary="After spending eight months in a mental institution, a former teacher moves back in with his parents and tries to reconcile with his ex-wife." rating="6.6999998092651403" year="2012" tagline="Wenn du mir, dann ich dir." thumb="/library/metadata/3177/thumb/1413153034" art="/library/metadata/3177/art/1413153034" duration="7341216" originallyAvailableAt="2012-11-16" addedAt="1413152283" updatedAt="1413153034">
		<Media videoResolution="1080" id="2949" duration="7341216" bitrate="8206" width="1920" height="800" aspectRatio="2.35" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="1">
			<Part id="2949" key="/library/parts/2949/file.mp4" duration="7341216" file="/mnt/media/Ina Filme/Silver Linings Playbook.mp4" size="7530083941" container="mp4" has64bitOffsets="1" hasChapterTextStream="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Comedy" />
		<Writer tag="David O. Russell" />
		<Director tag="David O. Russell" />
		<Country tag="USA" />
		<Role tag="Jennifer Lawrence" />
		<Role tag=" Bradley Cooper" />
		<Role tag=" Robert De Niro" />
	</Video>
	<Video ratingKey="3178" key="/library/metadata/3178" studio="Miramax Films" type="movie" title="Smart People" contentRating="R" summary="Professor Lawrence Wetherhold (Dennis Quaid) might be imperiously brilliant, monumentally self-possessed and an intellectual giant -- but when it comes to solving the conundrums of love and family, he&apos;s as downright flummoxed as the next guy." rating="5.5999999046325701" year="2008" thumb="/library/metadata/3178/thumb/1413153047" art="/library/metadata/3178/art/1413153047" duration="5457653" originallyAvailableAt="2008-04-11" addedAt="1413152283" updatedAt="1413153047">
		<Media videoResolution="sd" id="2950" duration="5457653" bitrate="1113" width="608" height="336" aspectRatio="1.78" audioChannels="2" audioCodec="aac" videoCodec="h264" container="mp4" videoFrameRate="PAL" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="2950" key="/library/parts/2950/file.mp4" duration="5457653" file="/mnt/media/Ina Filme/Smart People.mp4" size="759053202" container="mp4" has64bitOffsets="0" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Comedy" />
		<Writer tag="Mark Poirier" />
		<Director tag="Noam Murro" />
		<Country tag="USA" />
		<Role tag="Dennis Quaid" />
		<Role tag="Sarah Jessica Parker" />
		<Role tag="Ellen Page" />
	</Video>
	<Video ratingKey="3179" key="/library/metadata/3179" studio="Canal+" type="movie" title="So ist Paris" originalTitle="Paris" contentRating="R" summary="Adam Goldberg delivers &quot;an uproarious study in transatlantic culture panic&quot; as Jack, an anxious, hypochondriac-prone New Yorker vacationing throughout Europe with his breezy, free-spirited Parisian girlfriend, Marion. But when they make a two-day stop in Marion&apos;s hometown, the couple&apos;s romantic trip takes a turn as Jack is exposed to Marion&apos;s sexually perverse and emotionally unstable family." rating="6.3000001907348597" year="2007" thumb="/library/metadata/3179/thumb/1413153053" art="/library/metadata/3179/art/1413153053" duration="7438933" originallyAvailableAt="2007-02-10" addedAt="1413152283" updatedAt="1413153053">
		<Media videoResolution="480" id="2951" duration="7438933" bitrate="1091" width="720" height="304" aspectRatio="2.35" audioChannels="2" audioCodec="aac" videoCodec="h264" container="mp4" videoFrameRate="PAL" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="2951" key="/library/parts/2951/file.mp4" duration="7438933" file="/mnt/media/Ina Filme/So ist Paris.mp4" size="1014132116" container="mp4" has64bitOffsets="0" hasChapterTextStream="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Drama" />
		<Writer tag="Cédric Klapisch" />
		<Director tag="Cédric Klapisch" />
		<Country tag="France" />
		<Role tag="Juliette Binoche" />
		<Role tag="Romain Duris" />
		<Role tag="Fabrice Luchini" />
	</Video>
	<Video ratingKey="3189" key="/library/metadata/3189" studio="Columbia Pictures" type="movie" title="The Social Network" titleSort="Social Network" contentRating="PG-13" summary="On a fall night in 2003, Harvard undergrad and computer programming genius Mark Zuckerberg sits down at his computer and heatedly begins working on a new idea. In a fury of blogging and programming, what begins in his dorm room soon becomes a global social network and a revolution in communication. A mere six years and 500 million friends later, Mark Zuckerberg is the youngest billionaire in history... but for this entrepreneur, success leads to both personal and legal complications." rating="6.9000000953674299" year="2010" tagline="Du bekommst keine 500 Millionen Freunde, ohne dir ein paar Feinde zu machen" thumb="/library/metadata/3189/thumb/1413153269" art="/library/metadata/3189/art/1413153269" duration="6934080" originallyAvailableAt="2010-10-01" addedAt="1413152284" updatedAt="1413153269">
		<Media videoResolution="480" id="2961" duration="6934080" bitrate="1834" width="720" height="304" aspectRatio="2.35" audioChannels="2" audioCodec="aac" videoCodec="h264" container="mp4" videoFrameRate="PAL" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="2961" key="/library/parts/2961/file.mp4" duration="6934080" file="/mnt/media/Ina Filme/The social network.mp4" size="1589540619" container="mp4" has64bitOffsets="0" hasChapterTextStream="1" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Drama" />
		<Writer tag="Aaron Sorkin" />
		<Director tag="David Fincher" />
		<Country tag="USA" />
		<Role tag="Jesse Eisenberg" />
		<Role tag="Andrew Garfield" />
		<Role tag="Justin Timberlake" />
	</Video>
	<Video ratingKey="3180" key="/library/metadata/3180" studio="Joe&apos;s Daughter" type="movie" title="Take This Waltz" contentRating="R" summary="Michelle Williams plays twenty-eight-year-old Margot, happily married to Lou (Seth Rogen), a good-natured cookbook author. But when Margot meets Daniel (Luke Kirby), a handsome artist who lives across the street, their mutual attraction is undeniable. Warmly human, funny and bittersweet, TAKE THIS WALTZ deftly avoids romantic clichés and paints an unusually true and unsentimental portrait of adult relationships." rating="6.1999998092651403" year="2012" thumb="/library/metadata/3180/thumb/1413153070" art="/library/metadata/3180/art/1413153070" duration="6991609" originallyAvailableAt="2012-06-29" addedAt="1413152284" updatedAt="1413153070">
		<Media videoResolution="1080" id="2952" duration="6991609" bitrate="8307" width="1920" height="1040" aspectRatio="1.85" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="0" has64bitOffsets="1">
			<Part id="2952" key="/library/parts/2952/file.mp4" duration="6991609" file="/mnt/media/Ina Filme/Take This Waltz (2012).mp4" size="7260300733" container="mp4" has64bitOffsets="1" hasChapterTextStream="1" optimizedForStreaming="0" />
		</Media>
		<Genre tag="Drama" />
		<Writer tag="Sarah Polley" />
		<Director tag="Sarah Polley" />
		<Country tag="Canada" />
		<Country tag="Spain" />
		<Role tag="Michelle Williams" />
		<Role tag="Seth Rogen" />
		<Role tag="Sarah Silverman" />
	</Video>
	<Video ratingKey="3187" key="/library/metadata/3187" studio="Spyglass Entertainment" type="movie" title="The Tourist" titleSort="Tourist" contentRating="PG-13" summary="Revolves around Frank, an American tourist visiting Italy to mend a broken heart. Elise is an extraordinary woman who deliberately crosses his path." rating="6" year="2010" thumb="/library/metadata/3187/thumb/1413153209" art="/library/metadata/3187/art/1413153209" duration="6208256" originallyAvailableAt="2010-12-17" addedAt="1413152284" updatedAt="1413153209">
		<Media videoResolution="720" id="2959" duration="6208256" bitrate="2776" width="1280" height="534" aspectRatio="2.35" audioChannels="6" audioCodec="ac3" videoCodec="h264" container="mp4" videoFrameRate="24p" optimizedForStreaming="1" has64bitOffsets="0">
			<Part id="2959" key="/library/parts/2959/file.mp4" duration="6208256" file="/mnt/media/Ina Filme/The Tourist.mp4" size="2154208473" container="mp4" has64bitOffsets="0" optimizedForStreaming="1" />
		</Media>
		<Genre tag="Action &amp; Adventure" />
		<Writer tag="Florian Henckel von Donnersmarck" />
		<Writer tag="Julian Fellowes" />
		<Director tag="Florian Henckel von Donnersmarck" />
		<Country tag="France" />
		<Country tag="Italy" />
		<Role tag="Johnny Depp" />
		<Role tag="Angelina Jolie" />
		<Role tag="Paul Bettany" />
	</Video>
</MediaContainer>"""
    else:
        return """<MediaContainer size="6" allowSync="0" art="/:/resources/movie-fanart.jpg" content="secondary" identifier="com.plexapp.plugins.library" mediaTagPrefix="/system/bundle/media/flags/" mediaTagVersion="1420847353" thumb="/:/resources/movie.png" title1="Ina Filme" viewGroup="secondary" viewMode="65592">
	<Directory key="addedAt" title="Date Added" />
	<Directory key="originallyAvailableAt" title="Date Released" />
	<Directory default="asc" key="titleSort" title="Name" />
	<Directory key="rating" title="Rating" />
	<Directory key="mediaHeight" title="Resolution" />
	<Directory key="duration" title="Duration" />
</MediaContainer>"""

@bottle.route('/web/')
@bottle.route('/web/<filename:path>')
def send_static(filename="index.html"):
    return bottle.static_file(filename, root=web_path)


@bottle.route('/<filename:path>')
def default(filename):
    return bottle.static_file(filename, root=web_path)


# waits to recieve a MSearch mesagge. If a right message is recieved , calls callbackfun
def gdm_broadcast():
    SSDP_ADDR = '239.0.0.250'
    SSDP_PORT = 32414
    multicast_group_c = SSDP_ADDR
    server_address = ('', SSDP_PORT)

    import time
    import struct
    import socket
    import random

    # message = 'M-SEARCH * HTTP/1.1\r\nHOST: %s:%d\r\nMAN: "ssdp:discover"\r\nMX: 2\r\nST: ssdp:all\r\n\r\n' % (SSDP_ADDR, SSDP_PORT)
    # UPDATE * HTTP/1.0
    Response_message = """HTTP/1.1 200 OK\r
Content-Type: plex/media-server\r
Name: %s\r
Port: 32400\r
Resource-Identifier: 23f2d6867befb9c26f7b5f366d4dd84e9b2294c9\r
Updated-At: 1466340239\r
Version: 0.9.16.6.1993-5089475\r
Parameters: playerAdd=192.168.2.102\r\n""" % settings["title"]

    # Create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(server_address)
    # add the socket to the multicast group on all interfaces.
    group = socket.inet_aton(multicast_group_c)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    while True:
        print('waiting to recieve')
        data, address = sock.recvfrom(1024)
        print('received %s bytes from %s' % (len(data), address))
        print(data)

        # discard message if header is not in right format
        if data == b'M-SEARCH * HTTP/1.1\r\n\r\n':
            mxpos = data.find(b'MX:')
            maxdelay = int(data[mxpos+4]) % 5   # Max value of this field is 5
            time.sleep(random.randrange(0, maxdelay+1, 1))  # wait for random 0-MX time until sending out responses using unicast.
            print('Sending M Search response to - ', address)
            sock.sendto(Response_message.encode("utf8"), address)
        else:
            print('recieved wrong MSearch')

        time.sleep(5)


# gdm_thread = threading.Thread(target=gdm_broadcast)
# gdm_thread.start()

bottle.debug(True)
bottle.run(host='0.0.0.0', port=32400, reloader=True)
