from datetime import datetime
from flask import jsonify, Blueprint, request, send_file, make_response
from flask_restful import abort, Resource, Api, reqparse
from io import BytesIO
from os import listdir
from os.path import join, exists
from werkzeug.utils import secure_filename
from re import compile as regex_compile
from xml.etree import ElementTree as ET
import requests
from sys import stderr
from urllib.parse import ParseResult

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
    event_message = "{} downlooaded the content".format(user)
    new_download_event = build_a_premis_event(event_category, event_date, event_status, event_message, user, objid)
    print(path_to_record)
    print(new_download_event)
    was_it_written = add_event_to_premis_record(path_to_record, new_download_event)
    print(was_it_written)
    return was_it_written

def load_json_from_url(url):
    data = requests.get(url)
    return r.json()

def construct_url_to_get_a_user(userid):
    a_url = ParseResult(scheme="https", netloc="y2.lib.uchicago.edu", path="/ldragents/agents/" + userid.strip(), query="term=" + user_query)
    return a_url.geturl()

def construct_url_to_search_for_matches(user_query):
    a_url = ParseResult(scheme="https", netloc="y2.lib.uchicago.edu", path="/ldragents/agents", query="term=" + user_query.strip())
    return a_url.geturl()

def get_or_create_new_agent(user_query):
    searching_user = construct_url_to_find_user(host_name, user_query)
    pot_user_data = load_json_from_url(searching_user)

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
        try:
            user = request.headers.get("uid") if request.headers.get("uid") else "anonymous"
            event_category = "anonymous download" if user == "anonymous" else "restricted download"
            data = get_object_halves(arkid, premisid, current_app.config["LONGTERMSTORAGE_PATH"], current_app.config["LIVEPREMIS_PATH"])
            if not data:
                return abort(404, message="{} cannot be found".format(join(arkid, premisid)))
            else:
                new_download_event = build_a_premis_event(event_category,
                                                          datetime.now().isoformat(),
                                                          "SUCCESS", "{} downloaded this content".format(user),
                                                          user, data[1].objid)
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
        except Exception as e:
            return jsonify(_EXCEPTION_HANDLER.handle(e).dictify())

class GetAPremisItem(Resource):
    """
    fill_in_please
    """
    def get(self, arkid, premisid):
        """
        Get the whole record
        """
        from flask import current_app
        try:
            data = get_data_half_of_object(arkid, premisid, current_app.config["LIVEPREMIS_PATH"])
            if not data:
                return abort(404, message="{} premis record cannot be found.".format(join(arkid, premisid)))
            else:
                resp = send_file(data[0],
                                 as_attachment=True,
                                 attachment_filename=premisid + ".xml",
                                 mimetype="application/xml")
                return resp
        except Exception as e:
            return jsonify(_EXCEPTION_HANDLER.handle(e).dictify())

class GetTechMetadataList(Resource):
    """
    fill_in_please
    """
    def get(self, arkid, premisid):
        """
        Get the whole record
        """
        from flask import current_app
        data = get_content_half_of_object(arkid, premisid,
                                          current_app.config["LONGTERMSTORAGE_PATH"])
        try:
            if data:
                content_directory = dirname(data[0])
                content_directory_contents = listdir(content_directory)
                metadata_in_directory = [x for x in content_directory_contents if "premis" not in  x and "content.file" not in x and "0=" not in x]
                output = {}
                for i in range(len(metadata_in_directory)):
                    output[str(i)] = {"label": metadata_in_directory[i].split('.')[0], "loc": join("/", arkid, premisid, "techmds/", str(i))}
                resp = APIResponse("success", data={"technicalmetadata_list": output})
                return jsonify(resp.dictify())
            else:
                return abort(404, message="{} could not be found.".format(join(arkid, premisid)))
        except Exception as e:
            return jsonify(_EXCEPTION_HANDLER.handle(e).dictify())

