# Forge Py Terraform Module

This module is used to deploy the `forge_py` Lambda function with Terraform. It configures the necessary resources including the Lambda container image, IAM roles, VPC configurations, and various AWS resources required for the function to operate.

## Requirements

- Terraform 0.12 or later
- AWS Account with necessary permissions
- The following AWS resources:
  - IAM Roles
  - VPC with private subnets
  - Security Groups
  - S3 Buckets
  - Lambda Execution Role

## Inputs

| Name                        | Description                                                                 | Type   | Default                         |
| --------------------------- | --------------------------------------------------------------------------- | ------ | ------------------------------- |
| `lambda_container_image_uri` | URI of the container image for the `forge-py` Lambda function.              | string | `"ghcr.io/podaac/forge-py:0.1.0"`|
| `prefix`                     | Prefix for resource names.                                                  | string | `local.resources_name`           |
| `region`                     | AWS region where resources will be deployed.                                | string | `var.region`                     |
| `cmr_environment`            | CMR environment for the `forge-py` function.                                | string | `var.cmr_environment`            |
| `config_bucket`              | S3 bucket name for storing configuration files.                            | string | `"podaac-services-uat-hitide-backfill-internal"`|
| `config_dir`                 | Directory in the S3 bucket for configuration files.                         | string | `"forge_py_configs"`             |
| `footprint_output_bucket`    | S3 bucket for storing footprint output.                                     | string | `"${local.resources_name}-internal"`|
| `footprint_output_dir`       | Directory in the footprint output bucket.                                  | string | `"dataset-metadata"`             |
| `lambda_role`                | ARN of the Lambda execution role.                                          | string | `aws_iam_role.iam_execution.arn` |
| `security_group_ids`         | List of security group IDs to associate with the Lambda function.           | list   | `[var.aws_security_group_ids]`   |
| `subnet_ids`                 | List of subnet IDs for Lambda function placement in the VPC.                | list   | `data.aws_subnets.private.ids`   |
| `memory_size`                | Memory size for the Lambda function.                                        | number | `1024`                           |
| `timeout`                    | Timeout in seconds for the Lambda function.                                 | number | `900`                            |

## Outputs

- None

## Example Usage

```hcl
module "forge_py_module" {
  source                    = "https://github.com/podaac/forge-py/releases/download/0.1.0/forge-py-terraform-0.1.0.zip"
  lambda_container_image_uri = "ghcr.io/podaac/forge-py:0.1.0"
  prefix                    = "prefix"
  region                    = var.region
  cmr_environment           = var.cmr_environment
  config_bucket             = "config-bucket"
  config_dir                = "config-dir"
  footprint_output_bucket   = "output-bucket"
  footprint_output_dir      = "output-dir"
  lambda_role               = aws_iam_role.iam_execution.arn
  security_group_ids        = [var.aws_security_group_ids]
  subnet_ids                = data.aws_subnets.private.ids
  memory_size               = 1024
  timeout                   = 900
}
