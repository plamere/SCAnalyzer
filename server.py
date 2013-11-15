import os 
import cherrypy
import ConfigParser
import urllib2
import json
import pyen
import requests
import webtools
import pprint
import atexit

class SCAnalyzer(object):
    def __init__(self, config):
        self.sc_client_id = "72f69b27f62dd38d1fa075a898e5d9a1"
        self.en = pyen.Pyen()
        self.cache = {}
        atexit.register(self.save)
        self.load()

    def analyze(self, id, callback=None, _=''):
        if callback:
            cherrypy.response.headers['Content-Type']= 'text/javascript'
        else:
            cherrypy.response.headers['Content-Type']= 'application/json'
        print id
        if id in self.cache:
            result = { 'status' : 'OK',  'trid': self.cache[id]}
        else:
            if id.find('http') >= 0:
                js = self.resolve(id)
            else:
                url = 'http://api.soundcloud.com/tracks/%s.json?client_id=%s' % (id, self.sc_client_id)
                r = requests.get(url)
                js = r.json()

            if 'stream_url' in js:
                url = js['stream_url'] + '?client_id=' + self.sc_client_id
                result = self.en.post('track/upload',url=url)
                if result['status']['code'] == 0:
                    trid = result['track']['id']
                    self.add_entry(js, trid)
                    result = { 'status' : 'OK',  'trid': trid}
            else :
                result = { 'status' : 'ERROR',  'message': 'no audio'}
        return webtools.to_json(result, callback)
    analyze.exposed=True

    def resolve(self, url):
        url = 'http://api.soundcloud.com/resolve.json?url=%s&client_id=%s' % (url, self.sc_client_id)
        r = requests.get(url)
        return r.json()

    def add_entry(self, js, trid):
        url = js['permalink_url']
        surl = url.replace('http:', 'https:')
        self.cache[surl] = trid
        self.cache[js['permalink']] = trid
        self.cache[js['permalink_url']] = trid
        self.cache[js['uri']] = trid
        self.cache[js['id']] = trid

    def save(self):
        print "saving", len(self.cache), "items to sc.cache"
        js = json.dumps(self.cache)
        f = open("sc.cache", "w")
        print >>f, js
        f.close()

    def load(self):
        f = open("sc.cache", "r")
        js = f.read()
        f.close()
        self.cache = json.loads(js)
        

if __name__ == '__main__':
    urllib2.install_opener(urllib2.build_opener())

    conf_path = os.path.abspath('web.conf')
    print 'reading config from', conf_path
    cherrypy.config.update(conf_path)

    config = ConfigParser.ConfigParser()
    config.read(conf_path)
    production_mode = config.getboolean('settings', 'production')

    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Set up site-wide config first so we get a log if errors occur.

    if production_mode:
        print "Starting in production mode"
        cherrypy.config.update({'environment': 'production',
                                'log.error_file': 'simdemo.log',
                                'log.screen': True})
    else:
        print "Starting in development mode"
        cherrypy.config.update({'noenvironment': 'production',
                                'log.error_file': 'site.log',
                                'log.screen': True})

    conf = webtools.get_export_map_for_directory("static")
    cherrypy.quickstart(SCAnalyzer(config), '/SCAnalyzer', config=conf)

