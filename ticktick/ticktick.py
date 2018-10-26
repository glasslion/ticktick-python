# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals, print_function
from datetime import datetime

from addict import Dict
import arrow
import requests
import six
from six.moves.urllib.parse import urlencode

from .objectid import ObjectId


LOGIN_URL = 'https://ticktick.com/api/v2/user/signon?wc=true&remember=true'
BATCH_CHECK_URL = 'https://ticktick.com/api/v2/batch/check/0'
BATCH_TASK_URL = 'https://api.ticktick.com/api/v2/batch/task'
TASK_URL = 'https://api.ticktick.com/api/v2/task'
ALL_COMPLETED_URL = 'https://api.ticktick.com/api/v2/project/all/completedInAll/'

TIME_FORMAT = '%Y-%m-%d %H:%M:%S'


class TickTask(Dict):
    def __init__(self, *args, **kwargs):
        super(TickTask, self).__init__(self, *args, **kwargs)
        # Avoid conflicts between dict key 'items' and dict method 'items'
        items = self.get('items', [])
        if items:
            self.subtasks = [TickTask(item) for item in items]

    def text_view(self, show_list=False, show_subs=True):
        TAG = '🏷'
        COMPLETED = '✔'
        UNCOMPLETED = '❏'
        MARGIN = '\t\t'

        text = '{state} {title}'.format(
            state=COMPLETED if self.is_completed else UNCOMPLETED,
            title=self.title,
        )

        if show_list and self.list:
            text += '{}#{}'.format(MARGIN, self.list.name)

        if self.tags:
            text += MARGIN + ' '.join(TAG+tag for tag in self.tags)

        if show_subs and self.subtasks:
            sub_texts = [MARGIN + item.text_view() for item in self.subtasks if item.title]
            text += '\n'+ '\n'.join(sub_texts)
        return text

    @property
    def is_completed(self):
        # Status: 0 uncompleted, 1 subtask completed, 2 completed
        return self.status > 0


class TickTick(object):
    def __init__(self,  username, password, expire=600, auto_login=True):
        self.username = username
        self.password = password
        self.expire = expire
        if auto_login:
            self._login()

    def _login(self):
        """
        Create a requests session and login the user
        """
        self._session = requests.Session()
        r = self._session.post(
            url=LOGIN_URL,
            json={
                'username': self.username,
                'password': self.password,
            }
        )
        return r

    def fetch(self, from_=None, to=None, limit=100):
        self.fetch_uncompleted()
        self.fetch_completed(from_, to, limit)
        self.tasks = self.completed + self.uncompleted


    def fetch_uncompleted(self):
        r = self._session.get(BATCH_CHECK_URL)
        data = r.json()

        self.lists = [Dict(item) for item in data['projectProfiles']]
        self.list_lookup = {item.id:item for item in self.lists}
        self.inbox = Dict({
            'id': data['inboxId'],
            'name': 'Inbox',
            'sortOrder': 0,
        })
        self.list_lookup[self.inbox.id] = self.inbox

        self.tags = [Dict(item) for item in data['tags']]
        self.uncompleted = [TickTask(item) for item in data['syncTaskBean']['update']]
        for item in self.uncompleted:
            self.populate_task(item)

    def fetch_completed(self, from_, to, limit):
        from_qs = from_.strftime(TIME_FORMAT) if from_ else ''
        to_qs = to.strftime(TIME_FORMAT) if to else ''
        qs = urlencode({
            'from': from_qs,
            'to': to_qs,
            'limit': limit,
        })
        r = self._session.get(ALL_COMPLETED_URL + '?' + qs)
        data = r.json()
        self.completed = [TickTask(item) for item in data]
        for item in self.completed:
            self.populate_task(item)

    def query(self, filter=None, order_by=None):
        if filter is None:
            filter = lambda x: True
        items = [task for task in self.tasks if filter(task)]
        if order_by is None:
            order_by = lambda x: x.sortOrder
        items.sort(key=order_by)
        return items

    def populate_task(self, task):
        # Date / Time
        for attr, value in task.items():
            if value and (attr.endswith('Date') or attr.endswith('Time')):
                try:
                    task[attr] = arrow.get(value).to(task.timeZone).datetime.replace(tzinfo=None)
                except:
                    pass
        task['list'] = self.list_lookup[task.projectId]

    def query_inbox(self):
        return self.query(lambda x:x.list.name == 'Inbox')

    def query_today(self):
        def filter(task):
            today = arrow.now().floor('day').to('local').datetime.replace(tzinfo=None)
            if task.is_completed:
                if task.completedTime > today:
                    return True
                else:
                    return False
            if task.startDate and task.startDate <= today:
                return True
            return False
        return self.query(filter)

    def guess_timezone(self):
        """
        Guess user timezone from existing tasks
        """
        for task in self.tasks:
            if task.timeZone:
                return task.timeZone

    def get_list_id(self, name):
        for lst in self.lists:
            if lst.name == name:
                return lst.id

    def add(self, title, list_name=None, extra_kwargs=None):
        if not hasattr(self, 'tasks'):
            self.fetch()
        if list_name:
            list_id = self.get_list_id(name=list_name)
        else:
            list_id = self.inbox.id
        task_id = str(ObjectId())
        task = {
            'title': title,
            'timeZone': self.guess_timezone(),
            'id': task_id,
            'projectId': list_id,
        }
        if extra_kwargs:
            task.update(extra_kwargs)
        data = {'add': [task]}
        r = self._session.post(BATCH_TASK_URL, json=data)
        return task_id

    def delete(self, task_id, list_id):
        task = {
            'taskId': task_id,
            'projectId': list_id,
        }
        r = self._session.delete(TASK_URL, json=[task])
