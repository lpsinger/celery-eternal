from celery.bootsteps import StartStopStep
from celery.contrib.abortable import AbortableAsyncResult, AbortableTask
from celery.utils.log import get_task_logger
from celery_singleton import Singleton

__all__ = ('EternalTask',)

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

    Finally, you should also pass ``ignore_result=True``, because if the task
    runs until aborted, the return value is irrelevant.

    Here is an example eternal task that calls a fictional function
    `do_some_work()` in a loop::

        @app.task(base=EternalTask, bind=True, ignore_result=True)
        def long_running_task(self):
            while not self.is_aborted():
                do_some_work()

    """

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
