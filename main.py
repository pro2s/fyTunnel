#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
import logging
import math
import codecs 
import base64
import webapp2
import flickr_api
import urllib2
import urllib
import json
import re
import jinja2
import os
import datetime
from flickr import FlickrAPI 
from webapp2_extras import sessions
from google.appengine.api import urlfetch
from google.appengine.api import urlfetch
from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.api import taskqueue
from settings import * 


urlfetch.set_default_fetch_deadline(10)


FYT_SLAVES = [
'http://fyslave.appspot.com/sync/',
'http://fyslave-1.appspot.com/sync/',
'http://fyslave-2.appspot.com/sync/',
'http://fyslave-3.appspot.com/sync/',
]


class Settings(ndb.Model):
    name = ndb.StringProperty()
    value = ndb.StringProperty()
    
    @staticmethod
    def get(name):
        retval = Settings.get_by_id(name)
        if not retval:
            return None
        return retval.value
    
    @staticmethod
    def set(name, value):
        retval = Settings.get_by_id(name)
        if not retval:
            retval = Settings(id  =  name)
            retval.name = name
            retval.value = value
            retval.put()
        else:
            retval.value = value
            retval.put()
            
class Slave(ndb.Model):
    url = ndb.StringProperty()
    order = ndb.IntegerProperty()
    status = ndb.BooleanProperty(default = True)
    
class Album(ndb.Model):
    title = ndb.StringProperty()
    description = ndb.StringProperty()
    flikr_id = ndb.StringProperty()
    yaf_id = ndb.StringProperty()
    sync = ndb.BooleanProperty( default = False)
    
class Photo(ndb.Model):
    title = ndb.StringProperty()
    url = ndb.StringProperty()
    flikr_id = ndb.StringProperty()
    flikr_album_id = ndb.StringProperty()
    yaf_id = ndb.StringProperty()
    yaf_album_id = ndb.StringProperty()
    sync = ndb.BooleanProperty( default = False)


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader([os.path.join(os.path.dirname(__file__),"templates"),],encoding='utf-8'),
    extensions=['jinja2.ext.autoescape'])



MENU = [
    {
    "id":"index",
    "name":u"Flickr",
    "url":"/",
    },
    {
    "id":"yaf",
    "name":u"Яндекс.фотки",
    "url":"/",
    },
    {
    "id":"trafik",
    "name":u"Трафик",
    "url":"/",
    },
]

class BaseHandler(webapp2.RequestHandler):
    def dispatch(self):
        # Get a session store for this request.
        self.session_store = sessions.get_store(request=self.request)
        try:
            # Dispatch the request.
            webapp2.RequestHandler.dispatch(self)
        finally:
            # Save all sessions.
            self.session_store.save_sessions(self.response)
 
    @webapp2.cached_property
    def session(self):
        # Returns a session using the default cookie key.
        return self.session_store.get_session()

        
class Clear(BaseHandler):
    def get(self):	       
        order = 0    
        for slave_url in FYT_SLAVES:
            s = Slave.get_or_insert(slave_url)
            s.url = slave_url
            s.status = True
            s.order = order
            s.put()
            order += 1
        self.response.write("OK")

class Clean(BaseHandler):        
    def get(self):	        
        id = self.request.get('id','')
        a = Album.get_by_id(id)
        if a is not None and not a.sync:
            ndb.delete_multi(
                Photo.query(Photo.flikr_album_id == id).fetch(keys_only=True)
            )
            self.response.write("OK")
                        
class PhotoSync(BaseHandler):
    def post(self): 
        id = self.request.get('id')
        p = Photo.get_by_id(id)
        urlfetch.set_default_fetch_deadline(60)
        if p is not None:
            if not p.sync or p.yaf_id == '':
                data = ""
                
                result = urlfetch.fetch(p.url)
                data = result.content
                url = 'http://api-fotki.yandex.ru/api/users/protasov-s/album/'+ p.yaf_album_id +'/photos/?format=json'
                logging.info(url)
                result = urlfetch.fetch(url=url,
                    payload=data,
                    method=urlfetch.POST,
                    headers={'Content-Length': len(data),'Content-Type': 'image/jpeg', 'Authorization':'OAuth ' + yaf_token})

                url = result.headers.get('Location')
                photo = json.loads(result.content)
                
                photo['title'] =  p.flikr_id
                photo['summary'] = p.title
                photo_data = json.dumps(photo)
                # logging.info(photo_data)
                result = urlfetch.fetch(url=url,
                    payload=photo_data,
                    method=urlfetch.PUT,
                    headers={'Accept': 'application/json','Content-Type': 'application/json; charset=utf-8; type=entry;', 'Authorization':'OAuth ' + yaf_token})
                if result.status_code == 200:
                    p.yaf_id = photo['id']
                    p.sync = True
                    p.put()
                
            


