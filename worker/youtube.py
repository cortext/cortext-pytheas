import requests
import json
import os
import datetime as dt
import dateutil.parser as time
import logging
import re
from uuid import uuid4
from xml.etree import ElementTree
from html_unescaping import unescape
from code_country import language_code

data_dir = 'data/'

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Console handler
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
# format
formatter = logging.Formatter('%(filename)s ## [%(asctime)s] -- %(levelname)s == "%(message)s"')
stream_handler.setFormatter(formatter)
# add handler
logger.addHandler(stream_handler)


##########################################################################
# Youtube Data Api request
# used to make all http request to Youtube Data Api
##########################################################################
class YouTube():
    #api_key = None
    #access_token = None
    #api_base_url = 'https://www.googleapis.com/youtube/v3/'
    #part = None

    def __init__(self, api_key, access_token=None, api_url=None, part=None, type_part=None):
        self.api_key = api_key
        self.access_token = access_token
        self.api_base_url = 'https://www.googleapis.com/youtube/v3/'
        if part:
            self.part = part
        if type_part:
            self.type_part = type_part
        if api_url:
            self.api_url = api_url

    # make req
    def try_request(self, kwargs, endpoint):
        url = self.api_base_url + endpoint
        try:
            req = requests.get(url, kwargs)
            logger.info('try_request success on ' +  url)
            logger.debug('kwargs are ' + str(kwargs))
        except requests.exceptions.RequestException as e:
            logger.warning('try_request failed on ' + url)
            logger.warning('error is : ' + str(e))
        logger.debug(self.response(req))    
        return req.json()

    # prepare request with same obligatory param
    def get_query(self, endpoint, **kwargs):
        if self.access_token:
            kwargs['access_token'] = self.access_token
        else:
            kwargs['key'] = self.api_key
        if 'part' not in kwargs:
            kwargs['part'] = self.part
        # need integration of dynamic part choose
        # if 'type_part' in kwargs:
        #     kwargs['type'] = self.type_part
        kwargs = json.dumps(kwargs)
        kwargs = json.loads(kwargs)
        return self.try_request(kwargs, endpoint)

    # not used anymore for now but later...
    # have to invert between generic and complex methods who have to be repetaed often
    def get_search(self, query_data):
        if 'language' in query_data :
            search_results = YouTube(self.api_key).get_query(
                'search',
                q=query_data['q'],
                part=query_data['part'],
                relevanceLanguage=query_data['language'],
                maxResults=query_data['maxResults'],
                order=query_data['order']
            )
        else:
            search_results = YouTube(self.api_key).get_query(
                'search',
                q=query_data['q'],
                part=query_data['part'],
                maxResults=query_data['maxResults'],
                order=query_data['order']
            )
        return search_results

    def get_chrono_search(self, query_data):
        if 'language' in query_data :
            search_results = YouTube(self.api_key).get_query(
                'search',
                q=query_data['q'],
                part=query_data['part'],
                relevanceLanguage=query_data['language'],
                maxResults=query_data['maxResults'],
                publishedAfter = query_data['publishedAfter'],
                publishedBefore = query_data['publishedBefore'],
                order='date',
            )
        else:
            search_results = YouTube(self.api_key).get_query(
                'search',
                q=query_data['q'],
                part=query_data['part'],
                maxResults=query_data['maxResults'],
                publishedAfter = query_data['publishedAfter'],
                publishedBefore = query_data['publishedBefore'],
                order='date',
            )
        return search_results
    
    def get_channel_videos(self, mongo_curs, param):
        # taking paramaters pre-formated in Youtube style
        query_id = param['query_id']
        query_name = param['query']
        param_lighted = param.copy()
        del param_lighted['query']
        del param_lighted['query_id']

        api = YouTube(self.api_key)
        channel_playlistId = api.get_query(
            'channels',
            **param_lighted
        )

        param_lighted['part'] = param_lighted['part'].replace(', statistics', '')
        for items in channel_playlistId['items']:

            del param_lighted['id']
            param_lighted.update({'playlistId' : items['contentDetails']['relatedPlaylists']['uploads']})

            channel_results = api.get_query(
                'playlistItems',
                **param_lighted
            )

            # insert videos
            for each in channel_results['items']:
                each.update({'query_id'   : query_id,
                             'query' : query_name})
                each = YouTube.cleaning_each(each)
                mongo_curs.db.videos.insert_one(each)

            ## Loop and save
            while 'nextPageToken' in channel_results:
                channel_results = api.get_query(
                    'playlistItems',
                    **param_lighted,
                    pageToken=channel_results['nextPageToken']
                )

                for each in channel_results['items']:
                    each.update({'query_id'   : query_id,
                                 'query' : query_name})
                    each = YouTube.cleaning_each(each)
                    mongo_curs.db.videos.insert_one(each)

                # check if not last result 
                if not channel_results['items']:
                    break

        return

    # same as get_playlist (could be merged later maybe)
    def get_playlist(self, mongo_curs, param):
        query_id = param['query_id']
        query_name = param['query']
        playlist_id = param['playlist_id']
        part = param['part']
        maxResults = param['maxResults']
        
        api = YouTube(self.api_key)
        playlist_results = api.get_query(
            'playlistItems',
            playlistId=playlist_id,
            part=part,
            maxResults=maxResults
        )

        for each in playlist_results['items']:
            each.update({'query_id'   : query_id,
                         'query' : query_name})
            each = YouTube.cleaning_each(each)
            mongo_curs.db.videos.insert_one(each)

        while 'nextPageToken' in playlist_results:
            playlist_results = api.get_query(
                'playlistItems',
                playlistId=playlist_id,
                part=part,
                maxResults=maxResults,
                pageToken=playlist_results['nextPageToken']
            )

            for each in playlist_results['items']:
                each.update({'query_id': query_id,
                             'query' : query_name})
                each = YouTube.cleaning_each(each)
                mongo_curs.db.videos.insert_one(each)

            if not playlist_results['items']:
                break

        return playlist_results

    def verify_error(api_key, result_query):
        if not 'error' in result_query:
            return result_query
        else:
            logger.errors('Reason of error is : ' + commentThread['error']['errors'][0]['reason'])
            return commentThread['error']

    # Unclassed for moment
    # is for clean data from Youtube
    def cleaning_each(each):
        if 'videoId' in each['id']:
            each.update({'videoId': each['id']['videoId']})
        elif 'playlistId' in each['id']:
            each.update({'playlistId': each['id']['playlistId']})
        elif 'channelId' in each['id']:
            each.update({'channelId': each['id']['channelId']})
        return each
        
    # Unclassed for moment
    def cleaning_video(id_video):
        if 'youtube.com/watch?v=' in id_video:
            if 'https' in id_video:
                id_video = id_video.replace(
                    'https://www.youtube.com/watch?v=', '')
            else:
                id_video = id_video.replace(
                    'http://www.youtube.com/watch?v=', '')
        return id_video

    # cleaning_channel is for cleaning input url from user usage
    def cleaning_channel(id_channel_or_user):
        try:
            if 'https' in id_channel_or_user:
                id_channel_or_user = id_channel_or_user.replace(
                    'https://www.youtube.com', '')
            elif 'http':
                id_channel_or_user = id_channel_or_user.replace(
                    'http://www.youtube.com', '')

            if '/channel/' in id_channel_or_user:
                id_channel_or_user = id_channel_or_user.replace(
                    '/channel/', '')

            if '/c/' in id_channel_or_user:
                id_channel_or_user = id_channel_or_user.replace(
                    '/c/', '')

            if '/user/' in id_channel_or_user:
                id_channel_or_user = id_channel_or_user.replace(
                    '/user/', '')
        except Exception as e:
            logger.debug('Unexpected error on cleaning_channel :' + str(e))

        return id_channel_or_user

    def cleaning_playlist(id_playlist):
        # HERE WIlL have to parse URL or detect id PLYALIST later
        # if '&list=' in id_playlist:
        #     if 'https' in id_playlist:
        #         id_playlist = id_playlist.replace(
        #             'https://www.youtube.com/channel/', '')
        #     else:
        #         id_playlist = id_playlist.replace(
        #             'http://www.youtube.com/channel/', '')
        return id_playlist

    @staticmethod
    def response(response):
        return response.json()

