# -*- coding: utf-8 -*-
# Module: default
# Author: MiRo
# Created on: 2018-06-02
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import sys
import routing
from lib.waipu_api import WaipuAPI
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import inputstreamhelper
import time
from dateutil import parser
import urllib

class ItemClass(object):
    pass

plugin = routing.Plugin()

username = xbmcaddon.Addon().getSetting("username")
password = xbmcaddon.Addon().getSetting("password")
provider = int(xbmcaddon.Addon().getSetting("provider_select"))

# open settings,
if not username or not password:
    xbmcaddon.Addon().openSettings()

w = WaipuAPI(username, password, provider)

itemList = []

def itemExits(assetID, a_list):
    for a_item in a_list:
        if (a_item.assetId == assetID):
            return True
    return False

def _T(id):
    return xbmcaddon.Addon().getLocalizedString(id)

def load_acc_details():
    last_check = xbmcplugin.getSetting(plugin.handle, "accinfo_lastcheck")
    info_acc = xbmcplugin.getSetting(plugin.handle, "accinfo_account")
    user = xbmcplugin.getSetting(plugin.handle, "username")

    if info_acc != user or (int(time.time()) - int(last_check)) > 15*60:
        # load acc details
        acc_details = w.getAccountDetails()
        xbmc.log("waipu accdetails: " + str(acc_details), level=xbmc.LOGDEBUG)
        if 'error' in acc_details:
            xbmcaddon.Addon().setSetting('accinfo_status', acc_details["error"])
            xbmcaddon.Addon().setSetting('accinfo_account', "-")
            xbmcaddon.Addon().setSetting('accinfo_subscription', "-")
            xbmcaddon.Addon().setSetting('accinfo_network', "-")
        else:
            xbmcaddon.Addon().setSetting('accinfo_status', "Angemeldet")
            xbmcaddon.Addon().setSetting('accinfo_account', acc_details["sub"])
            xbmcaddon.Addon().setSetting('accinfo_subscription', acc_details["userAssets"]["account"]["subscription"])
            xbmcaddon.Addon().setSetting('accinfo_lastcheck', str(int(time.time())))
            # load network status
            status = w.getStatus()
            xbmc.log("waipu status: " + str(status), level=xbmc.LOGDEBUG)
            xbmcaddon.Addon().setSetting('accinfo_network_ip', status["ip"])
            if status["statusCode"] == 200:
                # direct access
                xbmcaddon.Addon().setSetting('accinfo_network', "Waipu verfügbar")
                xbmcaddon.Addon().setSetting('acc_needs_open_eu', 'false')
            elif status["isEuMobilityNetwork"]:
                # via eu
                xbmcaddon.Addon().setSetting('accinfo_network', "Via EU mobility verfügbar")
                xbmcaddon.Addon().setSetting('acc_needs_open_eu', 'true')
            else:
                xbmcaddon.Addon().setSetting('accinfo_network', status["statusText"])
                xbmcaddon.Addon().setSetting('acc_needs_open_eu', 'false')

