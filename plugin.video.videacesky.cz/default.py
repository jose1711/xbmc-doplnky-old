# -*- coding: UTF-8 -*-
#/*
# *      Copyright (C) 2011 Libor Zoubek
# *
# *
# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with this program; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *
# */

import re,os,urllib
import xbmcaddon,xbmc,xbmcgui,xbmcplugin
import util,resolver
import youtuberesolver as youtube

__scriptid__   = 'plugin.video.videacesky.cz'
__scriptname__ = 'videacesky.cz'
__addon__      = xbmcaddon.Addon(id=__scriptid__)
__language__   = __addon__.getLocalizedString

BASE_URL='http://www.videacesky.cz'

def categories():
	data = util.request(BASE_URL)
	data = util.substr(data,'<ul id=\"headerMenu2\">','</ul>')
	pattern = '<a href=\"(?P<url>[^\"]+)(.+?)>(?P<name>[^<]+)'
	for m in re.finditer(pattern, data, re.IGNORECASE | re.DOTALL ):
		util.add_dir(m.group('name'),{'cat':m.group('url')})

def list_content(page):
	data = util.substr(page,'<div class=\"contentArea','<div class=\"pagination\">')
	pattern = '<h\d class=\"postTitle\"><a href=\"(?P<url>[^\"]+)(.+?)<span>(?P<name>[^<]+)</span></a>(.+?)<div class=\"postContent\">[^<]+<a[^>]+[^<]+<img src=\"(?P<img>[^\"]+)'
	for m in re.finditer(pattern, data, re.IGNORECASE | re.DOTALL ):
		util.add_video(m.group('name'),{'play':m.group('url')},m.group('img'))
	data = util.substr(page,'<div class=\"pagination\">','</div>')
	m = re.search('<li class=\"info\"><span>([^<]+)',data)
	n = re.search('<li class=\"prev\"[^<]+<a href=\"(?P<url>[^\"]+)[^<]+<span>(?P<name>[^<]+)',data)
	k = re.search('<li class=\"next\"[^<]+<a href=\"(?P<url>[^\"]+)[^<]+<span>(?P<name>[^<]+)',data)
	if not m == None:
		if not n == None:
			util.add_dir('%s - %s' % (m.group(1),n.group('name')),{'cat':n.group('url')})
		if not k == None:
			util.add_dir('%s - %s' % (m.group(1),k.group('name')),{'cat':k.group('url')})
	
def play(url):
	data = util.substr(util.request(url),'<div class=\"postContent\"','</div>')
	m = re.search('file=(?P<url>[^\&]+)',data,re.IGNORECASE | re.DOTALL)
	if not m == None:
		youtube.__eurl__ = 'http://www.videacesky.cz/wp-content/plugins/jw-player-plugin-for-wordpress/player.swf'
		streams = resolver.resolve(m.group('url'))
		if not streams == None and len(streams)>0:
			stream = streams[0]
			print 'Sending %s to player' % stream
			li = xbmcgui.ListItem(path=stream,iconImage='DefaulVideo.png')
			return xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, li)
	print 'not resolved'
		

p = util.params()
if p=={}:
	categories()
	xbmcplugin.endOfDirectory(int(sys.argv[1]))
if 'cat' in p.keys():
	list_content(util.request(p['cat']))
	xbmcplugin.endOfDirectory(int(sys.argv[1]))
if 'play' in p.keys():
	play(p['play'])