##########################################################################
# Video
# rename in aggregate class (because of list of videos)
##########################################################################
class Video():
    # to complete
    video_fields = ['_id','videoId','query_id','kind', 'part']
    snippet_fields = ['']
    stats_fields = ['']

    def __init__(self, mongo_curs, video_id=None, query_id=None, api_key=None):
        self.db = mongo_curs.db
        if video_id:
            self.id_video = id_video
        if query_id:
            self.query_id = query_id
        if api_key:
            self.api_key = api_key
            self.api = YouTube(api_key=api_key)

    def add_stats_for_each_entry(self, query_id):
        try:        
            current_videos = self.db.videos.find({ 'query_id': query_id})
            for video in current_videos:
                id_video = video['videoId']
                stat_result = self.api.get_query('videos', id=id_video, part='id,statistics')
                
                logger.error(stat_result)
                logger.error(id_video)
                logger.error(query_id)

                # add new stats
                self.db.videos.update_one(
                    {   
                        '$and':
                            [{ 'videoId': id_video },
                            { 'query_id': query_id }] 
                         
                    },{ 
                        '$set': {
                            'statistics': stat_result['items'][0]['statistics']
                        }
                    }, upsert=False
                )

            # add new part
            # seems like $concat method didnt work with pymongo and update method (cf. $set)
            # have to make two call to db...
            part_value = self.db.queries.find_one_or_404({ 'query_id': query_id})
            self.db.queries.update_one(
                {
                    'query_id': query_id
                },{
                    '$set': {
                        'part': part_value['part'] + ", statistics",                             
                    } 
                }, upsert=False
            )

        except BaseException as e:
            logger.error('add_stats_for_each_entry get an error : ', str(e))
            return e
        return

    def delete():
        return


