import inspect
from asyncio import base_futures, futures, coroutines
from asyncio.tasks import _wrap_awaitable

_PENDING = base_futures._PENDING
_CANCELLED = base_futures._CANCELLED
_FINISHED = base_futures._FINISHED

from events import TimerHandle


class Future:
    _state = _PENDING
    _result = None
    _exception = None
    _loop = None

    _asyncio_future_blocking = False

    def __init__(self, *, name=None, loop=None):
        self.name = name
        self._loop = loop
        self._callbacks = []  # List[Function]

    def set_result(self, result):
        self._result = result
        self._state = _FINISHED

        callbacks = self._callbacks[:]
        self._callbacks[:] = []
        for callback in callbacks:
            self._loop.call_soon(callback, self)

    def __iter__(self):
        if not self._state != _PENDING:
            self._asyncio_future_blocking = True

        yield self  # This tells Task to wait for completion.
        assert self._state == _FINISHED, "yield from wasn't used with future"
        return self._result  # May raise too.

    __await__ = __iter__

    def __str__(self):
        return self.name

    def add_done_callback(self, fn):
        self._callbacks.append(fn)


def ensure_future(coro_or_future, *, loop=None):
    """Wrap a coroutine or an awaitable in a future.

    If the argument is a Future, it is returned directly.
    """
    if futures.isfuture(coro_or_future):
        if loop is not None and loop is not coro_or_future._loop:
            raise ValueError('loop argument must agree with Future')
        return coro_or_future
    elif coroutines.iscoroutine(coro_or_future):
        task = loop.create_task(coro_or_future)

        return task
    elif inspect.isawaitable(coro_or_future):
        return ensure_future(_wrap_awaitable(coro_or_future), loop=loop)
    else:
        raise TypeError('An asyncio.Future, a coroutine or an awaitable is '
                        'required')


class Task(Future):
    def __init__(self, coro, *, name=None, loop=None):
        super().__init__(loop=loop, name=name)
        self._coro = coro
        self._loop.call_soon(self._step)

    def _step(self, exc=None):
        coro = self._coro

        try:
            result = coro.send(None)
        except StopIteration as exc:
            self.set_result(exc.value)
        else:
            result.add_done_callback(self._wakeup)

    def _wakeup(self, future):
        self._step()


def _set_result_unless_cancelled(fut: Future, result):
    fut.set_result(result)


async def sleep(delay, result=None, *, loop=None):
    future = Future(loop=loop)
    loop.call_at(delay, _set_result_unless_cancelled, future, result)
    return await future