@plugin.route('/list-recordings')
def list_recordings():
    # get filter for sub-folders
    s_filter = plugin.args['s_filter'][0]

    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(plugin.handle, 'waipu.tv')
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(plugin.handle, 'videos')
    # Get video categories
    try:
        recordings = w.getRecordings()
    except Exception as e:
        dialog = xbmcgui.Dialog().ok("Error", str(e))
        return

    b_episodeid = xbmcplugin.getSetting(plugin.handle, "recordings_episode_id") == "true"
    b_recordingdate = xbmcplugin.getSetting(plugin.handle, "recordings_date") == "true"

    # clear list
    itemList = []

    # Iterate through categories
    for recording in recordings:
        if 'locked' in recording and recording['locked']:
            continue

        # check we have a filter
        if(s_filter != "0"):
            # skip itens, if wrong assetId
            if(recording['epgData']["assetId"] != s_filter):
                continue

        # new item
        item = ItemClass()

        item.recordID = recording["id"]
        item.status = recording['status']

        item.title = recording['epgData']['title']
        item.channel = recording['epgData']['channel']
        item.genre = recording['epgData']['genre']
        item.description = recording['epgData']['description']

        item.assetId = recording['epgData']["assetId"]
        item.episodeId = recording['epgData']['episodeId']
        item.episodeTitle = recording['epgData']['episodeTitle']
        item.episode = recording['epgData']['episode']
        item.season = recording['epgData']['season']

        item.startTime = parser.parse(recording['epgData']['startTime'])

        for previewImage in recording['epgData']['previewImages']:
            item.previewImage = previewImage + "?width=200&height=200"
            break

        item.count = 1

        # check if we are in the overview of recordings
        if (s_filter == "0"):
            # new item
            if not itemExits(item.assetId, itemList):
                itemList.append(item)
            else:
                # item exist, inc counter
                for aItem in itemList:
                    if (aItem.assetId in item.assetId):
                        aItem.count = aItem.count + 1
        else:
            # not the overview, so add all items
            itemList.append(item)

    # how many items?
    #xbmc.log("waipu test: " + str(len(itemList)), level=xbmc.LOGDEBUG)

    # enumerate through list
    for item in itemList:

        # check for more than 1 recording
        if(item.count > 1) and (s_filter == "0"):
            list_item = xbmcgui.ListItem(label= "[B]" +  item.title +  "[/B]" +  " - " + str(item.count) + " " + _T(32031), iconImage="DefaultFolder.png")

            if(item.previewImage is not None):
                xbmc.log("waipu image: " + previewImage, level=xbmc.LOGDEBUG)
                list_item.setArt(
                    {'thumb': item.previewImage, 'icon': item.previewImage, 'clearlogo': item.previewImage})

            metadata = {
                'genre': item.genre,
                'mediatype': 'video'}

            list_item.setInfo('video', metadata)
            xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(list_recordings, s_filter=item.assetId), list_item, isFolder=True)

        else:
            # normal display
            label_dat = ''

            # reocord is runing
            if item.status == "RECORDING":
                label_dat = '[COLOR red][REC][/COLOR] '

            metadata = {
                'genre': item.genre,
                'plot': item.description,
                'mediatype': 'video'}

            if item.episodeId is not None:
                # tv show
                if item.episodeTitle is not None:
                    metadata.update({"tvshowtitle": item.episodeTitle})
                    label_dat = label_dat + "[B]" + item.title + "[/B] - " + item.episodeTitle
                else:
                    label_dat = label_dat + "[B]" + item.title + "[/B]"

                if b_episodeid and (item.season is not None) and (item.episode is not None):
                    label_dat = label_dat + " (S"+ item.season + "E"+ item.episode +")"

                # add record date/time
                if b_recordingdate and (item.startTime is not None):
                    label_dat = label_dat + " " + item.startTime.strftime("(%d.%m.%Y %H:%M)")

                metadata.update({
                    'title': label_dat,
                    'season': item.season,
                    'episode': item.episode,
                })
            else:
                # movie
                label_dat = label_dat + "[B]" + item.title + "[/B]"

                # add record date/time
                if b_recordingdate and (item.startTime is not None):
                    label_dat = label_dat + " " + item.startTime.strftime("(%d.%m.%Y %H:%M)")

                metadata.update({
                    'title': label_dat
                })

            list_item = xbmcgui.ListItem(label=label_dat)
            list_item.setInfo('video', metadata)

            if(item.previewImage is not None):
                xbmc.log("waipu image: " + previewImage, level=xbmc.LOGDEBUG)
                list_item.setArt(
                    {'thumb': item.previewImage, 'icon': item.previewImage, 'clearlogo': item.previewImage})

            list_item.setProperty('IsPlayable', 'true')
            url = plugin.url_for(play_recording, recording_id= item.recordID)

            # path to callback and title (in ascii)
            s_path = plugin.url_for(delete_recordings)
            s_Title = label_dat.encode('ascii','ignore').decode('ascii')

            list_item.addContextMenuItems([("Aufnahme löschen", 'RunPlugin(%s?recording_id=%s&title=%s)' % (s_path, item.recordID, s_Title))])
            xbmcplugin.addDirectoryItem(plugin.handle, url, list_item, isFolder=False)

    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(plugin.handle, cacheToDisc=False)

