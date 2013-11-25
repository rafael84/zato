# -*- coding: utf-8 -*-

"""
Copyright (C) 2013 Dariusz Suchojad <dsuch at zato.io>

Licensed under LGPLv3, see LICENSE.txt for terms and conditions.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

# stdlib
import logging

# Zato
from zato.admin.web.forms.message.elem_path import CreateForm, EditForm
from zato.admin.web.views import CreateEdit, Delete as _Delete, Index as _Index, method_allowed
from zato.common.odb.model import ElemPath

logger = logging.getLogger(__name__)

class Index(_Index):
    method_allowed = 'GET'
    url_name = 'message-elem-path'
    template = 'zato/message/elem_path.html'
    service_name = 'zato.message.elem-path.get-list'
    output_class = ElemPath

    class SimpleIO(_Index.SimpleIO):
        input_required = ('cluster_id',)
        output_required = ('id', 'name', 'value')
        output_repeated = True

    def handle(self):
        return {
            'create_form': CreateForm(),
            'edit_form': EditForm(prefix='edit')
        }

class _CreateEdit(CreateEdit):
    method_allowed = 'POST'

    class SimpleIO(CreateEdit.SimpleIO):
        input_required = ('name', 'value')
        output_required = ('id', 'name')

    def success_message(self, item):
        return 'Successfully {0} the ElemPath [{1}]'.format(self.verb, item.name)

class Create(_CreateEdit):
    url_name = 'message-elem-path-create'
    service_name = 'zato.message.elem-path.create'

class Edit(_CreateEdit):
    url_name = 'message-elem-path-edit'
    form_prefix = 'edit-'
    service_name = 'zato.message.elem-path.edit'

class Delete(_Delete):
    url_name = 'message-elem-path-delete'
    error_message = 'Could not delete the ElemPath'
    service_name = 'zato.message.elem-path.delete'
