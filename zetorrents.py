# -*- coding: utf-8 -*-
# VERSION: 1.00
# AUTHORS: alexandre-eliot <alexandre.eliot@outlook.com>
# INSPIRED BY THE WORK OF
# sa3dany, Alyetama, BurningMop, scadams
# Yun (chenzm39@gmail.com)

# LICENSING INFORMATION
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from html.parser import HTMLParser

from novaprinter import prettyPrinter
from helpers import retrieve_url, download_file


class zetorrents(object):
    """
    `url`, `name`, `supported_categories` should be static variables of the engine_name class,
     otherwise qbt won't install the plugin.

    `url`: The URL of the search engine.
    `name`: The name of the search engine, spaces and special characters are allowed here.
    `supported_categories`: What categories are supported by the search engine and their corresponding id,
    possible categories are ('all', 'anime', 'books', 'games', 'movies', 'music', 'pictures', 'software', 'tv').
    """

    url = 'https://zetorrents.com'
    name = 'ZeTorrents'

    supported_categories = {
        'all': None,
        'anime': 'animation',
        'books': 'ebooks',
        'games': 'jeux-pc',
        'movies': 'films',
        'music': 'musique',
        'tv': 'series',
    }

    RESULTS_PER_PAGE = 100
    MAX_PAGES_LOOKUP = 10

    class zeTorrentsParser(HTMLParser):
        """Parses acg.rip browse page for search results and stores them."""
        
        def __init__(self, infos, url):
            """
            Construct a zeTorrents html parser.

            Parameters:
            :param list res: a list to store the results in @deprecated
            :param infos: an object to retrieve informations about the page
            :param str url: the base url of the search engine
            """
            
            try:
                super().__init__()
            except TypeError:
                #  See: http://stackoverflow.com/questions/9698614/
                HTMLParser.__init__(self)

            self.NB_OF_COLUMNS = 5

            self.page_infos = infos
              
            self.engine_url = url
            self.results = []
            self.row = {}

            self.is_inside_row = False
            self.is_found_content = False
            self.is_found_table = False

            self.td_counter = -1
            self.span_counter = -1
            self.a_counter = -1

            # Page number indicators to determine when to stop iterating
            # through result pages
            self.is_in_pages_div = False
            self.has_more_pages_after = True
            self.is_in_page_number_span = False
            self.is_page_number_a = False

        def handle_starttag(self, tag, attrs):
            params = dict(attrs)

            if 'content-list-torrent' in params.get('class'):
                self.is_found_content = True
                return

            if self.is_found_content and tag == 'tbody':
                self.is_found_table = True
                return

            if self.is_found_table and tag == 'tr':
                self.is_inside_row = True
                return

            if self.is_inside_row and tag == 'td':
                self.td_counter += 1
                return
        
            if self.is_inside_row and self.td_counter > -1 and tag == 'span':
                self.span_counter += 1
                return

            if self.is_inside_row and self.td_counter > -1 and tag == 'a':
                self.a_counter += 1

                if self.td_counter == 0:

                    if 'href' not in params:
                        return
                    
                    href = params['href']

                    if href.startswith('/torrents/'):
                        link = f'{self.engine_url}{href}'
                        self.row['link'] = link
                        self.row['engine_url'] = self.engine_url
                        self.row['desc_link'] = link

                return

            if 'pages' in params.get('class'):
                self.is_in_pages_div = True
                return

            if self.is_in_pages_div and params.get('rel') == 'next':
                self.has_more_pages_after = False
                return

            if self.is_in_pages_div \
            and tag == 'span' \
            and 'nextPrev' not in params.get('class'):
                self.is_in_page_number_span = True
                return

            if self.is_in_page_number_span and tag == 'a':
                self.is_page_number_a = True

        def handle_torrent_data(self, data):
            if self.td_counter > -1 \
            and self.td_counter < self.NB_OF_COLUMNS:

                match self.td_counter:
                    # Catch the name
                    case 1:
                        if self.a_counter == 0:
                            self.row['name'] = data.strip()

                    # Catch the size
                    case 2:
                        if self.a_counter == 0:
                            self.row['size'] = data.strip()

                    # Catch the seeds
                    case 3:
                        if self.span_counter == 0:
                            try:
                                self.span_counter += 2
                                self.row['seeds'] = int(data.strip())
                            except ValueError:
                                self.row['seeds'] = -1

                    # Catch the leeches
                    case 4:
                        if self.span_counter == 0:
                            try:
                                self.span_counter += 2
                                self.row['leech'] = int(data.strip())
                            except ValueError:
                                self.row['leech'] = -1

        def handle_page_number_data(self, data):
            if not self.has_more_pages_after \
            and self.is_page_number_a:
                page_count = int(data.strip())    
                
                if page_count > self.page_infos.max_pages_count:
                    self.page_infos.max_pages_count = int(data.strip())

        def handle_data(self, data):
            self.handle_torrent_data(data)                
            self.handle_page_number_data(data)

        def handle_endtag(self, tag):
            if tag == 'table':

                self.is_found_content = False
                self.is_found_table = False

            if self.is_inside_row and tag == 'tr':
                self.is_inside_row = False
                self.td_counter = -1
                
                array_length = len(self.row)
                if array_length < 1:
                    return
                
                self.page_infos.hit_count += 1
                
                prettyPrinter(self.row)
                self.row = {}

            if self.is_in_pages_div and tag == 'div':
                self.is_in_pages_div = False
                        
            if self.is_in_page_number_span and tag == 'span':
                self.is_in_page_number_span = False
                self.is_page_number_a = False

            if self.span_counter > -1 and tag == 'span':
                self.span_counter -= 1
            
            if self.a_counter > -1 and tag == 'a':
                self.a_counter -= 1

    def download_torrent(self, info):
        print(download_file(info))
        
    def build_url(self, url, query, category=None, page=1):
        page_url = f'{url}/torrents/find/'

        if category:
            page_url += f'1/${category}/'
    
        return f'${page_url}:${page}?title={query}'

    # DO NOT CHANGE the name and parameters of this function
    # This function will be the one called by nova2.py
    def search(self, what, cat='all'):
        """
        Retreive and parse engine search results by category and query.

        Parameters:
        `what` is a string with the search tokens, already escaped (e.g. "Ubuntu+Linux")
        `cat` is the name of a search category in ('all', 'anime', 'books', 'games', 'movies', 'music', 'pictures', 'software', 'tv')
        """
        
        category = self.supported_categories[cat]

        page_infos = {
            'hit_count': 0,
            'max_pages_count': -1,
        }

        parser = self.zeTorrentsParser(page_infos, self.url)

        page_index = 1

        while True:
            page_url = self.build_url(self.url, what, category, page_index)
            html = retrieve_url(page_url)
            parser.feed(html)

            max_pages_count = self.MAX_PAGES_LOOKUP
            
            if page_infos.max_pages_count > -1:
                max_pages_count = page_infos.max_pages_count

            if (
                page_infos.hit_count < self.RESULTS_PER_PAGE
                or page_index >= max_pages_count
            ): break

            page_infos.hit_count = 0

            page_index += 1

        parser.close()