__author__ = 'cstuempel'

import requests
import time
import base64


class SaveTV(object):
    CONFIGS = {
        'stv': {
            'system': 'All',
            'id': 'MGQ1MDRjZWFkZGUwNGY5MjhjYWJlNjgwMDk4ZTUzNDA=',
            'secret': 'Mjg0NDQwNGQzYjQwNDU1Mjg5N2NiMTc0YjBhN2EyMzIxZGEzMDNjY2FhNmE0YzcyYTQyODE1OGViZmJmYzEyYw=='
        }
        
    }

    username = ''
    password = ''

    access_token = ''
    expires_in = ''
    refresh_token = ''


    def __init__(self, language='en-US', items_per_page=50):
        self._config = self.CONFIGS['stv']
   
        # the default language is always en_US
        if not language:
            language = 'en_US'
            pass

        language = language.replace('-', '_')
        language_components = language.split('_')
        if len(language_components) != 2:
            language = 'en_US'
            pass

        self._language = language
        self._country = language.split('_')[1]
        self._log_error_callback = None

        self._max_results = items_per_page
        pass

 
    def set_log_error(self, callback):
        self._log_error_callback = callback
        pass

    def log_error(self, text):
        if self._log_error_callback:
            self._log_error_callback(text)
            pass
        else:
            print text
            pass
        pass


    def get_login_credentials(self):
        """
        Returns the username and password (Tuple)
        :return: (username, password)
        """
        return self.username, self.password

 
    def request_access_token(self):
        headers = {'Host': 'auth.save.tv',
                   'Connection': 'keep-alive',
                   'Origin': 'https://auth.save.tv',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.28 Safari/537.36',
                   'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                   'Accept': '*/*',
                   'DNT': '1',
                   'Referer': 'https://auth.save.tv',
                   'Accept-Encoding': 'gzip, deflate',
                   'Accept-Language': 'en-US,en;q=0.8,de;q=0.6'}

        _client_id = base64.b64decode(self._config['id'])
        _client_secret = base64.b64decode(self._config['secret'])
        credentials= self.get_login_credentials()
        
        post_data = {'grant_type': 'password',
                     'client_id': _client_id,
                     'client_secret': _client_secret,
                     'username': credentials[0],
                     'password': credentials[1]}

        # url
        url = 'https://auth.save.tv/token'

        result = requests.post(url, data=post_data, headers=headers, verify=False)
        #DEBUG
        #print result
        if result.status_code != requests.codes.ok:
            raise Exception('Access denied')

        if result.headers.get('content-type', '').startswith('application/json'):
            json_data = result.json()
        
            self.access_token = json_data.get('access_token', '')
            self.expires_in = time.time() + int(json_data.get('expires_in', 3600))
            self.refresh_token = json_data.get('refresh_token', '')
        
            # DEBUG
            #print self.access_token
            #print self.expires_in
            #print self.refresh_token
            if self.access_token == '' and self.refresh_token == '':
                raise Exception('Login Failed')
        
            return True

        raise LoginException('unexpected data')

     
    def get_max_results(self):
        return self._max_results

    def get_language(self):
        return self._language

    def get_country(self):
        return self._country

    def calculate_next_page_token(self, page, max_result):
        page -= 1
        low = 'AEIMQUYcgkosw048'
        high = 'ABCDEFGHIJKLMNOP'
        len_low = len(low)
        len_high = len(high)

        position = page * max_result

        overflow_token = 'Q'
        if position >= 128:
            overflow_token_iteration = position // 128
            overflow_token = '%sE' % high[overflow_token_iteration]
            pass
        low_iteration = position % len_low

        # at this position the iteration starts with 'I' again (after 'P')
        if position >= 256:
            multiplier = (position // 128) - 1
            position -= 128 * multiplier
            pass
        high_iteration = (position / len_low) % len_high

        return 'C%s%s%sAA' % (high[high_iteration], low[low_iteration], overflow_token)




    def get_video_stream_url(self, video_id, format, adfree= False):
        
        params = {'adfree': str(adfree).lower()}
        return self._perform_v3_request(method='GET', path='records/%s/downloads/%d' % (video_id, format), params=params)


    def get_categories(self):
        params = {'fields': 'id, name, tvsubcategories.id, tvsubcategories.name'}

        return self._perform_v3_request(method='GET', path='tvcategories', params=params)

    def get_recordings(self, category=None, subcategory=None, channel=None, ishighlight=None, q=None, station=None, minstartdate=None, maxstartdate= None, sort= None, max_results= -2):
        params = {
                 'nopagingheader': 'true',
                 'removedeletedtelecasts': 'true',
                 'recordstates': '3',
                 'fields': 'adfreeavailable, channels, channels.id, channels.name, createdate, enddate, formats, formats.recordformat.id, formats.recordformat.name, formats.recordstate.id, formats.recordstate.name, startdate, telecast, telecast.commentator, telecast.description, telecast.director, telecast.enddate, telecast.episode, telecast.id, telecast.imageurl100, telecast.imageurl250, telecast.imageurl500, telecast.interpret, telecast.isblackwhite, telecast.ishighlight, telecast.isomitted, telecast.moderator, telecast.roles, telecast.roles.rolename, telecast.roles.starid, telecast.roles.starname, telecast.startdate, telecast.subject, telecast.subtitle, telecast.title, telecast.tvcategory.id, telecast.tvcategory.name, telecast.tvstation.id, telecast.tvstation.isrecordable, telecast.tvstation.largelogourl, telecast.tvstation.name, telecast.tvstation.smalllogourl, telecast.tvsubcategory.id, telecast.tvsubcategory.name, telecast.updatedate, telecast.voluntaryselfregulationofthemovieindustry, telecastid, updatedate',
                 }
        if max_results==-2:
            max_results=self._max_results
            
        if max_results!= -1:
            params['limit']= str(max_results)
        if category != None:
            params['tvcategories']= category
        if subcategory != None:
            params['tvsubcategories']= subcategory
        if channel != None:
            params['channels']= channel
        if station != None:
                params['tvstations']= station
        if ishighlight != None:
            params['ishighlight']= str(ishighlight)
        if minstartdate != None:
            params['minstartdate']= minstartdate.isoformat(' ')+'Z'
        if maxstartdate != None:
            params['maxstartdate']= maxstartdate.isoformat(' ')+'Z'
        if q != None:
            params['q']= q
        if sort != None:
                params['sort']= sort
        return self._perform_v3_request(method='GET', path='records', params=params)

    def get_record_formats(self):
        params = {}
        
        return self._perform_v3_request(method='GET', path='recordFormats', params=params)
        
    def get_video_category(self, video_category_id, page_token=''):
        params = {'ishighlight': 'true',
                  'limit': str(self._max_results),
                  'videoCategoryId': video_category_id,
                  'chart': 'mostPopular',
                  'regionCode': self._country,
                  'hl': self._language}
        if page_token:
            params['pageToken'] = page_token
            pass
        return self._perform_v3_request(method='GET', path='videos', params=params)

    def get_video_categories(self, page_token=''):
        params = {'part': 'snippet',
                  'maxResults': str(self._max_results),
                  'regionCode': self._country,
                  'hl': self._language}
        if page_token:
            params['pageToken'] = page_token
            pass

        return self._perform_v3_request(method='GET', path='videoCategories', params=params)


    def delete_recording(self, video_item):

        return self._perform_v3_request(method='DELETE', path='records/'+video_item.get_id())
  
    def get_channels(self):
        params = {'fields': 'channelscope, channeltype, counttelecasts, id, imageurl100, imageurl250, imageurl500, name, searchquery, star.id, star.name, title, tvcategory.id, tvcategory.name, tvstation.id, tvstation.isrecordable, tvstation.name, tvsubcategory.id, tvsubcategory.name'}

        return self._perform_v3_request(method='GET', path='channels', params=params)

 
    def get_stations(self):
        params = {'fields': 'homepageurl, id, isrecordable, name, smalllogourl'}
 
        return self._perform_v3_request(method='GET', path='TvStations', params=params)

 
 # video_item: savetv telecast json
    def get_recommendations(self, video_item):
        video_id= video_item['telecastId']
        
        json_data= self.get_recordings(max_results=5000)
        
        video_archive = json_data.get('items', [])
        
        seriesRec = []
        seriesPos = 0
        moviesRec = []
        
        for seriesPos, item in enumerate(video_archive):
            if item['telecastId'] == video_id:
                break
        else:
            seriesPos = -1        
        
        # search "upwards" to get next episode
        for i in range(seriesPos,len(video_archive)):
            if video_archive[i]['telecast']['title']== video_item['telecast']['title']:
                if video_archive[i]['telecast']['subTitle'] != video_item['telecast']['subTitle']:
                    seriesRec.append(video_archive[i])
                    if len(seriesRec) + len(moviesRec)>=4:
                        break
        
        # search "downwards" to get the rest
        for i in range( seriesPos,-1,-1):
            if video_archive[i]['telecast']['title']== video_item['telecast']['title']:
                if video_archive[i]['telecast']['subTitle'] != video_item['telecast']['subTitle']:
                    if next((obj for obj in seriesRec if obj['telecastId']==video_id), None) is None:
                        seriesRec.append(video_archive[i])
            else:     
                if video_archive[i]['telecast']['tvSubCategory']['id'] == video_item['telecast']['tvSubCategory']['id']: # subcategory identical
                    if next((obj for obj in seriesRec if obj['telecastId']==video_id), None) is None:
                        seriesRec.append(video_archive[i])
            pass
            if len(seriesRec) + len(moviesRec)>=4:
                break
        
        # if the recommendation list is shorter than 4 items, add telecasts from the same category...
        if len(seriesRec) + len(moviesRec) < 4:
            cat = video_item['telecast']['tvCategory']['id']
            for i in range(0,len(video_archive)):
                # if ($.inArray(GlobalVars.VideoArchive[i].SC, GlobalVars.CategoryList[cat]) > -1 &&
                if video_archive[i]['telecast']['tvSubCategory']['id'] == video_item['telecast']['tvSubCategory']['id']: # subcategory identical
                    if (next((obj for obj in moviesRec if obj['telecastId']==video_id), None) is None) and video_archive[i]['telecast']['title']!=video_item['telecast']['title']:
                        moviesRec.append(video_archive[i])
                        if len(seriesRec) + len(moviesRec)>=4:
                            break
                        
                   
        pass    
        
        #...and if there are still less than 4 items, add telecasts from same TV station
        if len(seriesRec) + len(moviesRec) < 4:
            for i in range(0,len(video_archive)):
            # GlobalVars.VideoArchiveDelta API function GetVideoArchiveDelta (different return values than GetVideoArchive)
                if video_archive[i]['telecast']['tvStation']['id'] == video_item['telecast']['tvStation']['id']: 
                #$.inArray(moviesRec, GlobalVars.VideoArchiveDelta[key]) === -1){
                #get according telecast from VideoArchive, because telecasts from ArchiveDelta don't have a StartDate property
                #This. Is. Madness.
                    if (next((obj for obj in moviesRec if obj['telecastId']==video_id), None) is None) and video_archive[i]['telecast']['title']!=video_item['telecast']['title']:
                        moviesRec.append(video_archive[i])
                        if len(seriesRec) + len(moviesRec)>=4:
                            break
                              
            pass                      
            
        #....and if there are still less than 4 items, add latest telecasts that aren't already in rec-list
        if len(seriesRec) + len(moviesRec) < 4:
            for i in range(0,len(video_archive)):
                if (next((obj for obj in moviesRec if obj['telecastId']==video_id), None) is None) and video_archive[i]['telecast']['title']!=video_item['telecast']['title']:
                    moviesRec.append(video_archive[i])
                    if len(seriesRec) + len(moviesRec)>=4:
                        break
                    
        
        return {
                "seriesRec": seriesRec,
                "moviesRec": moviesRec
                }
               

    def search(self, q, search_type=['recordings'], event_type='', page_token=''):
        """
        Returns a collection of search results that match the query parameters specified in the API request. By default,
        a search result set identifies matching video, channel, and playlist resources, but you can also configure
        queries to only retrieve a specific type of resource.
        :param q:
        :param search_type: acceptable values are: 'video' | 'channel' | 'playlist'
        :param event_type: 'live', 'completed', 'upcoming'
        :param page_token: can be ''
        :return:
        """


        # prepare page token
        if not page_token:
            page_token = ''
            pass

        return self.get_recordings(q=q)
        
  
    def _perform_v3_request(self, method='GET', headers=None, path=None, post_data=None, params=None,
                            allow_redirects=True):
        result=None
        for trials in [0,1]:

            result= self._perform_v3_single_request(method,headers,path,post_data,params,allow_redirects)
            if (result.status_code == requests.codes.ok):
                break
            
            if trials==0:
                success= self.request_access_token()
                
                
        if result.headers.get('content-type', '').startswith('application/json'):
            return result.json()
        return None
        

    def get_access_token(self):
        """
        Returns the access token for some API
        :return: access_token
        """
        return self.access_token

            
    def _perform_v3_single_request(self, method='GET', headers=None, path=None, post_data=None, params=None,
                            allow_redirects=True):
        
        
        _params= params
        # headers
        if not headers:
            headers = {}
            pass
        _headers = {'Host': 'api.save.tv',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.36 Safari/537.36',
                    'Accept-Encoding': 'gzip, deflate'}
        # a config can decide if a token is allowed
        _headers['Authorization'] = 'Bearer %s' % self.get_access_token()
        _headers.update(headers)

        # url
        _url = 'https://api.save.tv/v3/%s' % path.strip('/')

        result = None
        print params
        print _url
        
        if method == 'GET':
            result = requests.get(_url, params=_params, headers=_headers, verify=False, allow_redirects=allow_redirects)
            pass
        elif method == 'POST':
            _headers['content-type'] = 'application/json'
            result = requests.post(_url, json=post_data, params=_params, headers=_headers, verify=False,
                                   allow_redirects=allow_redirects)
            pass
        elif method == 'PUT':
            _headers['content-type'] = 'application/json'
            result = requests.put(_url, json=post_data, params=_params, headers=_headers, verify=False,
                                  allow_redirects=allow_redirects)
            pass
        elif method == 'DELETE':
            result = requests.delete(_url, params=_params, headers=_headers, verify=False,
                                     allow_redirects=allow_redirects)
            pass

        if result is None:
            return {}

        return result

