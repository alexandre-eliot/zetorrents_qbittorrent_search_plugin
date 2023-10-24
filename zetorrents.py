# -*- coding: utf-8 -*-
# VERSION: 1.11
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

import re
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

    url = 'https://www.zetorrents.com'
    name = 'ZeTorrents'

    supported_categories = {
        'all': [None],
        'anime': ['animation'],
        'books': ['ebooks'],
        'games': ['jeux-pc', 'jeux-consoles'],
        'movies': ['films'],
        'music': ['musique'],
        'tv': ['series'],
    }

    RESULTS_PER_PAGE = 100

    class zeTorrentsParser(HTMLParser):
        """Parses zetorrents.com browse page for search results and stores them."""
        
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
            self.torrent_infos = {}

            self.is_found_content = False

            self.td_counter = -1
            self.span_counter = -1
            self.a_counter = -1

        def get_torrent_url_from_page_url(self, page_url):
            torrent_page = retrieve_url(page_url)
            torrent_regex = r'href="\/downloads\/torrentFile\/.*\.torrent"'
            matches = re.finditer(torrent_regex, torrent_page, re.MULTILINE)
            torrent_urls = [x.group() for x in matches]

            if len(torrent_urls) > 0:
                return torrent_urls[0].split('"')[1]

            return None
        
        def handle_starttag(self, tag, attrs):
            params = dict(attrs)

            if params.get('class') == 'content-list-torrent':
                self.is_found_content = True

            elif self.is_found_content:

                if tag == 'tr':
                    self.print_torrent_infos_and_reinit_row()

                elif tag == 'td':
                    self.td_counter += 1

                elif self.td_counter > -1:
                            
                    if tag == 'span':
                        self.span_counter += 1

                    elif tag == 'a':
                        self.a_counter += 1

                        if self.td_counter == 0:

                            if 'href' not in params:
                                return
                            
                            href = params['href']

                            if href.startswith('/torrents/'):
                                link = f'{self.engine_url}{href}'

                                torrent_url = self.get_torrent_url_from_page_url(link)

                                if torrent_url:
                                    self.torrent_infos['link'] = self.engine_url + torrent_url
                                    self.torrent_infos['engine_url'] = self.engine_url
                                    self.torrent_infos['desc_link'] = link


        def handle_torrent_data(self, data):
            if (
                self.td_counter > 0  # We skip the first "td"
                and self.td_counter < self.NB_OF_COLUMNS
            ):

                match self.td_counter:
                    # Catch the name
                    case 1:
                        if self.a_counter == 0:
                            self.torrent_infos['name'] = data.strip()

                    # Catch the size
                    case 2:
                        if self.span_counter == 0:
                            self.torrent_infos['size'] = unit_fr2en(data.strip())

                    # Catch the seeds
                    case 3:
                        if self.span_counter == 0:
                            try:
                                self.torrent_infos['seeds'] = int(data.strip())
                            except ValueError:
                                self.torrent_infos['seeds'] = -1

                    # Catch the leeches
                    case 4:
                        if self.span_counter == 0:
                            try:
                                self.torrent_infos['leech'] = int(data.strip())
                            except ValueError:
                                self.torrent_infos['leech'] = -1

        def handle_data(self, data):
            self.handle_torrent_data(data)                
        
        def print_torrent_infos_and_reinit_row(self):
            self.td_counter = -1

            array_length = len(self.torrent_infos)

            if array_length < 1:
                return

            self.page_infos['hit_count'] += 1
            
            prettyPrinter(self.torrent_infos)
            
            self.torrent_infos = {}

        def handle_endtag(self, tag):
            if self.is_found_content and tag == 'table':
                # Because we are printing out the previous torrent infos on
                # detecting a `td` tag, we need to try and print out the last
                # torrent's infos right before the end of the table
                self.print_torrent_infos_and_reinit_row()
                self.is_found_content = False

            elif self.td_counter > -1:
                if self.span_counter > -1 and tag == 'span':
                    self.span_counter -= 1
            
                elif self.a_counter > -1 and tag == 'a':
                    self.a_counter -= 1
        
    def build_url(self, url, query, category=None, page=1):
        page_url = f'{url}/torrents/find/'

        if category:
            page_url += f'1/{category}/'
    
        return f'{page_url}:{page}?title={query}'

    # DO NOT CHANGE the name and parameters of this function
    # This function will be the one called by nova2.py
    def search(self, what, cat='all'):
        """
        Retreive and parse engine search results by category and query.

        Parameters:
        `what` is a string with the search tokens, already escaped (e.g. "Ubuntu+Linux")
        `cat` is the name of a search category in ('all', 'anime', 'books', 'games', 'movies', 'music', 'pictures', 'software', 'tv')
        """
        
        categories = self.supported_categories[cat]

        page_infos = {
            'hit_count': 0,
        }

        parser = self.zeTorrentsParser(page_infos, self.url)

        for category in categories:

            page_index = 1

            while True:
                
                page_url = self.build_url(self.url, what, category, page_index)
                
                html = retrieve_url(page_url)

                # Trying to find the page arrow to know if
                # we should carry on iterating
                right_arrow_regex = r'<a\s*href=".*"\s*rel="next"\s*>><\/a>'
                is_last_page = len(re.findall(right_arrow_regex, html)) > 0

                parser.feed(html)

                if (
                    not is_last_page
                    or page_infos['hit_count'] < self.RESULTS_PER_PAGE
                ): break

                page_infos['hit_count'] = 0

                page_index += 1

        parser.close()

def unit_fr2en(size):
    """Convert french size unit to english unit"""
    return re.sub(
        r'([KMGTP])o',
        lambda match: match.group(1) + 'B',
        size, flags=re.IGNORECASE
    )