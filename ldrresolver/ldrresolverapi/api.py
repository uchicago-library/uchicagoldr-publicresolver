from datetime import datetime
from flask import jsonify, Blueprint, request, send_file, make_response
from flask_restful import abort, Resource, Api, reqparse
from io import BytesIO
from os import listdir
from os.path import join, exists
from werkzeug.utils import secure_filename
from re import compile as regex_compile
from xml.etree import ElementTree as ET
import re

from pypairtree.utils import identifier_to_path
from ldrpremisbuilding.utils import *
from uchicagoldrapicore.responses.apiresponse import APIResponse
from uchicagoldrapicore.responses.apiresponse import APIResponse
from uchicagoldrapicore.lib.apiexceptionhandler import APIExceptionHandler

_ALPHANUM_PATTERN = regex_compile("^[a-zA-Z0-9]+$")
_NUMERIC_PATTERN = regex_compile("^[0-9]+$")
_EXCEPTION_HANDLER = APIExceptionHandler()

# Create our app, hook the API to it, and add our resources

BP = Blueprint("ldrprocessorserverapi", __name__)
API = Api(BP)

def make_download_event(path_to_record, event_category, event_date, event_status, user, objid):
    if re.compile("^a|e|i|o|u.*").match(event_category):
        event_message = "there was an {} of this content".format(event_category)
    else:
        event_message = "there was a {} of this content".format(event_category)
    new_download_event = build_a_premis_event(event_category, event_date, event_status, event_message, user, objid, agent_type="person")
    was_it_written = add_event_to_premis_record(path_to_record, new_download_event)
    print(new_download_event)
    new_download_event = build_a_premis_event(event_category, event_date, event_status, event_message, user, objid, agent_type="person")
    was_it_written = add_event_to_premis_record(path_to_record, new_download_event)
    print(new_download_event)
    print(was_it_written)
    return was_it_written

def get_data_half_of_object(arkid, premisid, lp_path):
    arkid_path = str(identifier_to_path(arkid))
    premisid_path = str(identifier_to_path(premisid))
    path_to_premis = join(lp_path, arkid_path,"arf", "pairtree_root", premisid_path, "arf", "premis.xml")
    if exists(path_to_premis):
        return (path_to_premis, extract_identity_data_from_premis_record(path_to_premis))
    else:
        return None

def get_content_half_of_object(arkid, premisid, lts_path):
    arkid_path = str(identifier_to_path(arkid))
    premisid_path = str(identifier_to_path(premisid))
    path_to_content = join(lts_path, arkid_path,"arf",
                           "pairtree_root", premisid_path,
                           "arf", "content.file")
    if exists(path_to_content):
        return (path_to_content, None)
    else:
        return None

def get_object_halves(arkid, premisid, lts_path, lp_path):
    content = get_data_half_of_object(arkid, premisid, lts_path)
    data = get_data_half_of_object(arkid, premisid, lp_path)
    if content and data:
        return (content[0], data[1])
    else:
        return None

def get_an_attachment_filename(data_bit):
    try:
        extension = data_bit.mimetype.split('/')[1]
    except IndexError:
        extension = None
    if extension:
        return (str(data_bit.objid + "." + extension), data_bit.mimetype)
    else:
        return (data_bit.objid, "application/octet-stream")

class GetAContentItem(Resource):
    """
    fill_in_please
    """
    def get(self, arkid, premisid):
        """
        Get the whole record
        """
        from flask import current_app
        whitelist_opened = open(current_app.config["WHITELIST"], "r")
        check = False
        for line in whiteliste_opened:
            if line.strip() == join(arkid, premisid):
                check = True
                break
        if not check:
             return abort(404,  message="could not find the {}".format(join(arkid, presform.objid)))
        try:
            user = "authorized" if "private" in request.environ.get("REQUEST_URI") else "anonymous"
            event_category = "anonymous download" if user == "anonymous" else "authorized download"
            data = get_object_halves(arkid, premisid, current_app.config["LONGTERMSTORAGE_PATH"], current_app.config["LIVEPREMIS_PATH"])
            if not data:
                return abort(404, message="{} cannot be found".format(join(arkid, premisid)))
            else:
                attach_filename, mimetype = get_an_attachment_filename(data[1])
                record_path = join(current_app.config["LIVEPREMIS_PATH"],
                                   str(identifier_to_path(arkid)), "arf", "pairtree_root",
                                   str(identifier_to_path(premisid)), "arf", "premis.xml")
                make_download_event(record_path, event_category,
                                    datetime.now().isoformat(), "SUCCESS",
                                    user, data[1].objid)
                resp = send_file(data[1].content_loc,
                                 as_attachment=True,
                                 attachment_filename=attach_filename,
                                 mimetype=mimetype)
                return resp
        except Exception as e:
            return jsonify(_EXCEPTION_HANDLER.handle(e).dictify())


# file retrieval endpoints
API.add_resource(GetAContentItem, "/<string:arkid>/<string:premisid>")

def only_alphanumeric(n_item):
    """
    fill_in_please
    """
    if _ALPHANUM_PATTERN.match(n_item):
        return True
    return False

def retrieve_record(identifier):
    """
    fill_in_please
    """
    identifier = secure_filename(identifier)
    if not only_alphanumeric(identifier):
        raise ValueError("Record identifiers must be alphanumeric.")
    r_test = "test"
    return r_test