@plugin.route('/delete-recordings')
def delete_recordings():

    # get filter for sub-folders
    s_recordId = plugin.args['recording_id'][0]
    # get title
    s_title = plugin.args['title'][0]
    s_title = s_title.encode('utf8','ignore')

    ok = False
    ok = xbmcgui.Dialog().yesno(xbmcaddon.Addon().getAddonInfo('name'), "Möchten Sie die Aufnahme\n" +  s_title + "\nlöschen?")

    if (ok):
        result = w.deleteRecordings(s_recordId)
        xbmc.log("waipu DELETE " + s_recordId + " result = " + str(result), level=xbmc.LOGDEBUG)

        xbmc.executebuiltin('Container.Refresh')

def filter_pictograms(data, filter=True):
    if filter:
        return ''.join(c for c in data if ord(c) < 0x25A0 or ord(c) > 0x1F5FF)
    return data


@plugin.route('/play-vod')
def play_vod():
    streamUrlProvider = plugin.args['streamUrlProvider'][0]
    title = plugin.args['title'][0]
    # logo_url = plugin.args['logo_url'][0]
    user_agent = "kodi plugin for waipu.tv (python)"

    stream = w.getUrl(streamUrlProvider)
    # print("stream: "+str(stream))

    is_helper = inputstreamhelper.Helper('mpd', drm='widevine')
    if not is_helper.check_inputstream():
        return False

    # check if we need to call EU:
    if xbmcplugin.getSetting(plugin.handle, "acc_needs_open_eu") == "true":
        w.open_eu_network() # TODO: check for response code 200

    if "player" in stream and "mpd" in stream["player"]:
        listitem = xbmcgui.ListItem(title, path=stream["player"]["mpd"])
        listitem.setMimeType('application/xml+dash')
        listitem.setProperty(is_helper.inputstream_addon + ".license_type", "com.widevine.alpha")
        listitem.setProperty(is_helper.inputstream_addon + ".manifest_type", "mpd")
        listitem.setProperty('inputstreamaddon', is_helper.inputstream_addon)
        license_str = w.getLicense()
        listitem.setProperty(is_helper.inputstream_addon + '.license_key',
                             "https://drm.wpstr.tv/license-proxy-widevine/cenc/|User-Agent=" + user_agent + "&Content-Type=text%2Fxml&x-dt-custom-data=" + license_str + "|R{SSM}|JBlicense")
        xbmcplugin.setResolvedUrl(plugin.handle, True, listitem=listitem)
    else:
        return False


@plugin.route('/list-vod-channel')
def list_vod_channel():
    channel_id = plugin.args['channel_id'][0]

    xbmcplugin.setPluginCategory(plugin.handle, 'waipu.tv')
    streams = w.getEPGForChannel(channel_id)
    for stream in streams:
        #print("stream: "+str(stream))
        title = filter_pictograms(stream["title"])
        streamUrlProvider = stream["streamUrlProvider"]

        previewImage=""
        if "previewImages" in stream:
            previewImage = stream["previewImages"][0] + "?width=200&height=200"

        plot = ""
        if "description" in stream:
            plot = stream["description"]

        list_item = xbmcgui.ListItem(label=title)
        list_item.setInfo('video', {'title': title,
                                    'plot': plot,
                                    'mediatype': 'video'})

        list_item.setArt({'thumb': previewImage, 'icon': previewImage, 'clearlogo': previewImage})
        list_item.setProperty('IsPlayable', 'true')


        url = plugin.url_for(play_vod, streamUrlProvider=streamUrlProvider,
                             title=title.encode('ascii', 'ignore').decode('ascii'), logo_url=previewImage)
        xbmcplugin.addDirectoryItem(plugin.handle, url, list_item, isFolder=False)

    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(plugin.handle)