##########################################################################
# Comment
# rename in aggregate class (because of list of videos)
##########################################################################
class Comment():
    def __init__(self, mongo_curs, query_id):
        #super(Executive, self).__init__(*args)
        self.db = mongo_curs.db
        self.query_id = query_id

    def create_comment_for_each(self, commentThread):
        if not 'error' in commentThread:
            nb_comment = 0
            for each in commentThread['items']:
                nb_comment += 1
                
                snippet = each['snippet']['topLevelComment']['snippet']
                if 'authorChannelId' in snippet:
                    snippet['authorChannelId'] = snippet['authorChannelId']['value']
                else:
                    snippet['authorChannelId'] = 'cortext_pytheas_unknown_author#' + each['id']
                
                topCommentIntegrated = {
                    'id' : each['id'],
                    'query_id' : self.query_id,
                    'isPublic': each['snippet']['isPublic'],
                    'canReply': each['snippet']['canReply'],
                    'totalReplyCount': each['snippet']['totalReplyCount'],
                    'videoId' : each['snippet']['videoId'],
                    'snippet': snippet,
                    'is_top_level_comment': 'true',
                }
                self.db.comments.insert_one(topCommentIntegrated)
                
                if 'replies' in each:
                    for child in each['replies']['comments']:
                        nb_comment += 1
                        snippet = child['snippet']
                        if 'authorChannelId' in snippet:
                            snippet['authorChannelId'] = snippet['authorChannelId']['value']
                        else:
                            snippet['authorChannelId'] = 'cortext_pytheas_unknown_author#' + each['id']

                        CommentIntegrated = {
                            'id' : child['id'],
                            'query_id' : self.query_id,
                            'videoId' : child['snippet']['videoId'],
                            'snippet': snippet,
                            'is_top_level_comment': 'false'
                        }
                        self.db.comments.insert_one(CommentIntegrated)
        else:
            logger.error(commentThread['error'])
            logger.error('reason of error is : ' + commentThread['error']['errors'][0]['reason'])

        return

    # taken from cloned Captions
    def count_comments(self, query_id):
        query_id = self.query_id

        try:
            current_comment = self.db.comment.find_one_or_404(
                { '$and':[{ 'query_id': query_id }, { 'videoId': video_id }] }
            )
        except:
            self.create_captions(id_video)
            logger.error(
                'error need more investigate'
            )
        return


