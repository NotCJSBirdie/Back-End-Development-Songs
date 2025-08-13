from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "OK"}), 200

@app.route('/count', methods=['GET'])
def count():
    song_count = db.songs.count_documents({})
    return jsonify({"count": song_count}), 200

@app.route('/song', methods=['GET'])
def songs():
    # Retrieve all documents from the songs collection
    songs_cursor = db.songs.find({})
    songs_list = list(songs_cursor)       # Convert cursor to list

    # Serialize MongoDB ObjectId to string for JSON compatibility
    for song in songs_list:
        if '_id' in song:
            song['_id'] = {"$oid": str(song['_id'])}

    return jsonify({"songs": songs_list}), 200

@app.route('/song/<int:id>', methods=['GET'])
def get_song_by_id(id):
    # Look up a song by the "id" field
    song = db.songs.find_one({"id": id})

    if not song:
        # If no song found, return 404
        return jsonify({"message": f"song with id {id} not found"}), 404

    # Convert MongoDB ObjectId to JSON-friendly format
    if '_id' in song:
        song['_id'] = {"$oid": str(song['_id'])}

    return jsonify(song), 200

@app.route('/song', methods=['POST'])
def create_song():
    # Extract song data from request body
    song = request.get_json()

    # Check if song with same id already exists
    existing_song = db.songs.find_one({"id": song["id"]})
    if existing_song:
        return jsonify({"Message": f"song with id {song['id']} already present"}), 302

    # Insert new song
    result = db.songs.insert_one(song)

    # Return inserted id
    return jsonify({"inserted id": {"$oid": str(result.inserted_id)}}), 201

@app.route('/song/<int:id>', methods=['PUT'])
def update_song(id):
    # Extract updated song data from request body
    updated_data = request.get_json()

    # Check if song with given id exists
    existing_song = db.songs.find_one({"id": id})
    if not existing_song:
        return jsonify({"message": "song not found"}), 404

    # Attempt to update the song
    result = db.songs.update_one(
        {"id": id},
        {"$set": updated_data}
    )

    if result.modified_count == 0:
        # Song exists but nothing was changed
        return jsonify({"message": "song found, but nothing updated"}), 200

    # Fetch and return the updated document
    updated_song = db.songs.find_one({"id": id})
    if '_id' in updated_song:
        updated_song['_id'] = {"$oid": str(updated_song['_id'])}

    return jsonify(updated_song), 201

@app.route('/song/<int:id>', methods=['DELETE'])
def delete_song(id):
    # Try deleting the song by id
    result = db.songs.delete_one({"id": id})

    if result.deleted_count == 0:
        # Song not found
        return jsonify({"message": "song not found"}), 404

    # Song deleted successfully
    return '', 204
