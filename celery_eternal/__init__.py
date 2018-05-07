import errno
import os
import signal
import time

import billiard
from celery.bootsteps import StartStopStep
from celery.contrib.abortable import AbortableAsyncResult, AbortableTask
from celery.utils.log import get_task_logger
from celery_singleton import Singleton

__all__ = ('EternalTask', 'EternalProcessTask')

# Logging
log = get_task_logger(__name__)


class AbortStep(StartStopStep):
    """Boot step to abort all tasks on shutdown."""
    requires = {'celery.worker.components:Pool'}

    def stop(self, worker):
        for request in worker.state.active_requests:
            AbortableAsyncResult(request.task_id).abort()


class EternalTask(AbortableTask, Singleton):
    """Base class for a task that should run forever, and should be restarted
    if it ever exits. The task should periodically check
    :meth:`~celery.contrib.abortable.AbortableTask.is_aborted`
    and exit gracefully if it is set. During a warm shutdown, we will attempt
    to abort the task.

    Example
    -------

    To create an abortable task, call the :meth:`~celery.Celery.task` decorator
    with the keyword argument ``base=EternalTask``.

    Generally, you should also pass ``bind=True`` so that your task function
    has access to the :class:`~celery.app.task.Task` instance and can call
    ``self.is_aborted()``.

    Here is an example eternal task that calls a fictional function
    `do_some_work()` in a loop::

        @app.task(base=EternalTask, bind=True, ignore_result=True)
        def long_running_task(self):
            while not self.is_aborted():
                do_some_work()

    """

    ignore_result = True

    @classmethod
    def on_bound(cls, app):
        app.add_periodic_task(1.0, cls)
        app.steps['worker'].add(AbortStep)

    def __exit_message(self):
        if self.is_aborted():
            log.info('Eternal process exited early due to abort')
        else:
            log.error('Eternal process exited early!')

    def on_failure(self, *args, **kwargs):
        super(EternalTask, self).on_failure(*args, **kwargs)
        self.__exit_message()

    def on_success(self, *args, **kwargs):
        super(EternalTask, self).on_success(*args, **kwargs)
        self.__exit_message()


class EternalProcessTask(EternalTask):
    """Base class for an eternal task that runs in a subprocess.

    This is useful for tasks that do not check the method
    :meth:`~celery.contrib.abortable.AbortableTask.is_aborted` but can be
    stopped by a :obj:`KeyboardInterrupt` triggered by receving the signal
    :data:`SIGINT`.

    The task itself launches and supervises a subprocess that runs the
    function. The subprocess has Python's default :data:`SIGINT` handler
    installed.
    """

    def __call__(self, *args, **kwargs):
        process = billiard.Process(target=self.run, *args, **kwargs)
        old_handler = signal.signal(signal.SIGINT, signal.default_int_handler)
        try:
            process.start()
        finally:
            signal.signal(signal.SIGINT, old_handler)
        while process.is_alive() and not self.is_aborted():
            time.sleep(1)
        if self.is_aborted():
            try:
                os.kill(process.pid, signal.SIGINT)
            except OSError as e:
                if e.errno != errno.ESRCH:
                    log.exception('Failed to kill subprocess')
        process.join(1)
        process.terminate()
