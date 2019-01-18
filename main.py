# -*- coding: utf-8 -*-
# Module: default
# Author: MiRo
# Created on: 2018-06-02
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import sys
from urllib import urlencode
from urlparse import parse_qsl
from waipu import Waipu
import xbmcgui
import xbmcplugin
import xbmcaddon
import base64
import json
import inputstreamhelper
import time
from dateutil import parser

# Get the plugin url in plugin:// notation.
_url = sys.argv[0]
# Get the plugin handle as an integer number.
_handle = int(sys.argv[1])
username = xbmcplugin.getSetting(_handle, "username")
password = xbmcplugin.getSetting(_handle, "password")

# open settings, 
if not username or not password:
    xbmcaddon.Addon().openSettings()

w = Waipu(username, password)


def get_url(**kwargs):    
    """
    Create a URL for calling the plugin recursively from the given set of keyword arguments.

    :param kwargs: "argument=value" pairs
    :type kwargs: dict
    :return: plugin call URL
    :rtype: str
    """
    return '{0}?{1}'.format(_url, urlencode(kwargs))

def _T(id):
    return xbmcaddon.Addon().getLocalizedString(id)

def get_default():
    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(_handle, 'waipu.tv')

    # TV channel list
    list_item = xbmcgui.ListItem(label=_T(32030), iconImage="DefaultAddonPVRClient.png")
    url = get_url(action='list-channels')
    xbmcplugin.addDirectoryItem(_handle, url, list_item, isFolder=True)

    # recordings list
    list_item = xbmcgui.ListItem(label=_T(32031), iconImage="DefaultFolder.png")
    url = get_url(action='list-recordings')
    xbmcplugin.addDirectoryItem(_handle, url, list_item, isFolder=True)

    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)


def list_recordings():
    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(_handle, 'waipu.tv')
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(_handle, 'videos')
    # Get video categories
    try:
        recordings = w.getRecordings()
    except Exception as e:
        dialog = xbmcgui.Dialog().ok("Error", str(e))
        return
    # Iterate through categories
    for recording in recordings:
        label_dat = ''
        metadata = {
            'genre': recording['epgData']['genre'],
            'plot': recording['epgData']['description'],
            'mediatype': 'video'}

        if "episodeId" in recording['epgData'] and recording['epgData']['episodeId']:
            # tv show
            if recording['epgData']['episodeTitle']:
                metadata.update({"tvshowtitle": recording['epgData']['episodeTitle']})
                label_dat = "[B]" + recording['epgData']['title'] + "[/B] - " + recording['epgData']['episodeTitle']
            else:
                label_dat = "[B]" + recording['epgData']['title'] + "[/B]"
            metadata.update({
                'title': label_dat,
                'season': recording['epgData']['season'],
                'episode': recording['epgData']['episode'],
                })
        else:
            # movie
            label_dat = "[B]" + recording['epgData']['title'] + "[/B]"
            metadata.update({
                'title': label_dat
                })

        list_item = xbmcgui.ListItem(label=label_dat)
        list_item.setInfo('video', metadata)

        for previewImage in recording['epgData']['previewImages']:
            previewImage += "?width=200&height=200"
            xbmc.log("waipu image: " + previewImage, level=xbmc.LOGDEBUG)
            list_item.setArt(
            {'thumb': previewImage, 'icon': previewImage, 'clearlogo': previewImage})
            break
        list_item.setProperty('IsPlayable', 'true')
        url = get_url(action='play-recording', recordingid=recording["id"])
        xbmcplugin.addDirectoryItem(_handle, url, list_item, isFolder=False)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)


def list_channels():
    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(_handle, 'waipu.tv')
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(_handle, 'videos')
    # Get video categories
    epg_in_channel = xbmcplugin.getSetting(_handle, "epg_in_channel") == "true"
    epg_in_plot = xbmcplugin.getSetting(_handle, "epg_in_plot") == "true"
    if epg_in_plot:
        epg_hours_future = xbmcplugin.getSetting(_handle, "epg_hours_future")
    else:
        epg_hours_future = 0
    try:
        channels = w.getChannels(epg_hours_future)
    except Exception as e:
        dialog = xbmcgui.Dialog().ok("Error", str(e))
        return
    # Iterate through categories
    for data in channels:
        channel = data["channel"]

        if "programs" in data and len(data["programs"]) > 0:
            epg_now = " | "+data["programs"][0]["title"]

        plot = ""
        b1 = "[B]"
        b2 = "[/B]"
        if epg_in_plot and "programs" in data:
            for program in data["programs"]:
                starttime = parser.parse(program["startTime"]).strftime("%H:%M")
                plot += "[B]" + starttime + " Uhr:[/B] " + b1 + program["title"] + b2 + "\n"
                b1 = ""
                b2 = ""
        elif not epg_in_plot and "programs" in data and len(data["programs"]) > 0:
            plot = data["programs"][0]["description"]

        if epg_in_channel:
            title = "[B]"+channel['displayName']+"[/B]"+epg_now
        else:
            title = channel['displayName']


        list_item = xbmcgui.ListItem(label=title)
        list_item.setInfo('video', {'title': title,
                                    'tracknumber' : channel['orderIndex']+1,
                                    'plot': plot,
                                    'mediatype': 'video'})
        logo_url = ""
        livePlayoutURL = ""
        for link in channel["links"]:
            if link["rel"] == "iconsd":
                logo_url = link["href"]+ "?width=200&height=200"
            if link["rel"] == "livePlayout":
                livePlayoutURL = link["href"]

        list_item.setArt({'thumb': logo_url, 'icon': logo_url, 'clearlogo': logo_url})
        list_item.setProperty('IsPlayable', 'true')
        url = get_url(action='play-channel', playouturl=livePlayoutURL)
        xbmcplugin.addDirectoryItem(_handle, url, list_item, isFolder = False)
    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_TRACKNUM)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)

