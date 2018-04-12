# AWS Batch Exporter

Prometheus exporter for aws batch metrics. This exporter is useful to retrieve batch job metrics.

## Building and running

### Docker

```
docker run -d -p 8080:8080 -e AWS_REGION=us-east-1 oba11/aws-batch-exporter

OR

docker run -d -p 8080:8080 -v config.yml:/src/config.yml oba11/aws-batch-exporter

OR

docker run -d -p 8080:8080 -v config.yml:/config/config.yml -e CONFIG_PATH=/config/config.yml oba11/aws-batch-exporter
```

## Configuration

You need to set `AWS_REGION` environment variable if you want to skip using YAML configuration.</br>

The configuration is in YAML, an example with common options:

```
---
region: eu-west-1
queues:
	- queue-one
	- queue-two
```

IAM Policy

```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "batch:DescribeJobQueues",
        "batch:ListJobs"
      ],
      "Resource": "*"
    }
  ]
}
```

Name | Description
-----|------------
region   | Required. The AWS region to connect to.
role_arn   | Optional. The AWS role to assume. Useful for retrieving cross account metrics.
queues  | Optional. A list of batch queues to query and export metrics

## Metrics

List of metrics exposed by the exporter

Name | Description | Type
--------|------------|------------
`batch_job_runnable_duration_seconds`   |  Batch job duration in seconds in runnable status | gauge
`batch_job_runnable_total_duration_seconds`   |  Batch job total duration in seconds in runnable status since it was created | gauge
`batch_job_runnable_count`   |  The number of jobs in runnable status | gauge
`batch_job_running_duration_seconds`   |  Batch job duration in seconds in running status | gauge
`batch_job_running_total_duration_seconds`   |  Batch job total duration in seconds in running status since it was created | gauge
`batch_job_running_count`   |  The number of jobs in running status | gauge
`batch_job_succeeded_duration_seconds`   |  Batch job total duration in seconds in succeeded status since it was created | gauge
`batch_job_succeeded_total_duration_seconds`   |   Batch job duration in seconds in succeeded status | gauge
`batch_job_succeeded_count`   |  The number of jobs in succeeded status | gauge
`batch_job_failed_duration_seconds`   |   Batch job duration in seconds in failed status | gauge
`batch_job_failed_total_duration_seconds`   |  Batch job total duration in seconds in failed status since it was created | gauge
`batch_job_failed_count`   |  The number of jobs in failed status | gauge
