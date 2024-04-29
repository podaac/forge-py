"""Test cases for forge-py lambda_handler"""

import json
import os
import boto3
import pytest
from jsonschema import validate

from podaac.lambda_handler import lambda_handler_branch
from moto import mock_aws
from mock import patch, Mock
import xarray as xr
from podaac.forge_py import forge
from shapely.wkt import dumps

file_schema = {
  "type": "array",
  "items": {
    "additionalProperties": False,
    "type": "object",
    "required": [
      "bucket",
      "key"
    ],
    "properties": {
      "bucket": {
        "description": "Bucket where file is archived in S3",
        "type": "string"
      },
      "checksum": {
        "description": "Checksum value for file",
        "type": "string"
      },
      "checksumType": {
        "description": "Type of checksum (e.g. md5, sha256, etc)",
        "type": "string"
      },
      "fileName": {
        "description": "Name of file (e.g. file.txt)",
        "type": "string"
      },
      "key": {
        "description": "S3 Key for archived file",
        "type": "string"
      },
      "size": {
        "description": "Size of file (in bytes)",
        "type": "number"
      },
      "source": {
        "description": "Source URI of the file from origin system (e.g. S3, FTP, HTTP)",
        "type": "string"
      },
      "type": {
        "description": "Type of file (e.g. data, metadata, browse)",
        "type": "string"
      },
      "description": {
        "description": "variable values",
        "type": "string"
      }
    }
  }
}

class Context:
    def __init__(self, aws_request_id):
        self.aws_request_id = aws_request_id

@mock_aws
@patch('requests.get')
def test_lambda_handler_cumulus(mocked_get):
    """Test lambda handler to run through cumulus handler"""

    test_dir = os.path.dirname(os.path.realpath(__file__))

    bucket = "test-prefix-protected-test"
    aws_s3 = boto3.resource('s3', region_name='us-east-1')
    aws_s3.create_bucket(Bucket=bucket)

    input_dir = f'{test_dir}/input'
    config_dir = f'{test_dir}/configs'
    nc_file = f'{input_dir}/measures_esdr_scatsat_l2_wind_stress_23433_v1.1_s20210228-054653-e20210228-072612.nc'
    cfg_file = f'{config_dir}/PODAAC-CYGNS-C2H10.cfg'

    with open(nc_file, 'rb') as data:
        aws_s3.Bucket(bucket).put_object(Key='test_folder/test_granule.nc', Body=data)

    s3_client = boto3.client('s3', region_name='us-east-1')    

    # Mock S3 download here:
    os.environ["CONFIG_BUCKET"] = "internal-bucket"
    os.environ["CONFIG_DIR"] = "dataset-config"
    os.environ["CONFIG_URL"] = ""
    os.environ["FOOTPRINT_OUTPUT_BUCKET"] = "internal-bucket"
    os.environ["FOOTPRINT_OUTPUT_DIR"] = "test"

    aws_s3.create_bucket(Bucket='internal-bucket')

    with open(cfg_file, 'rb') as data:
        s3_client.put_object(Bucket='internal-bucket',
                         Key='dataset-config/JASON-1_L2_OST_GPN_E.cfg',
                         Body=data)

    s3_client.get_object(Bucket="internal-bucket",
                         Key='dataset-config/JASON-1_L2_OST_GPN_E.cfg',
                         )

    dir_path = os.path.dirname(os.path.realpath(__file__))
    input_file = dir_path + '/input.txt'

    with open(input_file) as json_event:
        event = json.load(json_event)
        granules = event.get('payload').get('granules')
        for granule in granules:
            files = granule.get('files')
            is_valid_shema = validate(instance=files, schema=file_schema)
            assert is_valid_shema is None

    context = Context("fake_request_id")
    output = lambda_handler_branch.handler(event, context)

    for granule in output.get('payload').get('granules'):
        is_valid_shema = validate(instance=granule.get('files'), schema=file_schema)
        assert is_valid_shema is None  

    assert output['meta']['collection']['meta']['workflowChoice']['forge_version'] == 'forge'