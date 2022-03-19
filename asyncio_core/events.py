class Handle:
    def __init__(self, callback, args, loop):
        self._loop = loop
        self._callback = callback
        self._args = args

    def _run(self):
        self._callback(*self._args)


class TimerHandle(Handle):
    def __init__(self, when, callback, args, loop):
        assert when is not None
        super().__init__(callback, args, loop)
        self._when = when
        self._scheduled = False
