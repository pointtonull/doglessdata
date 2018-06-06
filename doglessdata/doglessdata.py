#!/usr/bin/env python
'''
Simple interface for reporting metrics to DataDog.
'''

from __future__ import print_function

from contextlib import contextmanager
from functools import wraps
import os
import re
import time

REGEX_NAME = re.compile(r"(?P<region>[\w-]+\d+)"
                        r"[_-](?P<stack>[a-z]+[_-][a-z]+(?:[_-]staging)?)"
                        r"[_-](?P<name>.+)")

class DataDogMetrics(object):
    '''
    Datadog supports printing to stdout to report metrics.
    This only gives us counts and gauges:
        https://www.datadoghq.com/blog/monitoring-lambda-functions-datadog

    Another method would be via the API but that one only supports gauges and
    requires auth, which I'd rather not do until they've added support for
    histograms and counts.
    '''

    OK        =  0
    WARNING   =  1
    CRITICAL  =  2
    UNKNOWN   =  3


    def __init__(self, global_tags=[]):
        """
        """

        lambda_name = os.environ.get('AWS_LAMBDA_FUNCTION_NAME', "")
        if lambda_name:
            match = REGEX_NAME.match(lambda_name)
            if match:
                match = match.groupdict()
                lambda_name = match["name"]
                stack = match["stack"]
            else:
                stack = "no_stack"
#                 print("failed to match lambda_name: %s" % lambda_name)
        else:
            stack = "no_stack"

        default_tags = [] + global_tags
        default_tags.append("h:%s" % lambda_name)
        default_tags.append("host:%s" % lambda_name)
        default_tags.append("stack:%s" % stack)
        default_tags.append("lambda")

        aws_region = os.environ.get('AWS_REGION', "")
        if aws_region:
            default_tags.append("aws_region:%s" % aws_region)

        self._default_tags = default_tags


    def _get_tags(self, tags=None, metric_name=None):
        """
        Extend tags to cover new insights given by the names
        """
        tags = tags or []
        tags += self._default_tags
        if metric_name:
            name_tags = [".".join(metric_name.split(".")[:i+1])
                         for i in range(len(metric_name.split(".")))]
            tags += name_tags
        return list(set(tags))


    def increment(self, metric_name, count=1, tags=None):
        '''
        Incr - Increment a counter metric, providing a count of occurances per
               second
        '''
        tags = self._get_tags(tags, metric_name)
        return self._print_metric('count', metric_name, count, tags)


    def gauge(self, metric_name, value, tags=None):
        '''
        GAUGE

        Gauges are a constant data type. They are not subject to
                averaging, and they don't change unless you change them. That
                is, once you set a gauge value, it will be a flat line on the
                graph until you change it again

        If called multiple times during a check's execution for a metric only
        the last sample will be used.
        '''
        tags = self._get_tags(tags, metric_name)
        return self._print_metric('gauge', metric_name, value, tags)


    def histogram(self, metric_name, value, tags=None):
        '''
        HISTOGRAM

        Usage: Used to track the statistical distribution of a set of values.
        Should be called multiple times during an agent check (otherwise you
        have no distribution).

        Actually submits as multiple metrics:

            Name                 |  Web App type
            ---------------------|-----------------
            metric.max           |  GAUGE
            metric.avg           |  GAUGE
            metric.median        |  GAUGE
            metric.95percentile  |  GAUGE
            metric.count         |  RATE

        '''
        tags = self._get_tags(tags, metric_name)
        return self._print_metric('histogram', metric_name, value, tags)


    def timing(self, metric_name, delta, tags=None):
        """
        Timing - Track a duration event
        """
        tags = tags or []
        return self.histogram(metric_name, delta, tags)


    @contextmanager
    def timing_context(self, metric_name, tags=None):
        """
        Timing context to use with non decorated functions:
            with metric.timing_context("data_source", tags["entities"]):
                entities = data_source.get_entities()
        """
        start_time = time.time()
        yield
        end_time = time.time()
        delta = int(round((end_time - start_time) * 1000))
        self.timing(metric_name, delta, tags)


    def timeit(self, function):
        """
        Timing decorator for callable.
        """

        names = []
        try:
            names.append(function.__class__.__name__)
        except AttributeError:
            pass

        try:
            names.append(function.__qualname__)
        except AttributeError:
            pass

        try:
            names.append(function.__name__)
        except AttributeError:
            pass

        name = ".".join(names)

        @wraps(function)
        def decorated(*args, **kwargs):
            start_time = time.time()
            result = function(*args, **kwargs)
            end_time = time.time()
            delta = int(round((end_time - start_time) * 1000))
            self.timing(name, delta)
            return result

        return decorated


    def service_check(self, service_name="", status=OK, message="", tags=None):
        """
        SERVICE CHECK

        status - Integer corresponding to the check status: 

            0  =  OK
            1  =  WARNING
            2  =  CRITICAL
            3  =  UNKNOWN

        """
        assert isinstance(status, int)

        timestamp = int(time.time())

        metric_name = "lambda." + service_name
        metric_name = metric_name.replace("..", ".")
        tags = self._get_tags(tags, service_name)
        tags = ",".join(tags)
        timestamp = int(time.time())
        tmpl = (
                    "MONITORING"
                    "|{timestamp}"
                    "|{status}"
                    "|check"
                    "|{metric_name}"
                    "|#{tags}"
                )
        statsd_string = tmpl.format(**locals())
        if message:
            statsd_string += "|m:%s" % message
        return print(statsd_string)


    def _print_metric(self, metric_type, metric_name, value, tags_list):
        metric_name = "lambda." + metric_name
        metric_name = metric_name.replace("..", ".")
        timestamp = int(time.time())
        tags = ",".join(tags_list)
        statsd_string = (
            "MONITORING"
            "|{timestamp}"
            "|{value}"
            "|{metric_type}"
            "|{metric_name}"
            "|#{tags}"
        ).format(**locals())
        print(statsd_string)