@plugin.route('/list-vod-channels')
def list_vod_channels():
    load_acc_details()
    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(plugin.handle, 'waipu.tv')
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(plugin.handle, 'videos')
    # Get video categories
    epg_in_channel = xbmcplugin.getSetting(plugin.handle, "epg_in_channel") == "true"
    epg_in_plot = xbmcplugin.getSetting(plugin.handle, "epg_in_plot") == "true"
    if epg_in_plot:
        epg_hours_future = xbmcplugin.getSetting(plugin.handle, "epg_hours_future")
    else:
        epg_hours_future = 0
    try:
        channels = w.getChannels(epg_hours_future)
    except Exception as e:
        dialog = xbmcgui.Dialog().ok("Error", str(e))
        return

    # Iterate through categories
    order_index = 0
    for data in channels:
        channel = data["channel"]

        if not ("properties" in channel and "tvfuse" in channel["properties"]):
            # is not VoD channel
            continue

        order_index += 1
        title = channel['displayName']

        list_item = xbmcgui.ListItem(label=title, iconImage="DefaultFolder.png")
        logo_url = ""
        for link in channel["links"]:
            if link["rel"] == "iconsd":
                logo_url = link["href"] + "?width=200&height=200"

        list_item.setArt({'thumb': logo_url, 'icon': logo_url, 'clearlogo': logo_url})
        url = plugin.url_for(list_vod_channel, channel_id=channel['id'])
        xbmcplugin.addDirectoryItem(plugin.handle, url, list_item, isFolder=True)
    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(plugin.handle, xbmcplugin.SORT_METHOD_TRACKNUM)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(plugin.handle)

@plugin.route('/list-channels')
def list_channels():
    load_acc_details()
    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(plugin.handle, 'waipu.tv')
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(plugin.handle, 'videos')
    # Get video categories
    epg_in_channel = xbmcplugin.getSetting(plugin.handle, "epg_in_channel") == "true"
    epg_in_plot = xbmcplugin.getSetting(plugin.handle, "epg_in_plot") == "true"
    if epg_in_plot:
        epg_hours_future = xbmcplugin.getSetting(plugin.handle, "epg_hours_future")
    else:
        epg_hours_future = 0
    try:
        channels = w.getChannels(epg_hours_future)
    except Exception as e:
        dialog = xbmcgui.Dialog().ok("Error", str(e))
        return

    b_filter = xbmcplugin.getSetting(plugin.handle, "filter_pictograms") == "true"
    # Iterate through categories
    order_index = 0
    for data in channels:
        channel = data["channel"]

        if "properties" in channel and "tvfuse" in channel["properties"]:
            # is VoD channel
            continue

        order_index += 1

        if "programs" in data and len(data["programs"]) > 0:
            epg_now = " | " + filter_pictograms(data["programs"][0]["title"], b_filter)

        plot = ""
        b1 = "[B]"
        b2 = "[/B]"
        if epg_in_plot and "programs" in data:
            for program in data["programs"]:
                starttime = parser.parse(program["startTime"]).strftime("%H:%M")
                plot += "[B]" + starttime + " Uhr:[/B] " + b1 + filter_pictograms(program["title"],
                                                                                  b_filter) + b2 + "\n"
                b1 = ""
                b2 = ""
        elif not epg_in_plot and "programs" in data and len(data["programs"]) > 0:
            plot = filter_pictograms(data["programs"][0]["description"], b_filter)

        if epg_in_channel:
            title = "[B]" + channel['displayName'] + "[/B]" + epg_now
        else:
            title = "[B]" + channel['displayName'] + "[/B]"

        list_item = xbmcgui.ListItem(label=title)
        list_item.setInfo('video', {'title': title,
                                    'tracknumber': order_index,
                                    'plot': plot,
                                    'mediatype': 'video'})
        logo_url = ""
        for link in channel["links"]:
            if link["rel"] == "iconsd":
                logo_url = link["href"] + "?width=200&height=200"

        list_item.setArt({'thumb': logo_url, 'icon': logo_url, 'clearlogo': logo_url})
        list_item.setProperty('IsPlayable', 'true')
        url = plugin.url_for(play_channel, channel_id=channel["id"], title=title.encode('ascii', 'ignore').decode('ascii'), logo_url=logo_url)
        xbmcplugin.addDirectoryItem(plugin.handle, url, list_item, isFolder=False)
    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(plugin.handle, xbmcplugin.SORT_METHOD_TRACKNUM)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(plugin.handle)

