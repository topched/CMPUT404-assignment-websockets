#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import flask
from flask import Flask, request, redirect, url_for, render_template
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

clients = list()

def send_all(msg):
    for client in clients:
        client.put(msg)

def send_all_json(obj):
    send_all(json.dumps(obj))

class Client:
    def __init__(self):
        self.queue = queue.Queue()

    def put(self, v):
        self.queue.put_nowait(v)

    def get(self):
        return self.queue.get()

class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()
        
    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
        self.update_listeners( entity )

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            listener(entity, self.get(entity))

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())
    
    def world(self):
        return self.space

myWorld = World()        

def set_listener( entity, data ):
    ''' do something with the update ! '''

myWorld.add_set_listener( set_listener )

#redirect to the index        
@app.route('/')
def hello():
    return flask.redirect("/static/index.html")


def read_ws(ws,client):
    '''A greenlet function that reads from the websocket and updates the world'''
    # XXX: TODO IMPLEMENT ME
    
    try:
        while True:
            msg = ws.recieve()
            print "WS RECV: %s" % msg
            if (msg is not None):

                '''Need to update the world here'''
                packet = json.loads(msg)
                send_all_json( packet )
            else:
                break;
    except:
        '''Done'''


    return None

@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''
    
    client = Client()
    clients.append(client)
    g = gevent.spawn( read_ws, ws, client)
    print "Subscribing"
    try:
        while True:
            # block here
            msg = client.get()
            print "Got a message"
            ws.send(msg)

    except Exception as e:
        print "WS Error %s" % e

    finally:
        clients.remove(client)
        gevent.kill(g)


    return None

'''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
def flask_post_json():
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data != ''):
        return json.loads(request.data)
    else:
        return json.loads(request.form.keys()[0])

#update a specific entity
@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    
    tmp = flask_post_json()

    for key in tmp.keys():
        myWorld.update(entity, key, tmp[key])

    return json.dumps(myWorld.get(entity))

#return the world
@app.route("/world", methods=['POST','GET'])    
def world():
    return json.dumps(myWorld.world())

#return a specific entity
@app.route("/entity/<entity>")    
def get_entity(entity):
    return json.dumps(myWorld.get(entity))

#clear to world then return a blank world
@app.route("/clear", methods=['POST','GET'])
def clear():
    myWorld.clear()
    return json.dumps(myWorld.world())


if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
