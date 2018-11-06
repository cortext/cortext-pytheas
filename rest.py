import json
from flask import Blueprint
from flask import Flask, current_app
from flask import jsonify
from flask import request
from flask import session
from flask import redirect
from flask import url_for
from database import Database
from bson import json_util
from bson.objectid import ObjectId

rest = Blueprint('rest', __name__,)
app = Flask(__name__)

with app.app_context():
    current_app = app
    mongo_curs = Database().init_mongo(app)


##########################################################################
# REST
##########################################################################
@rest.route('/queries/', methods=['GET'])
def queries_list():
    result = mongo_curs.db.query.find({})
    json_res = json_util.dumps(
        result, sort_keys=True, indent=2, separators=(',', ': '))
    return jsonify(json.loads(json_res))

@rest.route('/queries/<query_id>', methods=['GET'])
def query_search(query_id):
    result = mongo_curs.db.query.find_one_or_404({'query_id': query_id})
    json_res = json_util.dumps(
        result, sort_keys=True, indent=2, separators=(',', ': '))
    return jsonify(json.loads(json_res))

@rest.route('/queries/<query_id>/videos/', methods=['GET'])
def videos_list_by_query(query_id):
    result = mongo_curs.db.videos.find({'query_id': query_id})
    json_res = json_util.dumps(
        result, sort_keys=True, indent=2, separators=(',', ': '))
    return jsonify(json.loads(json_res))

@rest.route('/queries/<query_id>/comments/', methods=['GET'])
def comments_list_by_query(query_id):
    result = mongo_curs.db.comments.find({'query_id': query_id})
    json_res = json_util.dumps(
        result, sort_keys=True, indent=2, separators=(',', ': '))
    return jsonify(json.loads(json_res))

@rest.route('/queries/<query_id>/captions/', methods=['GET'])
def captions_list_by_query(query_id):
    result = mongo_curs.db.captions.find({'query_id': query_id})
    json_res = json_util.dumps(
        result, sort_keys=True, indent=2, separators=(',', ': '))
    return jsonify(json.loads(json_res))

@rest.route('/videos/<video_id>', methods=['GET'])
def video_search(video_id):
    result = mongo_curs.db.videos.find({'id.videoId': video_id})
    json_res = json_util.dumps(
        result, sort_keys=True, indent=2, separators=(',', ': '))
    return jsonify(json.loads(json_res))

@rest.route('/videos/<video_id>/comments/', methods=['GET'])
def comments_list_by_video(video_id):
    result = mongo_curs.db.comments.find({'videoId': video_id})
    json_res = json_util.dumps(
        result, sort_keys=True, indent=2, separators=(',', ': '))
    return jsonify(json.loads(json_res))

@rest.route('/comments/<comment_id>', methods=['GET'])
def comment_search(comment_id):
    result = mongo_curs.db.comments.find_one_or_404(
        {'_id': ObjectId(comment_id)})
    json_res = json_util.dumps(
        result, sort_keys=True, indent=2, separators=(',', ': '))
    return jsonify(json.loads(json_res))

@rest.route('/captions/<caption_id>', methods=['GET'])
def caption_search(caption_id):
    result = mongo_curs.db.captions.find_one_or_404(
        {'_id': ObjectId(caption_id)})
    json_res = json_util.dumps(
        result, sort_keys=True, indent=2, separators=(',', ': '))
    return jsonify(json.loads(json_res))

##########################################################################
# Download videos, comments set
##########################################################################
## future work to get dynamically repetitive methods access data. 
## Could be possibly apply on others data side of code.
# but warn because will need to identify query_type in url
# and also rename ontolgogy for query_type based between videos (as lists of videos by query) and others (see below)
@rest.route('/download/<query_type>/<query_id>', methods=['GET'])
def download_videos_by_type(query_id, query_type):
    print(query_type)
    if query_type not in ['comments', 'captions']:
        # need to fix later. There is 404 function in @app
        from flask import render_template
        return render_template('structures/error.html', error='error')

    query = mongo_curs.db.query.find_one({'query_id': query_id})    
    
    if 'query' in query:
        if not 'ranking' in query: 
            query_name = str(query['query'])
        else:
            query_name = '_'.join([query['query'], query['language'], query['ranking']])
    elif 'channel_id' in query:
        query_name = query['channel_id']
    
    query_type = mongo_curs.db[query_type]
    result = query_type.find({'query_id': query_id})
    json_res = json_util.dumps(result, sort_keys=True, indent=2, separators=(',', ': '))

    response = jsonify(json.loads(json_res))
    response.headers['Content-Disposition'] = 'attachment;filename=' + \
        str(query_name) + '_videos.json'
    return response

# old style hard query_type fro /queries/videos...
@rest.route('/download/queries/<query_id>/videos', methods=['GET'])
def download_videos(query_id):
    query = mongo_curs.db.query.find_one({'query_id': query_id})    
    
    if 'query' in query:
        if not 'ranking' in query: 
            query_name = str(query['query'])
        else:
            query_name = '_'.join([query['query'], query['language'], query['ranking']])
    elif 'channel_id' in query:
        query_name = query['channel_id']
    
    result = mongo_curs.db.videos.find({'query_id': query_id})
    json_res = json_util.dumps(result, sort_keys=True, indent=2, separators=(',', ': '))

    response = jsonify(json.loads(json_res))
    response.headers['Content-Disposition'] = 'attachment;filename=' + \
        str(query_name) + '_videos.json'
    return response


##########################################################################
# View db
##########################################################################
# @rest.route('/view-videos/<query_id>', methods=['POST','GET'])
# def view_videos(query_id):
#     print( session['access_token'] )
#     session['access_token'] = session['access_token']
#     url_req = 'http://127.0.0.1:' + str('8080') + '/queries/' + query_id + '/videos/'
#     headers_req = {'access_token': session['access_token']}
#     #print(url_req, headers_req)

#     # r = requests.get( url_req, headers=headers_req)
#     t = videos_list_by_query(query_id)
#     print(json.dumps(json.loads(t.response)))


#     # data = json.loads(my_json)
#     # s = json.dumps(data, indent=4, sort_keys=True)

#     from flask import render_template
#     return render_template('view.html', list_queries=t.response)

# @rest.route('/view-comments/<query_id>', methods=['POST','GET'])
# def view_comments(query_id):    
#     r = requests.get('http://127.0.0.1:' + str(app.config['PORT']) +'/queries/' + query_id + '/comments/')
#     return render_template('view.html', list_queries=r.json())

# @rest.route('/view-captions/<query_id>', methods=['POST','GET'])
# def view_captions(query_id):    
#     r = requests.get('http://127.0.0.1:' + str(app.config['PORT']) +'/queries/' + query_id + '/captions/')
#     return render_template('view.html', list_queries=r.json())


##########################################################################
# Delete dataset
##########################################################################
@rest.route('/delete/<query_id>', methods=['GET'])
def delete(query_id):
    query = mongo_curs.db.query.find_one({'query_id': query_id})
    from_query = json.dumps(query, default=json_util.default)
    from_query = json.loads(from_query)
    
    mongo_curs.db.comments.remove({'query_name': query_id})
    mongo_curs.db.videos.remove({'query_id': query_id})
    mongo_curs.db.query.remove({'query_id': query_id})
    return redirect(url_for('manage'))