class Sync(BaseHandler):
    def post(self):
        p_id =  self.request.get('id')
        p_title =  self.request.get('title')
        album_id = self.request.get('album_id')
        album_yaf = self.request.get('album_yaf').split(':')[-1]
        
        ph = Photo.get_by_id(p_id)
        if ph is None:
            f = FlickrAPI(api_key = F_API_KEY,
                api_secret= F_API_SECRET,
                oauth_token= F_TOKEN,
                oauth_token_secret= F_TOKEN_SECRET)
            
            sizes = f.get('flickr.photos.getSizes', params={'photo_id': p_id})
            if sizes['stat'] == 'ok':
                url_photo = sizes['sizes']['size'][-1]['source']
            logging.info(url_photo)
            
            ph = Photo(
                id = p_id, 
                url = url_photo,
                title = p_title, 
                flikr_id = p_id,
                flikr_album_id = album_id,  
                yaf_id = '', 
                yaf_album_id = album_yaf,
                )
            ph.put()
        if not ph.sync:
            # taskqueue.add(url='/psync/',queue_name='psync', params = {'id': p.id,})
            
            form_fields = {
              "id": ph.flikr_id,
              "url": ph.url,
              "title": ph.title,
              "album_id": ph.yaf_album_id,
            }
            form_data = urllib.urlencode(form_fields)
            slaves = Slave.query().order(Slave.order)
            slave_url = 'http://fyslave.appspot.com/sync/'
            for s in slaves:
                logging.info(s)
                if s.status: 
                    slave_url = s.url
                    break
            logging.info(slave_url)
            result = urlfetch.fetch(url= slave_url,
                payload=form_data,
                method=urlfetch.POST,
                headers={'Content-Type': 'application/x-www-form-urlencoded'})
        
    def get(self):	        
        flickr_auth = flikr_token
        if flickr_auth is not None:
            a = flickr_api.auth.AuthHandler.fromdict(flickr_auth)
            flickr_api.set_auth_handler(a)
            u = flickr_api.test.login()
            id = self.request.get('id','')
            for item in u.getPhotosets():
                if item.id == id:
                    a = Album.get_by_id(item.id)
                    if a is not None and not a.sync:
                        pages = (item.photos + 250) // 500
                        if pages == 0: pages = 1 
                        for page in range(pages):
                            for p in item.getPhotos(page = page + 1):
                                # p.id, p.title, album.id, album.yaf_id
                                taskqueue.add(url='/sync/', params = {'id': p.id, 'title': p.title, 'album_id': item.id, 'album_yaf':a.yaf_id})
                        self.response.write(a.title + '<br>')
                        
                    
class GetResult(BaseHandler):
    def post(self):     
        id = self.request.get('id')
        status = self.request.get('status')
        yaf_id = self.request.get('yandex_id')
        slave_url = self.request.get('slave_url')
        logging.info(slave_url)
        if status == 'ok':
            p = Photo.get_by_id(id)
            if p is not None:
                p.yaf_id = yaf_id
                p.sync = True
                p.put()
        elif status == 'busy':
            s = Slave.get_by_id(slave_url)
            if s is not None:
                s.status = False
                s.put()    
        
        
class GetVerifier(BaseHandler):
    def get(self):	        
        oauth_verifier = self.request.get('oauth_verifier')
        oauth_token = self.session.get('oauth_token')
        oauth_token_secret = self.session.get('oauth_token_secret')
        f = FlickrAPI(api_key=F_API_KEY,
              api_secret=F_API_SECRET,
              oauth_token=oauth_token,
              oauth_token_secret=oauth_token_secret)

        authorized_tokens = f.get_auth_tokens(oauth_verifier)

        Settings.set('F_TOKEN', authorized_tokens['oauth_token'])
        
        Settings.set('F_TOKEN_SECRET', authorized_tokens['oauth_token_secret'])
        self.redirect('/')
        
	
