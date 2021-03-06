from app import app
from flask import Flask, jsonify, request, make_response, send_from_directory 
from registry import Registry
import json
import global_vars
from analysis.data import ESServer as ES

R = Registry()
####
# Load the main html file
@app.route('/', methods=['GET','POST'])
def root():
    return send_from_directory('app/static', 'index.html')

@app.route('/static/<path:path>')
def resources_main(path):
    return send_from_directory('app/static', path)

@app.route('/img/<path:path>', methods=['GET'])
def resources_img(path):
    return send_from_directory('app/static/img', path)

@app.route('/css/<path:path>', methods=['GET'])
def resources_css(path):
    return send_from_directory('app/static/css', path)

@app.route('/js/<path:path>', methods=['GET'])
def resources_js(path):
    return send_from_directory('app/static/js', path)

####
# Return a list of the modules we have loaded

@app.route('/api/v1.0/modules/list', methods=['GET'])
def get_modules_list():
    mlist = []
    for m in R.GetModules():
        mlist.append({
            "name": m.name,
            "description": m.description,
            "id": m.id,
            "options": m.GetOptions()
            })
    return make_response(json.dumps(mlist))

####
# Return a list of custom log importers we have loaded

@app.route('/api/v1.0/importers/list', methods=['GET'])
def get_importers_list():
    ilist = []
    for i in R.GetImporters():
        ilist.append({
            "name": i.name,
            "description": i.description,
            "id": i.id,
            "options": i.GetOptions()
            })
    return make_response(json.dumps(ilist)) 

####
# Set an option in a module, if global call R.SetGlobal

@app.route('/api/v1.0/module/<int:module_id>/set', methods=['POST'])
def set_module_option(module_id):
    if not request.json:
        print("where's my json yo?")
        return jsonify({'success': False, 'reason': "I was expecting json."})
    
    dat = request.json 
    for k in dat:
        if k in global_vars.options:
            R.SetGlobal(k, request.json[k])
            continue
        if R.GetModules()[module_id].SetOption(k, dat[k]):
            print("Successfully set option ", k)
        else:
            print("Failed to set option ", k)

    return jsonify({'success': True})

####
# Run a module

@app.route('/api/v1.0/module/<int:module_id>/run', methods=['GET'])
def run_module(module_id):
    #try:
    R.GetModules()[module_id].RunModule()
    return jsonify({'success': True})
    #except Exception, err:
    #    return jsonify({'success': False, "reason": str(err)})


####
# Set an option for an importer, if global call R.SetGlobal

@app.route('/api/v1.0/importer/<int:importer_id>/set', methods=['POST'])
def set_importer_option(importer_id):
    if not request.json:
        return jsonify({'success': False, 'reason': "I was expecting json."})

    for k in request.json:
        if k in global_vars.options:
            R.SetGlobal(k, request.json[k])
            continue
        if not R.GetImporters()[importer_id].SetOption(k, request.json[k]):
            return jsonify({'success': False})
    return jsonify({'success': True})

####
# Run an importer

@app.route('/api/v1.0/importer/<int:importer_id>/run', methods=['GET'])
def run_importer(importer_id):
    if R.GetImporters()[importer_id].Read():
        return jsonify({'success': True})
    return jsonify({'success': False})

####
# Set the customer global

@app.route('/api/v1.0/customer/set', methods=['POST'])
def set_customer():
    if not request.json["customer"]:
        return jsonify({'success': False, 
            'reason': 'I expected json to contain customer'})

    R.SetGlobal("customer", request.json["customer"])
    return jsonify({'success': True})

####
# Set the address of elasticsearch

# TODO: This should support esservers that require authentication
@app.route('/api/v1.0/esserver/set', methods=['POST'])
def set_server():
    if not request.json["server"]:
        return jsonify({'success': False, 
            'reason': 'I expected json to contain server'})
    R.SetGlobal("server", request.json["server"])
    return jsonify({'success': True})

####
# Get results out of the ES database
@app.route('/api/v1.0/results/list', methods=['GET'])
def get_results():
    opts = R.GetModules()[0].GetOptions()
    cust = ""
    server = ""
    for opt in opts:
        if opt["name"] == "customer":
            cust = opt["value"]
        if opt["value"] == "server":
            server = opt["value"]

    fields = ["src","dst","proto"]
    scroll_id = ""
    scroll_len = 1000
    es = ES([server])
    hits, scroll_id, scroll_size = es.get_data( cust, "results", fields, [], [], scroll_len, "")
    retval = []
    for hit in hits:
        try:
            temp = {
                    "src": hit['fields']["src"][0],
                    "dst":  hit['fields']["dst"][0],
                    "result_type": hit['fields']["result_type"][0]
                    }
            retval.append(temp)
        except Exception, err:
            print("Pull error: ", str(err))
            continue
    return make_response(json.dumps(retval))
