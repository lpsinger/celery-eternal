# Celery-Eternal

[![Build Status](https://travis-ci.org/lpsinger/celery-eternal.svg?branch=master)](https://travis-ci.org/lpsinger/celery-eternal)
[![Doc Build Status](https://readthedocs.org/projects/celery-eternal/badge/?version=latest)](http://celery-eternal.readthedocs.io/en/latest/)

celery-eternal provides a [Celery](http://www.celeryproject.org) task subclass
based on [celery-singleton](https://github.com/steinitzu/celery-singleton) and [celery.contrib.abortable](http://docs.celeryproject.org/en/latest/reference/celery.contrib.abortable.html) for jobs that should run forever.
