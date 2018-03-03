Celery-Eternal Documentation
============================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

Celery-Eternal provides a Celery_ task subclass for jobs that should run
forever, based on celery-singleton_ and celery.contrib.abortable_.

Like celery-singleton_, your app **must use a redis result backend**.

.. _Celery: http://www.celeryproject.org
.. _celery-singleton: https://github.com/steinitzu/celery-singleton
.. _celery.contrib.abortable: http://docs.celeryproject.org/en/latest/reference/celery.contrib.abortable.html

API
---

.. autoclass:: celery_eternal.EternalTask
.. autoclass:: celery_eternal.EternalProcessTask
