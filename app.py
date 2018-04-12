from util import memoize
from prometheus_client import start_http_server, Summary
from prometheus_client.core import GaugeMetricFamily, REGISTRY
import time
from datetime import datetime
import boto3
import yaml, os
import logging, sys

# Logging config
loglevel = logging.INFO
if os.getenv('DEBUG', 'false').lower() == 'true':
  loglevel = logging.DEBUG
log = logging.getLogger(__name__)
log.setLevel(loglevel)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(loglevel)
formatter = logging.Formatter('%(asctime)s - %(levelname)s == %(message)s')
ch.setFormatter(formatter)
log.addHandler(ch)

REQUEST_TIME = Summary('request_processing_seconds',
                       'Time spent processing request')


class AwsBatchGauge(object):
  statuses = ['runnable', 'running', 'succeeded', 'failed']

  @REQUEST_TIME.time()
  def collect(self):
    config = self.read_config()
    self._setup_prometheus_metrics()
    queues = config['queues'] if config.get('queues') else []
    jobs = self.aws_batch_stat(queues, config['region'],
                               config.get('role_arn', None))
    for job in jobs:
      self._get_metrics(job)

    for status in self.statuses:
      for metric in self._prometheus_metrics[status].values():
        yield metric

  def read_config(self):
    configfile = os.path.join(os.path.dirname(__file__), 'config.yaml')
    if os.getenv('CONFIG_PATH'):
      configfile = os.getenv('CONFIG_PATH')
      log.info(os.path.exists(configfile))
      log.debug(configfile)
    if not (os.path.exists(configfile) and os.stat(configfile).st_size > 0):
      log.warn('cannot read config file: {}'.format(configfile))
      return {'region': os.environ['AWS_REGION']}
    return yaml.safe_load(open(configfile))

  def aws_batch_stat(self, queues, region, role_arn=None):
    result = []

    if role_arn:
      client = self.session(role_arn=role_arn).client(
        'batch', region_name=region)
    else:
      log.info('Using client credentials')
      client = boto3.client('batch', region_name=region)

    log.info('Starting to query the job queues')

    if not queues:
      resp = client.describe_job_queues()
      queues = [x['jobQueueName'] for x in resp['jobQueues']]

    for queue in queues:
      for s in self.statuses:
        kwargs = {'jobQueue': queue, 'jobStatus': s.upper()}
        while True:
          resp = client.list_jobs(**kwargs)
          for x in resp['jobSummaryList']:

            duration, total_duration = self._calculate_duration(x)
            result.append({
              'job_id': x['jobId'],
              'job_name': x['jobName'],
              'queue_name': queue,
              'duration': duration,
              'total_duration': total_duration,
              'status': s
            })
          if resp.get('nextToken'):
            kwargs['nextToken'] = resp['nextToken']
          else:
            log.info(
              'Completed the querying of the job for status:{}'.format(s))
            break
        result.append({
          'count': len(list(filter(lambda x: x['status'] == s, result))),
          'queue_name': queue,
          'status': s
        })
    return result

  def _calculate_duration(self, job):
    duration = 0
    total_duration = 0

    if not isinstance(job, dict):
      log.info('The job should be a dictionary')
      return duration, total_duration

    now = datetime.utcnow()

    if job['status'].upper() in ['RUNNABLE']:
      duration = (now - datetime.utcfromtimestamp(job['createdAt'] / 1000.))
      total_duration = duration
    elif job['status'].upper() in ['RUNNING']:
      duration = (now - datetime.utcfromtimestamp(job['startedAt'] / 1000.))
      total_duration = (
        now - datetime.utcfromtimestamp(job['createdAt'] / 1000.))
    elif job['status'].upper() in ['SUCCEEDED', 'FAILED']:
      duration = (
        datetime.utcfromtimestamp(job['stoppedAt'] / 1000.) -
        datetime.utcfromtimestamp(job['startedAt'] / 1000.))
      total_duration = (
        datetime.utcfromtimestamp(job['stoppedAt'] / 1000.) -
        datetime.utcfromtimestamp(job['createdAt'] / 1000.))
    return round(duration.total_seconds()), round(
      total_duration.total_seconds())

  @memoize(expiry_time=45 * 60)
  def session(self, role_arn):
    log.info('Retrieving session for assumed role')
    sts = boto3.client('sts')
    user = sts.get_caller_identity()['Arn'].split('/')[-1]
    resp = sts.assume_role(RoleArn=role_arn, RoleSessionName=user)
    return boto3.Session(
      aws_access_key_id=resp['Credentials']['AccessKeyId'],
      aws_secret_access_key=resp['Credentials']['SecretAccessKey'],
      aws_session_token=resp['Credentials']['SessionToken'])

  def _setup_prometheus_metrics(self):
    self._prometheus_metrics = {}

    for status in self.statuses:
      self._prometheus_metrics[status] = {
        'duration':
          GaugeMetricFamily(
            'batch_job_{}_duration_seconds'.format(status),
            'Batch job duration in seconds for {}'.format(status),
            labels=['job_id', 'job_name', 'queue_name']),
        'total_duration':
          GaugeMetricFamily(
            'batch_job_{}_total_duration_seconds'.format(status),
            'Batch job total duration in seconds for {}'.format(status),
            labels=['job_id', 'job_name', 'queue_name']),
        'count':
          GaugeMetricFamily(
            'batch_job_{}_count'.format(status),
            'Batch job count for {}'.format(status),
            labels=["queue_name"])
      }

  def _get_metrics(self, job):
    for status in self.statuses:
      if status in job.values():
        self._add_metrics(status, job)

  def _add_metrics(self, status, status_data):
    if status_data.get('count'):
      self._prometheus_metrics[status]['count'].add_metric(
        [status_data['queue_name']], status_data['count'])
    if status_data.get('job_id'):
      self._prometheus_metrics[status]['duration'].add_metric([
        status_data['job_id'], status_data['job_name'],
        status_data['queue_name']
      ], status_data['duration'])
      self._prometheus_metrics[status]['total_duration'].add_metric([
        status_data['job_id'], status_data['job_name'],
        status_data['queue_name']
      ], status_data['total_duration'])


if __name__ == '__main__':
  REGISTRY.register(AwsBatchGauge())
  start_http_server(8080)
  while True:
    time.sleep(5)