@plugin.route('/play-channel')
def play_channel():
    title = plugin.args['title'][0]
    logo_url = plugin.args['logo_url'][0]
    channel_id = plugin.args['channel_id'][0]

    is_helper = inputstreamhelper.Helper('mpd', drm='widevine')
    if not is_helper.check_inputstream():
        return False

    # check if we need to call EU:
    if xbmcplugin.getSetting(plugin.handle, "acc_needs_open_eu") == "true":
        w.open_eu_network() # TODO: check for response code 200

    user_agent = "kodi plugin for waipu.tv (python)"
    """
    Play a video by the provided path.

    :param path: Fully-qualified video URL
    :type path: str
    """
    stream_resp = w.playChannel(channel_id)
    xbmc.log("play channel (stream resp): " + str(stream_resp), level=xbmc.LOGDEBUG)

    if "streamUrl" not in stream_resp:
        xbmc.executebuiltin(
            'Notification("Stream selection","No stream of type \'' + str(stream_select) + '\' found",10000)')
        return

    listitem = xbmcgui.ListItem(channel_id, path=stream_resp["streamUrl"])
    listitem.setArt({'thumb': logo_url, 'icon': logo_url, 'clearlogo': logo_url})

    metadata = {'title': title, 'mediatype': 'video'}

    if xbmcplugin.getSetting(plugin.handle, "metadata_on_play") == "true":
        current_program = w.getCurrentProgram(channel_id)
        xbmc.log("play channel metadata: " + str(current_program), level=xbmc.LOGDEBUG)

        b_filter = xbmcplugin.getSetting(plugin.handle, "filter_pictograms") == "true"

        description = ""
        if "title" in current_program and current_program["title"] is not None:
            description = "[B]" + filter_pictograms(current_program["title"], b_filter) + "[/B]\n"
            metadata.update({'title': filter_pictograms(current_program["title"], b_filter)})
        if "description" in current_program and current_program["description"] is not None:
            description += filter_pictograms(current_program["description"], b_filter)
        metadata.update({'plot': description})

    listitem.setInfo('video', metadata)
    listitem.setMimeType('application/xml+dash')
    listitem.setProperty(is_helper.inputstream_addon + ".license_type", "com.widevine.alpha")
    listitem.setProperty(is_helper.inputstream_addon + ".manifest_type", "mpd")
    listitem.setProperty('inputstreamaddon', is_helper.inputstream_addon)
    # License update, to be tested...
    # listitem.setProperty(is_helper.inputstream_addon + ".media_renewal_url", get_url(action='renew_token', playouturl=playouturl))

    license_str = w.getLicense()
    listitem.setProperty(is_helper.inputstream_addon + '.license_key',
                         "https://drm.wpstr.tv/license-proxy-widevine/cenc/|User-Agent=" + user_agent + "&Content-Type=text%2Fxml&x-dt-custom-data=" + license_str + "|R{SSM}|JBlicense")

    xbmcplugin.setResolvedUrl(plugin.handle, True, listitem=listitem)

@plugin.route('/renew-token')
def renew_token():
    playouturl = plugin.args['playouturl'][0]
    # user_agent = "waipu-2.29.3-370e0a4-9452 (Android 8.1.0)"
    channel = w.playChannel(playouturl)
    xbmc.log("renew channel token: " + str(channel), level=xbmc.LOGDEBUG)

    stream_select = xbmcplugin.getSetting(plugin.handle, "stream_select")
    xbmc.log("stream to be renewed: " + str(stream_select), level=xbmc.LOGDEBUG)

    url = ""
    for stream in channel["streams"]:
        if (stream["protocol"] == 'mpeg-dash'):
            # if (stream["protocol"] == 'hls'):
            for link in stream['links']:
                path = link["href"]
                rel = link["rel"]
                if path and (stream_select == "auto" or rel == stream_select):
                    # path=path+"|User-Agent="+user_agent
                    url = path
                    xbmc.log("selected renew stream: " + str(link), level=xbmc.LOGDEBUG)
                    break
    xbmc.executebuiltin(
        'Notification("Stream RENEW","tada",30000)')
    listitem = xbmcgui.ListItem()
    xbmcplugin.addDirectoryItem(plugin.handle, url, listitem)
    xbmcplugin.endOfDirectory(plugin.handle, cacheToDisc=False)