class MainHandler(BaseHandler):
    def get(self):
        url = ''
        ps = ''
        albums = {}
        y_albums = {}
        
        auth = False
        
        F_TOKEN = Settings.get('F_TOKEN')
        F_TOKEN_SECRET = Settings.get('F_TOKEN_SECRET')
        if F_TOKEN and F_TOKEN_SECRET:
            f = FlickrAPI(api_key = F_API_KEY,
                api_secret= F_API_SECRET,
                oauth_token= F_TOKEN,
                oauth_token_secret= F_TOKEN_SECRET)
            try:
                result = f.get('flickr.test.null')
                if result['stat'] == 'ok':
                    auth = True
            except:
                auth = False
        
        if  not auth:
            f = FlickrAPI(api_key=F_API_KEY,
                api_secret=F_API_SECRET,
                callback_url='http://fytunnel.appspot.com/callback/')
                #callback_url='http://localhost:10080/callback/')
            auth_props = f.get_authentication_tokens(perms = 'read')
            auth_url = auth_props['auth_url']

            #Store this token in a session or something for later use in the next step.
            self.session['oauth_token'] =  auth_props['oauth_token']
            self.session['oauth_token_secret'] = auth_props['oauth_token_secret']
            self.redirect(auth_url)
            
        else:
        
            f = FlickrAPI(api_key = F_API_KEY,
                api_secret= F_API_SECRET,
                oauth_token= F_TOKEN,
                oauth_token_secret= F_TOKEN_SECRET)
            
            user = f.get('flickr.test.login')
            data = f.get('flickr.photosets.getList', params={'user_id': user['user']['id']})
            
            albums = {}
            if data['stat'] == 'ok':
                for item in data['photosets']['photoset']:
                    id = item['id']
                    albums[id] = {} 
                    albums[id]['id'] = id
                    albums[id]['photos'] = item['photos']
                    albums[id]['title'] = item['title']['_content']
                    albums[id]['description'] = item['description']['_content']
            
            
            '''
            a = flickr_api.auth.AuthHandler.fromdict(flickr_auth)
            flickr_api.set_auth_handler(a)
            u = flickr_api.test.login()
            ps = u.getPhotosets()
            '''
            
            for id, item in albums.iteritems():
                a = Album.get_by_id(id)
                
                if a is None:
                    a = Album(title = item['title'],description = item['description'], flikr_id = item['id'], yaf_id = '', id = id)
                    a.put()
                if a.yaf_id == '':
                    url = 'http://api-fotki.yandex.ru/api/users/protasov-s/albums/?format=json'
                    data = json.dumps({'title':item['title'], 'summary':item['description'], 'password':item['id']})
                    req = urllib2.Request(url, data, {'Accept': 'application/json','Content-Type': 'application/json; charset=utf-8; type=entry;', 'Authorization':'OAuth ' + yaf_token})
                    f = urllib2.urlopen(req)
                    data = json.load(f)
                    a.yaf_id = data['id']
                    a.put()
                    f.close()
                if a.title != item['title'] or a.description != item['description']:
                    a.title = item['title']
                    a.description = item['description']
                    
                    url = 'http://api-fotki.yandex.ru/api/users/protasov-s/album/%s/?format=json' % a.yaf_id.split(':')[-1]
                    result = urlfetch.fetch(url=url,headers={'Accept': 'application/json', 'Authorization':'OAuth ' + yaf_token})
                    if result.status_code == 200:
                        yalbum = json.loads(result.content)
                        yalbum['title'] = item['title']
                        yalbum['summary'] = item['description']
                        
                        yalbum_data = json.dumps(yalbum)
                        
                        result = urlfetch.fetch(url=url,
                        payload=yalbum_data,
                        method=urlfetch.PUT,
                        headers={'Accept': 'application/json','Content-Type': 'application/json; charset=utf-8; type=entry;', 'Authorization':'OAuth ' + yaf_token})
                        
                    
                item['yaf_id'] = a.yaf_id
            
            url = 'http://api-fotki.yandex.ru/api/users/protasov-s/albums/published/'
            result = urlfetch.fetch(url=url, headers={'Accept': 'application/json', 'Authorization':'OAuth ' + yaf_token})
            data = json.loads(result.content)
            
            for a in data['entries']:
                y_albums[a['id']] = a
        
        template_values = {
        'auth':auth,
        'menu':MENU,
        'active':'index',
        'albums':albums,
        'url':url,
        'y_albums':y_albums
        }
        template = JINJA_ENVIRONMENT.get_template('index.tpl')
        html = template.render(template_values)
        self.response.write(html)

config = {}
config['webapp2_extras.sessions'] = {
    'secret_key': 'some-secret-key',
}        
app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/callback/',GetVerifier),
    ('/clear/',Clear),
    ('/clean/',Clean),
    ('/sync/',Sync),
    ('/result/',GetResult),
    ('/psync/',PhotoSync),
    
], debug=True,config=config)