class GetASpecificTechnicalMetadata(Resource):
    def get(self, arkid, premisid, numbered_request):
        """
        Get the whole record
        """
        from flask import current_app
        try:
            just_one_side_of_thing = get_content_half_of_object(arkid, premisid,
                                                                current_app.config["LONGTERMSTORAGE_PATH"])
            if just_one_side_of_thing:
                content_directory = dirname(just_one_side_of_thing[0])
                content_directory_contents = listdir(content_directory)
                metadata_in_directory = [x for x in content_directory_contents if "premis" not in  x and "content.file" not in x and "0=" not in x]
                output = {}
                for i in range(len(metadata_in_directory)):
                    output[str(i)] = {"label": metadata_in_directory[i].split('.')[0], "loc": join("/", arkid, premisid, "techmds/", str(i))}
                matched_mdata = output.get(str(numbered_request))
                if matched_mdata:
                    mdata_file_basename = [x for x in content_directory_contents if matched_mdata.get("label") in x][0]
                    mdata_filepath = join(content_directory, mdata_file_basename)
                    if 'xml' in mdata_file_basename:
                        mimetype = 'application/xml'
                        resp = send_file(mdata_filepath,
                                         as_attachment=True,
                                         attachment_filename=premisid+".xml",
                                         mimetype=mimetype)
                    else:
                        mimetype = 'plain/text'
                        resp = send_file(mdata_filepath,
                                         as_attachment=True,
                                         attachment_filename=premisid+".txt",
                                         mimetype=mimetype)
                    return resp
                else:
                    resp = APIResponse("fail", errors=["{}/{} was not found".format(join(arkid, premisid), numbered_request)])
            else:
                return abort(404, message="{} could not be found.".format(join(arkid, premisid)))
        except Exception as e:
            return jsonify(_EXCEPTION_HANDLER.handle(e).dictify())

class GetPresformsList(Resource):
    """
    fill_in_please
    """
    def get(self, arkid, premisid):
        """
        Get the whole record
        """
        from flask import current_app
        try:
            data = get_data_half_of_object(arkid, premisid, current_app.config["LIVEPREMIS_PATH"])
            related_objects = data[1].related_objects
            output = {}
            tally = 1
            for n_object in related_objects:
                output[str(tally)] = {"loc":join("/", arkid, n_object)}
            resp = APIResponse("success", data={"presforms": output})
            return jsonify(resp.dictify())
        except Exception as e:
            return jsonify(_EXCEPTION_HANDLER.handle(e).dictify())

class GetASpecificPresform(Resource):
    def get(self, arkid, premisid, numbered_request):
        """a method to to retrieve one particular presform related to the identified object

        __Args__
        1. arkid (str): an accession identifier
        2. premisid (str): an object identifier
        3. numbered_request (int): a numbered related object that is desired
        """
        from flask import current_app
        try:
            user = request.headers.get("uid") if request.headers.get("uid") else "anonymous"
            event_category = "anononymous download" if user == "anonymous" else "restricted download"
            data = get_object_halves(arkid, premisid, current_app.config["LIVEPREMIS_PATH"])
            related_objects = data[1].related_objects
            output = {}
            tally = 1
            for n_object in related_objects:
                output[str(tally)] = {"loc":join("/", arkid, n_object)}
            choice = output.get(numbered_request)
            if choice:
                presform = get_object_halves(arkid, choice.get("loc").split("/")[2],
                                             current_app.config["LONGTERMSTORAGE_PATH"])
                if presform:
                    record_path = join(current_app.config["LIVEPREMIS_PATH"],
                                       str(identifier_to_path(arkid)), "arf", "pairtree_root",
                                       str(identifier_to_path(presform[1].objid)), "arf", "premis.xml")
                    make_download_event(record_path, event_category,
                                        datetime.now().isoformat(), "SUCCESS",
                                        user, presform[1].objid)
                    attach_filename, mimetype = get_an_attachment_filename(data)
                    resp = send_file(content_item,
                                     as_attachment=True,
                                     attachment_filename=attach_filename,
                                     mimetype=mimetype)
                    return jsonify(resp.dictify())
                else:
                    return abort(404,  message="could not find the {}".format(join(arkid, presform.objid)))
            else:
                return abort(404, message="could not find {}".format(join(arkid, premisid)))
        except Exception as e:
            return jsonify(_EXCEPTION_HANDLER.handle(e).dictify())

