# -*- coding: utf-8 -*-

"""
Copyright (C) 2011 Dariusz Suchojad <dsuch at gefira.pl>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

# stdlib
from contextlib import closing
from traceback import format_exc
from uuid import uuid4

# lxml
from lxml import etree
from lxml.objectify import Element

# Zato
from zato.common import ZATO_OK
from zato.common.broker_message import MESSAGE_TYPE, DEFINITION
from zato.common.odb.model import Cluster, ConnDefAMQP
from zato.common.odb.query import def_amqp_list
from zato.server.service.internal import AdminService, ChangePasswordBase

class GetList(AdminService):
    """ Returns a list of AMQP definitions available.
    """
    class SimpleIO:
        required = ('cluster_id',)

    def handle(self):
        with closing(self.odb.session()) as session:
            definition_list = Element('definition_list')
            definitions = def_amqp_list(session, self.request.input.cluster_id, False)
            
            for definition in definitions:
    
                definition_elem = Element('definition')
                definition_elem.id = definition.id
                definition_elem.name = definition.name
                definition_elem.host = definition.host
                definition_elem.port = definition.port
                definition_elem.vhost = definition.vhost
                definition_elem.username = definition.username
                definition_elem.frame_max = definition.frame_max
                definition_elem.heartbeat = definition.heartbeat
    
                definition_list.append(definition_elem)
    
            self.response.payload = etree.tostring(definition_list)
        
class GetByID(AdminService):
    """ Returns a particular AMQP definition
    """
    class SimpleIO:
        required = ('id',)

    def handle(self):
        with closing(self.odb.session()) as session:

            definition = session.query(ConnDefAMQP.id, ConnDefAMQP.name, ConnDefAMQP.host,
                ConnDefAMQP.port, ConnDefAMQP.vhost, ConnDefAMQP.username,
                ConnDefAMQP.frame_max, ConnDefAMQP.heartbeat).\
                filter(ConnDefAMQP.id==self.request.input.id).\
                one()            
            
            definition_elem = Element('definition')
            
            definition_elem.id = definition.id
            definition_elem.name = definition.name
            definition_elem.host = definition.host
            definition_elem.port = definition.port
            definition_elem.vhost = definition.vhost
            definition_elem.username = definition.username
            definition_elem.frame_max = definition.frame_max
            definition_elem.heartbeat = definition.heartbeat
    
            self.response.payload = etree.tostring(definition_elem)
        
class Create(AdminService):
    """ Creates a new AMQP definition.
    """
    class SimpleIO:
        required = ('cluster_id', 'name', 'host', 'port', 'vhost', 
            'username', 'frame_max', 'heartbeat')

    def handle(self):
        input = self.request.input
        input.password = uuid4().hex
        
        with closing(self.odb.session()) as session:
            # Let's see if we already have an account of that name before committing
            # any stuff into the database.
            existing_one = session.query(ConnDefAMQP).\
                filter(ConnDefAMQP.cluster_id==Cluster.id).\
                filter(ConnDefAMQP.def_type=='amqp').\
                filter(ConnDefAMQP.name==input.name).\
                first()
            
            if existing_one:
                raise Exception('AMQP definition [{0}] already exists on this cluster'.format(input.name))
            
            created_elem = Element('def_amqp')
            
            try:
                def_ = ConnDefAMQP(None, input.name, 'amqp', input.host, input.port, input.vhost, 
                    input.username, input.password, input.frame_max, input.heartbeat,
                    input.cluster_id)
                session.add(def_)
                session.commit()
                
                created_elem.id = def_.id
                
                self.response.payload = etree.tostring(created_elem)
                
            except Exception, e:
                msg = "Could not create an AMQP definition, e=[{e}]".format(e=format_exc(e))
                self.logger.error(msg)
                session.rollback()
                
                raise 

class Edit(AdminService):
    """ Updates an AMQP definition.
    """
    class SimpleIO:
        required = ('id', 'cluster_id', 'name', 'host', 'port', 'vhost', 
            'username', 'frame_max', 'heartbeat')

    def handle(self):
        input = self.request.input
        
        with closing(self.odb.session()) as session:
            # Let's see if we already have an account of that name before committing
            # any stuff into the database.
            existing_one = session.query(ConnDefAMQP).\
                filter(ConnDefAMQP.cluster_id==Cluster.id).\
                filter(ConnDefAMQP.def_type=='amqp').\
                filter(ConnDefAMQP.id!=input.id).\
                filter(ConnDefAMQP.name==input.name).\
                first()
            
            if existing_one:
                raise Exception('AMQP definition [{0}] already exists on this cluster'.format(input.name))
            
            def_amqp_elem = Element('def_amqp')
            
            try:
                
                def_amqp = session.query(ConnDefAMQP).filter_by(id=input.id).one()
                old_name = def_amqp.name
                def_amqp.name = input.name
                def_amqp.host = input.host
                def_amqp.port = input.port
                def_amqp.vhost = input.vhost
                def_amqp.username = input.username
                def_amqp.frame_max = input.frame_max
                def_amqp.heartbeat = input.heartbeat
                
                session.add(def_amqp)
                session.commit()
                
                def_amqp_elem.id = def_amqp.id
                
                input.action = DEFINITION.AMQP_EDIT
                input.old_name = old_name
                self.broker_client.send_json(input, msg_type=MESSAGE_TYPE.TO_AMQP_CONNECTOR_SUB)
                
                self.response.payload = etree.tostring(def_amqp_elem)
                
            except Exception, e:
                msg = "Could not update the AMQP definition, e=[{e}]".format(e=format_exc(e))
                self.logger.error(msg)
                session.rollback()
                
                raise         
        
class Delete(AdminService):
    """ Deletes an AMQP definition.
    """
    class SimpleIO:
        required = ('id',)

    def handle(self):
        with closing(self.odb.session()) as session:
            try:
                def_ = session.query(ConnDefAMQP).\
                    filter(ConnDefAMQP.id==self.request.input.id).\
                    one()
                
                session.delete(def_)
                session.commit()

                msg = {'action': DEFINITION.AMQP_DELETE, 'id': self.request.input.id}
                self.broker_client.send_json(msg, msg_type=MESSAGE_TYPE.TO_AMQP_CONNECTOR_SUB)
                
            except Exception, e:
                session.rollback()
                msg = 'Could not delete the AMQP definition, e=[{e}]'.format(e=format_exc(e))
                self.logger.error(msg)
                
                raise
            
class ChangePassword(ChangePasswordBase):
    """ Changes the password of an HTTP Basic Auth definition.
    """
    def handle(self):
        
        def _auth(instance, password):
            instance.password = password
            
        return self._handle(ConnDefAMQP, _auth, 
            DEFINITION.AMQP_CHANGE_PASSWORD, msg_type=MESSAGE_TYPE.TO_AMQP_CONNECTOR_SUB, 
            payload=self.request.payload)
