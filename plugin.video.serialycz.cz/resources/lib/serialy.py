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
import urllib2,re,os,sys,cookielib
import util,resolver
from provider import ContentProvider
from provider import cached
class SerialyczContentProvider(ContentProvider):

    def __init__(self,username=None,password=None,filter=None,tmp_dir='.'):
        ContentProvider.__init__(self,'serialycz.cz','http://www.serialycz.cz/',username,password,filter,tmp_dir)
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.LWPCookieJar()))
        urllib2.install_opener(opener)

    def capabilities(self):
        return ['resolve','categories']


    def categories(self):
        result = []
        item = self.dir_item()
        item['type'] = 'new'
        item['url'] = 'category/new-episode'
        result.append(item)
        data = util.substr(util.request(self.base_url),'<div id=\"primary\"','<div id=\"secondary')
        pattern='<a href=\"(?P<url>[^\"]+)[^>]+>(?P<name>[^<]+)</a>'	
        for m in re.finditer(pattern, util.substr(data,'Seriály</a>','</ul>'), re.IGNORECASE | re.DOTALL):
            item = self.dir_item()
            item['title'] = m.group('name')
            item['url'] = m.group('url')
            result.append(item)
        return result

    def new_episodes(self,page):
        result = []
        data = util.substr(page,'<div id=\"archive-posts\"','</ul>')
        pattern='<img(.+?)src=\"(?P<img>[^\"]+)(.+?)<a href=\"(?P<url>[^\"]+)[^>]+>(?P<name>[^<]+)</a>'	
        for m in re.finditer(pattern, data, re.IGNORECASE | re.DOTALL):
            name = util.decode_html(m.group('name'))
            item = self.video_item()
            item['url'] = m.group('url')
            item['title'] = name
            item['img'] = m.group('img')
            self._filter(result,item)
        return result

    def list(self,url):
        if url.find('category/new-episode') == 0:
            return self.new_episodes(util.request(self._url(url)))
        result = []
        page = util.request(self._url(url))
        data = util.substr(page,'<div id=\"archive-posts\"','</div>')
        m = re.search('<a(.+?)href=\"(?P<url>[^\"]+)', data, re.IGNORECASE | re.DOTALL)
        if m:
            data = util.request(m.group('url'))
            for m in re.finditer('<a href=\"(?P<url>[^\"]+)(.+?)(<strong>|<b>)(?P<name>[^<]+)', util.substr(data,'<div class=\"entry-content','</div>'), re.IGNORECASE | re.DOTALL):
                item = self.video_item()
                item['title'] = util.decode_html(m.group('name'))
                item['url'] = m.group('url')
                self._filter(result,item)
        return result

    def resolve(self,item,captcha_cb=None,select_cb=None):
        item = item.copy()
        url = self._url(item['url']).replace('×', '%c3%97')
        data = util.substr(util.request(url), '<div id=\"content\"', '#content')
        
        for script in re.finditer('<script.+?src=\"([^\"]+)',data,re.IGNORECASE|re.DOTALL):
            try:
                data += util.request(script.group(1)).replace('\\\"','\"')
            except:
                pass
        util.init_urllib() # need to reinitialize urrlib, because anyfiles could have left some cookies 
        visionone_resolved, onevision_resolved, scz_resolved = [],[],[]
        
        onevision = re.search('(?P<url>http://onevision\.ucoz\.ua/[^<]+)', data, re.IGNORECASE)
        if onevision:
            onevision_data = util.substr(util.request(onevision.group('url')),'<td class=\"eText\"','<td class=\"rightColumn\"')
            onevision_resolved=self.findstreams(onevision_data, ['<embed( )src=\"(?P<url>[^\"]+)',
                                                  '<object(.+?)data=\"(?P<url>[^\"]+)',
                                                  '<iframe(.+?)src=[\"\'](?P<url>.+?)[\'\"]',
                                                  '<object.*?data=(?P<url>.+?)</object>'])
        
        visionone = re.search('(?P<url>http://visionone\.ucoz\.ru/[^<]+)', data, re.IGNORECASE)
        if visionone:
            visionone_data = util.substr(util.request(visionone.group('url')),'<td class=\"eText\"','<td class=\"rightColumn\"')
            visionone_resolved = self.findstreams(visionone_data, ['<embed( )src=\"(?P<url>[^\"]+)',
                                                  '<object(.+?)data=\"(?P<url>[^\"]+)',
                                                  '<iframe(.+?)src=[\"\'](?P<url>.+?)[\'\"]',
                                                  '<object.*?data=(?P<url>.+?)</object>'])
        scz = re.search('(?P<url>http://scz\.uvadi\.cz/\?p=[\d]+)', data, re.IGNORECASE)
        if scz:
            scz_data = util.substr(util.request(scz.group('url')),'<div id=\"content\"', '#content')
            scz_resolved = self.findstreams(scz_data, ['<embed( )src=\"(?P<url>[^\"]+)',
                                                  '<object(.+?)data=\"(?P<url>[^\"]+)',
                                                  '<iframe(.+?)src=[\"\'](?P<url>.+?)[\'\"]',
                                                  '<object.*?data=(?P<url>.+?)</object>'])
            
        serialy_resolved = self.findstreams(data, ['<embed( )src=\"(?P<url>[^\"]+)',
                                               '<object(.+?)data=\"(?P<url>[^\"]+)',
                                               '<iframe(.+?)src=[\"\'](?P<url>.+?)[\'\"]',
                                               '<object.*?data=(?P<url>.+?)</object>',
                                               '<p><code><strong>(?P<url>http.+?)</strong></code></p>',
                                               '<p><code><strong><big>(?P<url>.+?)</big></strong></code></p>'])
        
        resolved = []
        resolved+= serialy_resolved or []
        resolved+= visionone_resolved or []
        resolved+= onevision_resolved or []
        resolved+= scz_resolved or []
        resolved = len(resolved) > 0 and resolved or None
        
        if len(resolved) == 1:
            return resolved[0]
        elif len(resolved) > 1 and select_cb:
            return select_cb(resolved)