##########################################################################
# Related Videos
##########################################################################
class RelatedVideos():   
    def __init__(self, mongo_curs, query_id):
        self.db = mongo_curs.db
        self.query_id = query_id
        self.maxResults = 50
        self.type = 'video'

    def create_relatedVideos(self, video_id):
        self.db.relatedVideos.insert_one({
            'query_id' : self.query_id,
            'relatedToVideoId' : video_id,
            'part' : 'id,snippet',
            'type' : self.type,
        })

    def createRelatedVideos_if_not_exist(self, video_id):
        query_id = self.query_id
        
        for x in search_results['items']:
            logger.debug(
                str('FIKNJKBNJKFNDJKNFJKNKNFNDJKN') + str(x) + str(type(x))
            ) 

        try:
            current_relatedVideos = self.db.relatedVideos.find_one_or_404(
                { '$and':[{ 'query_id': query_id }, { 'relatedToVideoId': video_id }] }
            )
        except BaseException as e:
            self.create_relatedVideos(video_id)
            logger.warning(
                str('relatedVideos not found or error. Log is here : ') + str(e) + str(type(e))
            ) 
        return

##########################################################################
# Captions
# rename in aggregate class (because of list of videos)
##########################################################################
class Caption():
    # https://github.com/jdepoix/youtube-transcript-api (sese below next Class YoutubeTranscript API)
    # use an undocumentad part of the api youtube (web client api)
    
    def __init__(self, mongo_curs, query_id):
        self.db = mongo_curs.db
        self.query_id = query_id

    def create_captions(self, video_id):
        # for x in language_code:
        #     logger.debug(x[0])
        transcript = YouTubeTranscriptApi().get_transcript(video_id, languages=x[0])
        self.db.captions.insert_one({
            'query_id' : self.query_id,
            'videoId' : video_id,
            'captions' : transcript,
            'language' : x[0]
        })

    def create_if_not_exist(self, video_id):
        query_id = self.query_id
        try:
            current_caption = self.db.captions.find_one_or_404(
                { '$and':[{ 'query_id': query_id }, { 'id.videoId': video_id }] }
            )
        except BaseException as e:
            self.create_captions(video_id)
            logger.warning(
                str('Caption not found or error. Log is here : ') + str(e) + str(type(e))
            ) 
        return


#################################################################""
# https://github.com/jdepoix/youtube-transcript-api

