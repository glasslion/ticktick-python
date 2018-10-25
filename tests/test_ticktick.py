#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for `ticktick` package."""

import os
from datetime import datetime
import pytest

from ticktick import TickTick



def test_login():
    tt = TickTick(
        username=os.environ['TICKTICK_USERNAME'],
        password=os.environ['TICKTICK_PASSWORD'],
        auto_login=False,
    )
    r = tt._login()
    assert r.status_code == 200


def test_fetch():
    tt = TickTick(
        username=os.environ['TICKTICK_USERNAME'],
        password=os.environ['TICKTICK_PASSWORD'],
    )
    tt.fetch(datetime(2018, 10, 1), datetime(2018, 10, 31), 50)
    assert len(tt.tasks) > 0
    assert len(tt.tasks) == len(tt.completed) +  len(tt.uncompleted)

def test_add_delete():
    tt = TickTick(
        username=os.environ['TICKTICK_USERNAME'],
        password=os.environ['TICKTICK_PASSWORD'],
    )
    task_id = tt.add('API add test')
    assert len(task_id) == 24
    assert tt.guess_timezone() == 'Asia/Shanghai'
    tt.delete(task_id, tt.inbox.id)