class ConvenienceToGetLastPresformOrContent(Resource):
    def get(self, arkid, premisid):
        """a method to get the last  related object if there is one or the content file

        __Args__
        1. arkid (str): an accession identifier
        2. premisid (str): an object identifier
        """
        from flask import current_app
        try:
            user = request.headers.get("uid") if request.headers.get("uid") else "anonymous"
            event_category = "anononymous download" if user == "anonymous" else "restricted download"
            data = get_object_halves(arkid, premisid, current_app.config["LONGTERMSTORAGE_PATH"], current_app.config["LIVEPREMIS_PATH"])
            related_objects = data[1].related_objects

            if len(related_objects) > 0:
                output = {}
                tally = 1
                for n_object in related_objects:
                    output[str(tally)] = {"loc":join("/", arkid, n_object)}
                last_related_object = list(output.keys())[-1]
                choice = output.get(last_related_object)
                if choice:
                    presform = get_object_halves(arkid, choice.get("loc").split("/")[2],
                                                 current_app.config["LONGTERMSTORAGE_PATH"])
                    if presform:
                        record_path = join(current_app.config["LIVEPREMIS_PATH"],
                                          str(identifier_to_path(arkid)), "arf", "pairtree_root",
                                          str(identifier_to_path(presform[1].objid)), "arf", "premis.xml")
                        make_download_event(record_path, event_category,
                                            datetime.now().isoformat(), "SUCCESS",
                                            user, presform[1].objid)
                        attach_filename, mimetype = get_an_attachment_filename(presform[1])
                        resp = send_file(presform[1].content_loc,
                                         as_attachment=True,
                                         attachment_filename=attach_filename,
                                         mimetype=mimetype)
                        return resp
                    else:
                        return abort(404,  message="could not find the {}".format(join(arkid, presform.objid)))
                else:
                    return abort(404, message="could not find {}".format(join(arkid, premisid)))
            else:
                record_path = join(current_app.config["LIVEPREMIS_PATH"],
                                   str(identifier_to_path(arkid)), "arf", "pairtree_root",
                                   str(identifier_to_path(premisid)), "arf", "premis.xml")
                make_download_event(record_path, event_category,
                                    datetime.now().isoformat(), "SUCCESS",
                                    user, data[1].objid)
                attach_filename, mimetype = get_an_attachment_filename(data[1])
                resp = send_file(data[1].content_loc,
                                 as_attachment=True,
                                 attachment_filename=attach_filename,
                                 mimetype=mimetype)
                return resp
        except Exception as e:
            return jsonify(_EXCEPTION_HANDLER.handle(e).dictify())


# file retrieval endpoints
API.add_resource(GetAContentItem, "/<string:arkid>/<string:premisid>/content")
API.add_resource(GetAPremisItem, "/<string:arkid>/<string:premisid>/premis")
API.add_resource(GetTechMetadataList, "/<string:arkid>/<string:premisid>/techmds")
API.add_resource(GetASpecificTechnicalMetadata, "/<string:arkid>/<string:premisid>/techmds/<int:numbered_request>")
API.add_resource(GetPresformsList, "/<string:arkid>/<string:premisid>/presforms")
API.add_resource(GetASpecificPresform, "/<string:arkid>/<string:premisid>/presforms/<int:numbered_request>")
API.add_resource(ConvenienceToGetLastPresformOrContent, "/<string:arkid>/<string:premisid>/presform")

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

