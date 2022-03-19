import heapq
from collections import deque
from selectors import DefaultSelector
import sys
import time

from tasks import Task, Future
import tasks, events
from events import Handle


def _run_until_complete_cb(fut: Future):
    exc = fut._exception
    if (isinstance(exc, BaseException)
            and not isinstance(exc, Exception)):
        # Issue #22429: run_forever() already finished, no need to
        # stop it.
        return
    fut._loop.stop = True


class BaseEventLoop:
    def __init__(self):
        self._ready = deque()  # List[Handle]
        self._scheduled = []  # List[TimerHandle]，是一个最小二叉堆
        self._selector = DefaultSelector()
        self.stop = False

    def run_until_complete(self, future):
        future = tasks.ensure_future(future, loop=self)
        future.add_done_callback(_run_until_complete_cb)
        self.run_forever()
        return future._result

    def run_forever(self):
        while True:
            self._run_once()
            if self.stop:
                break

    def create_task(self, coro, *, name=None):
        task = tasks.Task(coro, loop=self, name=name)
        return task

    def _run_once(self):
        if self._ready:
            timeout = 0
        elif self._scheduled:
            timeout = self._scheduled[0]._when
        else:
            timeout = 0
        if sys.platform == 'win32':
            time.sleep(timeout)
        else:
            event_list = self._selector.select(timeout)
        # self._process_eventsts(event_list)
        while self._scheduled:
            handle = heapq.heappop(self._scheduled)
            handle._scheduled = False
            self._ready.append(handle)

        n_todo = len(self._ready)
        for i in range(n_todo):
            handle: Handle = self._ready.popleft()
            handle._run()

    def call_soon(self, callback, *args):
        handle = events.Handle(callback, args, self)
        self._ready.append(handle)
        return handle

    def call_at(self, when, callback, *args):
        timer = events.TimerHandle(when, callback, args, self)
        heapq.heappush(self._scheduled, timer)
        timer._scheduled = True
        return timer
