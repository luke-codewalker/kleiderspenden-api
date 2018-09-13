from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from pymongo import MongoClient, ReplaceOne
from pymongo.errors import ConnectionFailure, OperationFailure
import os
import re

# setup
load_dotenv("../.env")
app = Flask(__name__)
CORS(app)

# connect to MLab database
client = MongoClient(
    "mongodb://{DB_USER}:{DB_PASSWORD}@ds040837.mlab.com:40837/kleiderspenden".format(**os.environ))
db = client["kleiderspenden"]
sites = db["sites"]

# check if connection was successful
try:
    db.command("ismaster")
    print("Successfully connected to '{0}'".format(db.name))
except (ConnectionFailure, OperationFailure) as e:
    print("Failed to connect to db '{0}': {1}".format(db.name, e))


def strip_id(arg):
    return {key: val for key, val in arg.items() if key != "_id"}

# Routes

# @route: api/sites
# @method: GET
# @desc: get all sites, or all matching a search for a place, or closest one to coordinates


@app.route("/api/sites")
def find():
    # check if params where specified
    params = {key: request.args.get(key)
              for key in ["place", "coords", "category", "radius"]}

    query = {}
    # add category if defined
    if params["category"]:
        query["category.name"] = {"$in": params["category"].split(",")}

    # search for district, area, zipcode
    if params["place"]:
        place = params["place"].lower()
        pattern = re.compile(re.escape(place))
        query["$or"] = [{"location.city": pattern},
                        {"location.district": pattern},
                        {"location.area": pattern},
                        {"location.zipcode": pattern}
                        ]

    # search for coordinates (return within 1 km radius)
    if(params["coords"]):
        # convert coordinates to object
        params["coords"] = {"lat": params["coords"].split(
            ",")[0], "lon": params["coords"].split(",")[1]}
        # form geospatial query
        query["location.gps_location"] = {
            "$near": {
                "$geometry": {"type": "Point", "coordinates": [float(params["coords"]["lon"]), float(params["coords"]["lat"])]},
                "$maxDistance": int(params["radius"]) if params["radius"] is not None else 1000
            }}

    # return result of query (all sites if place parameter, coords or category not specified)
    return jsonify(list(strip_id(x) for x in sites.find(query)))


# @route: api/sites/<id>
# @method: GET
# @desc: get sites by id
@app.route("/api/sites/<uid>")
def find_by_id(uid):
    result = sites.find_one({"uid": uid})
    return jsonify(strip_id(result))
