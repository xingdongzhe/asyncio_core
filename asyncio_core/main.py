import time

from base_events import BaseEventLoop

from tasks import sleep


async def cor():
    print('enter cor ...', time.time())
    await sleep(2, loop=loop)
    print('exit cor ...', time.time())

    return 'cor'


loop = BaseEventLoop()
task = loop.create_task(cor(), name='my_task')
rst = loop.run_until_complete(task)
print(rst)
