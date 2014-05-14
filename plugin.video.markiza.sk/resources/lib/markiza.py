# -*- coding: UTF-8 -*-
# /*
# *      Copyright (C) 2014 Maros Ondrasek
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

import re
import urllib
import urllib2
import cookielib

import util
from provider import ContentProvider

CATEGORIES_START = '<div class="col-left">'
CATEGORIES_END = '<div class="col-middle">'
CATEGORIES_ITER_RE = '<li class=\"(?P<type>[^\"]+)\">\s+<a href=\"(?P<url>[^\"]+)\" title=\"(?P<title>[^\"]+)\">.+?</a>\s*</li>'
LISTING_START = CATEGORIES_END
LISTING_END = '<div class="footer">'
LISTING_ITER_RE = """
    <div\ class=\"item\">\s*
        <div\ class=\"image\">.+?<img.+?src=\"(?P<img>[^\"]+)\"\ />.+?</div>\s*
        <div\ class=\"text\">\s*
            <h2><a\ href=\"(?P<url>[^\"]+)\">(?P<title>[^<]+)</a></h2>\s*
            <div\ class=\"info\">\s*
                <div\ class=\"section\">.+?<a\ href=\"(?P<section_url>[^\"]+)\">(?P<section_title>[^<]+)</a></div>\s*
                <div\ class=\"length\">.+?(?P<length>\d{2}:\d{2}:\d{2})</div>\s*
                <div\ class=\"date\">.+?(?P<date>\d{1,2}[^<]+)</div>\s*
            </div>
"""
PAGER_START = '<div class="paging">'
PAGER_END = '</div>'
PAGE_NEXT_RE = '<a\s+href=\"(?P<url>[^\"]+)\".+?id=\"video_list_fwd\">.+?</a>'
PAGE_PREV_RE = '<a\s+href=\"(?P<url>[^\"]+)\".+?id=\"video_list_back\">.+?</a>'

class MarkizaContentProvider(ContentProvider):

    def __init__(self, username=None, password=None, filter=None, tmp_dir='/tmp'):
        ContentProvider.__init__(self, 'videoarchiv.markiza.sk', 'http://videoarchiv.markiza.sk', username, password, filter, tmp_dir)
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.LWPCookieJar()))
        urllib2.install_opener(opener)

    def capabilities(self):
        return ['categories', 'resolve']

    def list(self, url):
        if url.find('#subcat#') == 0:
            url = url[8:]
            return self.list_subcategories(util.request(self._url(url)), url)
        return self.list_content(util.request(self._url(url)))

    def categories(self):
        result = []
        item = self.dir_item()
        item['type'] = 'new'
        item['url'] = 'najnovsie'
        result.append(item)
        data = util.request(self.base_url)
        data = util.substr(data, CATEGORIES_START, CATEGORIES_END)
        for m in re.finditer(CATEGORIES_ITER_RE, data, re.IGNORECASE | re.DOTALL):
            if m.group('type').strip() == 'child':
                continue
            item = self.dir_item()
            item['title'] = m.group('title')
            if m.group('type').strip() == 'has-child':
                item['url'] = "#subcat#" + m.group('url')
            else:
                item['url'] = m.group('url')
            self._filter(result, item)
        return result

    def list_subcategories(self, page, category_name):
        result = []
        data = util.substr(page, CATEGORIES_START, CATEGORIES_END)
        data = util.substr(data, category_name, CATEGORIES_END)
        for m in re.finditer(CATEGORIES_ITER_RE, data, re.IGNORECASE | re.DOTALL):
            if m.group('type').strip() != 'child':
                break
            item = self.dir_item()
            item['title'] = m.group('title')
            item['url'] = m.group('url')
            self._filter(result, item)
        return result

    def list_content(self, page):
        result = []
        data = util.substr(page, LISTING_START, LISTING_END)
        for m in re.finditer(LISTING_ITER_RE, data, re.DOTALL | re.VERBOSE):
            item = self.video_item()
            item['title'] = "%s - (%s)" % (m.group('title').strip(), m.group('date').strip())
            item['img'] = m.group('img')
            item['url'] = m.group('url')
            self._filter(result, item)
        data = util.substr(page, PAGER_START, PAGER_END)
        p = re.search(PAGE_PREV_RE, data, re.DOTALL)
        n = re.search(PAGE_NEXT_RE, data, re.DOTALL)
        if p:
            item = self.dir_item()
            item['type'] = 'prev'
            item['url'] = p.group('url')
            result.append(item)
        if n:
            item = self.dir_item()
            item['type'] = 'next'
            item['url'] = n.group('url')
            result.append(item)
        return result


    def resolve(self, item, captcha_cb=None, select_cb=None):
        result = []
        item = item.copy()
        urlpart = item['url'].split('/')[-1] or item['url'].split('/')[-2]
        video_id = re.search("(\d+)\_", urlpart).group(1)
        videodata = util.json.loads(util.request('http://www.markiza.sk/json/video.json?id=' + video_id))
        for v in videodata['playlist']:
            for b in v['bitrates']:
                 item = self.video_item()
                 item['title'] = v['title']
                 item['url'] = "%s playpath=%s" % (v['netConnectionUrl'], b['url'])
                 item['surl'] = v['title']
                 item['quality'] = b['label']
                 item['length'] = b['length']
                 item['size'] = b['size']
                 result.append(item)
        if len(result) > 0 and select_cb:
            return select_cb(result)
        return result