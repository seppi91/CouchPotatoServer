# -*- coding: utf-8 -*-
import json
import re
import urllib
import time
import datetime
from couchpotato.core.helpers.variable import tryInt

from couchpotato.core.media._base.providers.och.base import OCHProvider
from couchpotato.core.helpers.encoding import simplifyString, handle_special_chars
from couchpotato.core.logger import CPLog
from bs4 import BeautifulSoup

log = CPLog(__name__)


class Base(OCHProvider):
    urls = {
        'search': 'http://hd-world.org/index.php?s=%s',
    }

    def _searchOnTitle(self, title, movie, quality, results):
        #Nach Lokalem Titel (abh. vom def. Laendercode) und original Titel suchen
        alt_titles = movie['info'].get('alternate_titles', [])
        titles = []
        titles.extend(alt_titles);
        titles.append(title)
        for title in titles:
            self.do_search(simplifyString(handle_special_chars(title)), results)
        if not results:
            shortenedAltTitles = []
            # trying to delete original title string from alt title string
            for alt_title in alt_titles:
                if alt_title != title and title in alt_title:
                    shortenedAltTitle = simplifyString(alt_title).replace(simplifyString(title), "")
                    if shortenedAltTitle != "":
                        self.do_search(shortenedAltTitle, results)


    def do_search(self, title, results):
        query = '%s' % (urllib.quote_plus(title))
        searchUrl = self.urls['search'] % query

        log.debug('fetching data from %s' % searchUrl)

        #TODO: Search result has more than one page <vorwaerts> link
        data = self.getHTMLData(searchUrl)

        linksToMovieDetails = self.parseSearchResult(data)
        for movieDetailLink in linksToMovieDetails:
            log.debug("fetching data from Movie's detail page %s" % movieDetailLink)
            data = self.getHTMLData(movieDetailLink)
            result = self.parseMovieDetailPage(data)
            if len(result):
                results.append(result)
        return len(linksToMovieDetails)


    #===============================================================================
    # INTERNAL METHODS
    #===============================================================================

    def parseInfo(self, info):
        def _getDateObject(day, month, year):
            months = ["januar", "februar", "märz", "april", "mai", "juni", "juli", "august", "september", "oktober", "november", "dezember"]
            try:
                month = months.index(month.lower()) + 1
                return datetime.date(tryInt(year), month, tryInt(day))
            except:
                raise

        parsed = re.search("Datum:\s(?P<date>\w+,\s\d\d?.\s\w+\s\d{4})", info.p.text, re.UNICODE)

        try:
            relDateString = parsed.group('date')
            day = relDateString.split(" ")[1][:-1]
            month = relDateString.split(" ")[2]
            year = relDateString.split(" ")[3]
            relDate = _getDateObject(day, month, year)
        except AttributeError, e:
            relDate = None
            log.error("error while parsing date.")

        return {
            'age':  (datetime.date.today() - relDate).days if relDate is not None else 0,
        }


    def parsePost(self, post):
        captionElem = post.find("h2", id=re.compile(r"post-[0-9]{6}"))
        id = captionElem["id"].split("-")[1]
        title = captionElem.text

        entry = post.find(attrs={"class": "entry"}, recursive=False)

        size_raw = str(entry.find('strong', text=re.compile(u'Größe:\s?', re.UNICODE)).nextSibling).strip()
        size = self.parseSize(size_raw.replace(',', '.'))

        #release = str(post.find('strong', text='Release:').nextSibling).strip()

        url = []
        download = entry.find('strong', text=re.compile("Download:?\s?")).findNextSibling('a')
        hoster = download.text
        for acceptedHoster in self.conf('hosters').replace(' ', '').split(','):
            if acceptedHoster in hoster.lower():
                url.append(download["href"])

        for i in xrange(1, 5):  #support up to 5 mirrors
            for mirrorTxt in entry.findAll('strong', text=re.compile('Mirror #?%i:?\s?' % i)):
                hoster = mirrorTxt.findNextSibling('a').text
                for acceptedHoster in self.conf('hosters').replace(' ', '').split(','):
                    if acceptedHoster in hoster.lower():
                        url.append(mirrorTxt.findNextSibling('a')["href"])

        return {"id": id,
                "name": title,
                "size": size,
                "url": json.dumps(url)}

    def parseMovieDetailPage(self, data):
        dom = BeautifulSoup(data)
        content = dom.find(id='content')

        post = content.find(attrs={"class": "post"}, recursive=False)
        info = content.find(id="info", recursive=False)

        try:
            postContent = self.parsePost(post)
            infoContent = self.parseInfo(info)
        except:
            postContent = {}
            infoContent = {}
            # :TODO something is wrong here - but usually it works as expected
            log.error("something went wrong when parsing post of release.")

        res = {}
        res.update(postContent)
        res.update(infoContent)
        res["pwd"] = "hd-world.org"  # hardcoded, is static on hd-world.org page
        return res

    def parseSearchResult(self, data):
        #print data
        try:
            dom = BeautifulSoup(data)

            content = dom.find(id='archiv')

            linksToMovieDetails = []
            for link in content.findAll('h1', id=re.compile(r"post-[0-9]{6}"), recursive=True):
                linksToMovieDetails.append(link.a['href'])
            num_results = len(linksToMovieDetails)
            log.info('Found %s %s on search.', (num_results, 'release' if num_results == 1 else 'releases'))
            return linksToMovieDetails
        except:
            log.debug('There are no search results to parse!')
            return []


config = [{
              'name': 'hdworld',
              'groups': [
                  {
                      'tab': 'searcher',
                      'list': 'och_providers',
                      'name': 'HD-World',
                      'description': 'See <a href="https://www.hd-world.org">HD-World.org</a>. Less accurate!',
                      'wizard': True,
                      'options': [
                          {
                              'name': 'enabled',
                              'type': 'enabler',
                          },
                          {
                              'name': 'extra_score',
                              'advanced': True,
                              'label': 'Extra Score',
                              'type': 'int',
                              'default': 0,
                              'description': 'Starting score for each release found via this provider.',
                          },
                          {
                              'name': 'hosters',
                              'label': 'accepted Hosters',
                              'default': '',
                              'placeholder': 'Example: uploaded,share-online',
                              'description': 'List of Hosters separated by ",". Should be at least one!'
                          },
                      ],
                  },
              ],
          }]