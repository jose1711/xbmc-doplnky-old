# -*- coding: UTF-8 -*-
#/*
# *      Copyright (C) 2013 Ivo Brhel
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

import re,urllib2,cookielib
import util,resolver

from provider import ContentProvider

class JaksetodelaContentProvider(ContentProvider):
	

	def __init__(self,username=None,password=None,filter=None):
		ContentProvider.__init__(self,'jaksetodela.cz','http://www.jaksetodela.cz/',username,password,filter)
		opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.LWPCookieJar()))
		urllib2.install_opener(opener)

	def capabilities(self):
		return ['resolve','categories','search']
		

	def search(self,keyword):
		return self.catl3(util.parse_html(self._url('search/?search_id='+keyword+'&search_type=search_videos&submit=Hledej')))
		
			
	def substr(self,data,start,end):
		i1 = data.find(start)
		i2 = data.find(end,i1+1)
		return data[i1:i2]
			
	def cat(self,page):
		"""
		top level menu - as of 2016 contains Videa, Kategorie and Rady a Tipy
		
		cat		catl2		catl3   
		Videa - 	Nejnovejsi      [video1, video2..]
				Nejsledovanejsi [video1, video2..]
                Kategorie - 	Deti a rodina	[subcat1, subcat2, .., video1, video2..]
				Dum a zahrada	[subcat1, subcat2, .., video1, video2..]
				Doprava a cestovani
		Rady a tipy -	Deti a rodina   [article1, article2..]

		"""
		result = []
		navigation = page.select('ul.topnav li[class=navigation_title]')
		for url,title in [(x.find('a')['href'],x.find('a').text) for x in navigation]:
			# skip Home
			if title in 'Home' or title in 'Rady a tipy':
				continue
			item = self.dir_item()
			item['title']=title
			item['url'] = '#catl2#'+self._url(url)
			result.append(item)
		return result

	def catl2(self,page):
		"""
		Subcategories (level2) - url prefixed with #catl2#
		"""
		result = []
		try:
			navigation = page.select('ul.topnav a[id]')[0].findParent().select('a')
		except:
			# this are most likely Rady a tipy
			navigation = page.select('div.block2 h3 a')

		for link in navigation[1:]:
			if not link.text:
				continue
			item = self.dir_item()
			item['title']=link.text
			item['url'] = "#catl3#"+self._url(link['href'])
			result.append(item)
		return result

	def catl3(self,page):
		"""
		List of movies  - url prefixed with #catl3#
		"""
		result = []
		try:
			# kategorie
			navigation = page.select('div.block-padding-lg')[0].select('div')[1].select('div a')
		except IndexError:
			# videa
			navigation = page.select('div.video_thumb_watch a')

		subcategories = page.select('ul[id=subcategory-list] a')
		for subcategory in subcategories:
			item = self.dir_item()
			if subcategory.parent.get('class') == ['selected']:
				item['title']='[COLOR red]%s[/COLOR]' % subcategory.text
			else:
				item['title']='[COLOR yellow]%s[/COLOR]' % subcategory.text
			item['url']="#catl3#"+self._url(subcategory['href'])
			result.append(item)

		for vitem in [x for x in navigation if x.img]:
			item = self.video_item()
			item['img'] = vitem.img['src']
			item['title'] = vitem['title']
			item['url'] = self._url(vitem['href'])
			result.append(item)

		if page.select('a.prevChar'):
			item = self.dir_item()
			item['type'] = 'prev'
			item['url'] = '#catl3#'+self._url(page.select('a.prevChar')[0]['href'])
			result.append(item)

		if page.select('a.nextChar'):
			item = self.dir_item()
			item['type'] = 'next'
			item['url'] = '#catl3#'+self._url(page.select('a.nextChar')[0]['href'])
			result.append(item)

		return result
		
	
	def categories(self):
		result = []
		
		item = self.dir_item()
		item['type'] = 'new'
		item['url']  = '#last#'+self._url('videos/basic/mr')
		result.append(item)
		result.extend(self.cat(util.parse_html(self._url('videos'))))
		
		return result
	
	
	def list(self,url):
		if url.find('#cat#') == 0:
			return self.cat(util.parse_html(self._url(url[5:])))
		if url.find('#catl2#') == 0:
			return self.catl2(util.parse_html(self._url(url[7:])))
		if url.find('#catl3#') == 0:
			return self.catl3(util.parse_html(self._url(url[7:])))
		if url.find('#last#') == 0:
			return self.catl3(util.parse_html(self._url(url[6:])))
		else:
			raise Exception("Invalid url, I do not know how to list it :"+url)

	def resolve(self,item,captcha_cb=None,select_cb=None):
		item = item.copy()
		url = self._url(item['url'])
		print 'URL: '+url
		data = util.request(url)
		
		pattern = 'videoId: \'(?P<vid>.+?)[\'?]'
		m = re.search(pattern, data, re.IGNORECASE | re.DOTALL)
		if not m == None:
			url = 'http://www.youtube.com/watch?v='+m.group('vid')
		
		resolved = resolver.findstreams(url,['(?P<url>http://www.youtube.com/watch\?v='+m.group('vid')+')'])
		result = []
		try:
			for i in resolved:
				item = self.video_item()
				item['title'] = i['name']
				item['url'] = i['url']
				item['quality'] = i['quality']
				item['surl'] = i['surl']
				result.append(item)  
		except:
			print '===Unknown resolver==='
			
		if len(result)==1:
			return result[0]
		elif len(result) > 1 and select_cb:
			return select_cb(result)