class YouTubeTranscriptApi():
    class CouldNotRetrieveTranscript(Exception):
        """
        Raised if a transcript could not be retrieved.
        """

        ERROR_MESSAGE = (
            'Could not get the transcript for the video {video_url}! '
            'This usually happens if one of the following things is the case:\n'
            ' - subtitles have been disabled by the uploader\n'
            ' - none of the language codes you provided are valid\n'
            ' - none of the languages you provided are supported by the video\n'
            ' - the video is no longer available.\n\n'
            'If none of these things is the case, please create an issue at '
            'https://github.com/jdepoix/youtube-transcript-api/issues'
        )

        def __init__(self, video_id):
            super(YouTubeTranscriptApi.CouldNotRetrieveTranscript, self).__init__(
                self.ERROR_MESSAGE.format(video_url=_TranscriptFetcher.WATCH_URL.format(video_id=video_id))
            )
            self.video_id = video_id

    @classmethod
    def get_transcripts(cls, video_ids, languages=None, continue_after_error=False, proxies=None):
        """
        Retrieves the transcripts for a list of videos.

        :param video_ids: a list of youtube video ids
        :type video_ids: [str]
        :param languages: A list of language codes in a descending priority. For example, if this is set to ['de', 'en']
        it will first try to fetch the german transcript (de) and then fetch the english transcipt (en) if it fails to
        do so. As I can't provide a complete list of all working language codes with full certainty, you may have to
        play around with the language codes a bit, to find the one which is working for you!
        :type languages: [str]
        :param continue_after_error: if this is set the execution won't be stopped, if an error occurs while retrieving
        one of the video transcripts
        :type continue_after_error: bool
        :param proxies: a dictionary mapping of http and https proxies to be used for the network requests
        :type proxies: {'http': str, 'https': str} - http://docs.python-requests.org/en/master/user/advanced/#proxies
        :return: a tuple containing a dictionary mapping video ids onto their corresponding transcripts, and a list of
        video ids, which could not be retrieved
        :rtype: ({str: [{'text': str, 'start': float, 'end': float}]}, [str]}
        """
        data = {}
        unretrievable_videos = []

        for video_id in video_ids:
            try:
                data[video_id] = cls.get_transcript(video_id, languages, proxies)
            except Exception as exception:
                if not continue_after_error:
                    raise exception

                unretrievable_videos.append(video_id)

        return data, unretrievable_videos

    @classmethod
    def get_transcript(cls, video_id, languages=None, proxies=None):
        """
        Retrieves the transcript for a single video.

        :param video_id: the youtube video id
        :type video_id: str
        :param languages: A list of language codes in a descending priority. For example, if this is set to ['de', 'en']
        it will first try to fetch the german transcript (de) and then fetch the english transcript (en) if it fails to
        do so. As I can't provide a complete list of all working language codes with full certainty, you may have to
        play around with the language codes a bit, to find the one which is working for you!
        :type languages: [str]
        :param proxies: a dictionary mapping of http and https proxies to be used for the network requests
        :type proxies: {'http': str, 'https': str} - http://docs.python-requests.org/en/master/user/advanced/#proxies
        :return: a list of dictionaries containing the 'text', 'start' and 'duration' keys
        :rtype: [{'text': str, 'start': float, 'end': float}]
        """
        try:
            return _TranscriptParser(_TranscriptFetcher(video_id, languages, proxies).fetch()).parse()
        except Exception:
            raise YouTubeTranscriptApi.CouldNotRetrieveTranscript(video_id)


class _TranscriptFetcher():
    WATCH_URL = 'https://www.youtube.com/watch?v={video_id}'
    API_BASE_URL = 'https://www.youtube.com/api/{api_url}'
    LANGUAGE_REGEX = re.compile(r'(&lang=.*&)|(&lang=.*)')

    def __init__(self, video_id, languages, proxies):
        self.video_id = video_id
        self.languages = languages
        self.proxies = proxies

    def fetch(self):
        if self.proxies:
            fetched_site = requests.get(self.WATCH_URL.format(video_id=self.video_id), proxies=self.proxies).text
        else:
            fetched_site = requests.get(self.WATCH_URL.format(video_id=self.video_id)).text
        timedtext_url_start = fetched_site.find('timedtext')

        for language in (self.languages if self.languages else [None,]):
            response = self._execute_api_request(fetched_site, timedtext_url_start, language)
            if response:
                return response

        return None

    def _execute_api_request(self, fetched_site, timedtext_url_start, language):
        url = self.API_BASE_URL.format(
            api_url=fetched_site[
                timedtext_url_start:timedtext_url_start + fetched_site[timedtext_url_start:].find('"')
            ].replace(
                '\\u0026', '&'
            ).replace(
                '\\', ''
            )
        )
        if language:
            url = re.sub(self.LANGUAGE_REGEX, '&lang={language}&'.format(language=language), url)
        if self.proxies:
            return requests.get(url, proxies=self.proxies).text
        else:
            return requests.get(url).text


class _TranscriptParser():
    HTML_TAG_REGEX = re.compile(r'<[^>]*>', re.IGNORECASE)

    def __init__(self, plain_data):
        self.plain_data = plain_data

    def parse(self):
        return [
            {
                'text': re.sub(self.HTML_TAG_REGEX, '', unescape(xml_element.text)),
                'start': float(xml_element.attrib['start']),
                'duration': float(xml_element.attrib['dur']),
            }
            for xml_element in ElementTree.fromstring(self.plain_data)
            if xml_element.text is not None
        ]