@plugin.route('/play-recording')
def play_recording():
    recordingid = plugin.args['recording_id'][0]

    is_helper = inputstreamhelper.Helper('mpd', drm='widevine')
    if not is_helper.check_inputstream():
        return False

    # check if we need to call EU:
    if xbmcplugin.getSetting(plugin.handle, "acc_needs_open_eu") == "true":
        w.open_eu_network() # TODO: check for response code 200

    user_agent = "kodi plugin for waipu.tv (python)"

    streamingData = w.playRecording(recordingid)
    xbmc.log("play recording: " + str(streamingData), level=xbmc.LOGDEBUG)

    for stream in streamingData["streamingDetails"]["streams"]:
        if (stream["protocol"] == 'MPEG_DASH'):
            path = stream["href"]
            if path:
                path = path + "|User-Agent=" + user_agent
                # print(path)
                break

    b_filter = xbmcplugin.getSetting(plugin.handle, "filter_pictograms") == "true"
    b_episodeid = xbmcplugin.getSetting(plugin.handle, "recordings_episode_id") == "true"
    b_recordingdate = xbmcplugin.getSetting(plugin.handle, "recordings_date") == "true"
    title = ""
    metadata = {'mediatype': 'video'}
    if streamingData["epgData"]["title"]:
        title = filter_pictograms(streamingData["epgData"]["title"], b_filter)
    if streamingData["epgData"]["episodeTitle"]:
        title = title + ": " + filter_pictograms(streamingData["epgData"]["episodeTitle"], b_filter)
    if b_recordingdate and not streamingData["epgData"]["episodeId"] and streamingData["epgData"]["startTime"]:
        startDate = parser.parse(streamingData['epgData']['startTime'])
        title = title + " " + startDate.strftime("(%d.%m.%Y %H:%M)")
    if b_episodeid and streamingData['epgData']['season'] and streamingData['epgData']['episode']:
        title = title + " (S" + streamingData['epgData']['season'] + "E" + streamingData['epgData']['episode'] + ")"
        metadata.update({
            'season': streamingData['epgData']['season'],
            'episode': streamingData['epgData']['episode'],
        })

    metadata.update({"title": title})

    listitem = xbmcgui.ListItem(title, path=path)

    if "epgData" in streamingData and streamingData["epgData"]["description"]:
        metadata.update({"plot": filter_pictograms(streamingData["epgData"]["description"], b_filter)})

    if "epgData" in streamingData and len(streamingData["epgData"]["previewImages"]) > 0:
        logo_url = streamingData["epgData"]["previewImages"][0] + "?width=256&height=256"
        listitem.setArt({'thumb': logo_url, 'icon': logo_url})

    listitem.setInfo('video', metadata)
    listitem.setMimeType('application/xml+dash')
    listitem.setProperty(is_helper.inputstream_addon + ".license_type", "com.widevine.alpha")
    listitem.setProperty(is_helper.inputstream_addon + ".manifest_type", "mpd")
    listitem.setProperty('inputstreamaddon', is_helper.inputstream_addon)

    license_str = w.getLicense()
    listitem.setProperty(is_helper.inputstream_addon + '.license_key',
                         "https://drm.wpstr.tv/license-proxy-widevine/cenc/|User-Agent=" + user_agent + "&Content-Type=text%2Fxml&x-dt-custom-data=" + license_str + "|R{SSM}|JBlicense")

    xbmcplugin.setResolvedUrl(plugin.handle, True, listitem=listitem)

@plugin.route('/')
def index():
    load_acc_details()

    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(plugin.handle, 'waipu.tv')

    # TV channel list
    list_item = xbmcgui.ListItem(label=_T(32030), iconImage="DefaultAddonPVRClient.png")
    xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(list_channels), list_item, isFolder=True)

    # VoD Channels
    list_item = xbmcgui.ListItem(label=_T(32032), iconImage="DefaultFolder.png")
    xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(list_vod_channels), list_item, isFolder=True)

    # recordings list (overview)
    list_item = xbmcgui.ListItem(label=_T(32031), iconImage="DefaultFolder.png")
    xbmcplugin.addDirectoryItem(plugin.handle, plugin.url_for(list_recordings, s_filter="0"), list_item, isFolder=True)

    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(plugin.handle)

def run():
    plugin.run()