def play_channel(playouturl):

    is_helper = inputstreamhelper.Helper('mpd', drm='widevine')
    if not is_helper.check_inputstream():
        return False

    user_agent = "waipu-2.29.3-370e0a4-9452 (Android 8.1.0)"
    """
    Play a video by the provided path.

    :param path: Fully-qualified video URL
    :type path: str
    """
    channel = w.playChannel(playouturl)
    xbmc.log("play channel: " + str(channel), level=xbmc.LOGDEBUG)

    for stream in channel["streams"]:
        if (stream["protocol"] == 'mpeg-dash'):
        #if (stream["protocol"] == 'hls'):
            for link in stream['links']:
                path=link["href"]
                if path:
                    path=path+"|User-Agent="+user_agent
                    print path
                    break

    listitem = xbmcgui.ListItem(channel["channel"], path=path)
    listitem.setMimeType('application/xml+dash')
    listitem.setProperty(is_helper.inputstream_addon + ".license_type", "com.widevine.alpha")
    listitem.setProperty(is_helper.inputstream_addon + ".manifest_type", "mpd")
    listitem.setProperty('inputstreamaddon', is_helper.inputstream_addon)

    # Prepare for drm keys
    jwtheader,jwtpayload,jwtsignature = w.getToken().split(".")
    xbmc.log("waipu jwt payload: "+jwtpayload, level=xbmc.LOGDEBUG)
    jwtpayload_decoded = base64.b64decode(jwtpayload + '=' * (-len(jwtpayload) % 4))
    jwt_json = json.loads(jwtpayload_decoded)
    xbmc.log("waipu userhandle: "+jwt_json["userHandle"], level=xbmc.LOGDEBUG)
    license = {'merchant' : 'exaring', 'sessionId' : 'default', 'userId' : jwt_json["userHandle"]}
    license_str=base64.b64encode(json.dumps(license))
    xbmc.log("waipu license: "+license_str, level=xbmc.LOGDEBUG)
    listitem.setProperty(is_helper.inputstream_addon + '.license_key', "https://drm.wpstr.tv/license-proxy-widevine/cenc/|User-Agent="+user_agent+"&Content-Type=text%2Fxml&x-dt-custom-data="+license_str+"|R{SSM}|JBlicense")

    xbmcplugin.setResolvedUrl(_handle, True, listitem=listitem)

def play_recording(recordingid):

    is_helper = inputstreamhelper.Helper('mpd', drm='widevine')
    if not is_helper.check_inputstream():
        return False

    user_agent = "waipu-2.29.3-370e0a4-9452 (Android 8.1.0)"

    streamingData = w.playRecording(recordingid)
    for stream in streamingData["streamingDetails"]["streams"]:
        if (stream["protocol"] == 'MPEG_DASH'):
                path=stream["href"]
                if path:
                    path=path+"|User-Agent="+user_agent
                    print path
                    break

    listitem = xbmcgui.ListItem(streamingData["epgData"]["title"], path=path)
    listitem.setMimeType('application/xml+dash')
    listitem.setProperty(is_helper.inputstream_addon + ".license_type", "com.widevine.alpha")
    listitem.setProperty(is_helper.inputstream_addon + ".manifest_type", "mpd")
    listitem.setProperty('inputstreamaddon', is_helper.inputstream_addon)

    # Prepare for drm keys
    jwtheader,jwtpayload,jwtsignature = w.getToken().split(".")
    xbmc.log("waipu jwt payload: "+jwtpayload, level=xbmc.LOGDEBUG)
    jwtpayload_decoded = base64.b64decode(jwtpayload + '=' * (-len(jwtpayload) % 4))
    jwt_json = json.loads(jwtpayload_decoded)
    xbmc.log("waipu userhandle: "+jwt_json["userHandle"], level=xbmc.LOGDEBUG)
    license = {'merchant' : 'exaring', 'sessionId' : 'default', 'userId' : jwt_json["userHandle"]}
    license_str=base64.b64encode(json.dumps(license))
    xbmc.log("waipu license: "+license_str, level=xbmc.LOGDEBUG)
    listitem.setProperty(is_helper.inputstream_addon + '.license_key', "https://drm.wpstr.tv/license-proxy-widevine/cenc/|User-Agent="+user_agent+"&Content-Type=text%2Fxml&x-dt-custom-data="+license_str+"|R{SSM}|JBlicense")

    xbmcplugin.setResolvedUrl(_handle, True, listitem=listitem)

def router(paramstring):
    params = dict(parse_qsl(paramstring))
    if params:
        if params['action'] == "play-channel":
            play_channel(params['playouturl'])
        elif params['action'] == "list-channels":
            list_channels()
        elif params['action'] == "list-recordings":
            list_recordings()
        elif params['action'] == "play-recording":
            play_recording(params['recordingid'])
        else:
            # If the provided paramstring does not contain a supported action
            # we raise an exception. This helps to catch coding errors,
            # e.g. typos in action names.
            raise ValueError('Invalid paramstring: {0}!'.format(paramstring))
    else:
        get_default()


if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    router(sys.argv[2][1:])
