"""lambda function used for footprint generation in aws lambda with cumulus"""

import json
import logging
import os
import re
from shutil import rmtree
import requests

import botocore
import xarray as xr
from cumulus_logger import CumulusLogger
from cumulus_process import Process, s3
from podaac.forge_py import forge

cumulus_logger = CumulusLogger('forge_py')


def clean_tmp(remove_matlibplot=True):
    """ Deletes everything in /tmp """
    temp_folder = '/tmp'
    temp_files = os.listdir(temp_folder)

    cumulus_logger.info("Removing everything in tmp folder {}".format(temp_files))
    for filename in os.listdir(temp_folder):
        file_path = os.path.join(temp_folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                if filename.startswith('matplotlib'):
                    if remove_matlibplot:
                        rmtree(file_path)
                else:
                    rmtree(file_path)
        except OSError as ex:
            cumulus_logger.error('Failed to delete %s. Reason: %s' % (file_path, ex))

    temp_files = os.listdir(temp_folder)
    cumulus_logger.info("After Removing everything in tmp folder {}".format(temp_files))


class FootprintGenerator(Process):
    """
    Footprint generation class to generate footprints for a granule file and upload to s3


    Attributes
    ----------
    processing_regex : str
        regex for nc file to generate footprint
    logger: logger
        cumulus logger
    config: dictionary
        configuration from cumulus


    Methods
    -------
    upload_file_to_s3('/user/test/test.png', 's3://bucket/path/test.fp')
        uploads a local file to s3
    process()
        main function ran for footprint generation
    get_config()
        downloads configuration file for footprint
    download_file_from_s3('s3://my-internal-bucket/dataset-config/MODIS_A.2019.cfg', '/tmp/workspace')
        downloads a file from s3 to a directory
    """

    def __init__(self, *args, **kwargs):

        self.processing_regex = '(.*\\.nc$)'
        super().__init__(*args, **kwargs)
        self.logger = cumulus_logger

    def clean_all(self):
        """ Removes anything saved to self.path """
        rmtree(self.path)
        clean_tmp()

    def download_file_from_s3(self, s3file, working_dir):
        """ Download s3 file to local

        Parameters
        ----------
        s3file: str
            path location of the file  Ex. s3://my-internal-bucket/dataset-config/MODIS_A.2019.cfg
        working_dir: str
            local directory path where the s3 file should be downloaded to

        Returns
        ----------
        str
            full path of the downloaded file
        """
        try:
            return s3.download(s3file, working_dir)
        except botocore.exceptions.ClientError as ex:
            self.logger.error("Error downloading file %s: %s" % (s3file, working_dir), exc_info=True)
            raise ex

    def upload_file_to_s3(self, filename, uri):
        """ Upload a local file to s3 if collection payload provided

        Parameters
        ----------
        filename: str
            path location of the file
        uri: str
            s3 string of file location
        """
        try:
            return s3.upload(filename, uri, extra={"ACL": "bucket-owner-full-control"})
        except botocore.exceptions.ClientError as ex:
            self.logger.error("Error uploading file %s: %s" % (os.path.basename(os.path.basename(filename)), str(ex)), exc_info=True)
            raise ex

    def get_config(self):
        """Get configuration file for footprint generations
        Returns
        ----------
        str
            string of the filepath to the configuration
        """
        config_url = os.environ.get("CONFIG_URL")
        config_name = self.config['collection']['name']
        config_bucket = os.environ.get('CONFIG_BUCKET')
        config_dir = os.environ.get("CONFIG_DIR")

        if config_url:
            file_url = "{}/{}.cfg".format(config_url, config_name)
            response = requests.get(file_url, timeout=60)
            cfg_file_full_path = "{}/{}.cfg".format(self.path, config_name)
            with open(cfg_file_full_path, 'wb') as file_:
                file_.write(response.content)

        elif config_bucket and config_dir:
            config_s3 = 's3://{}.cfg'.format(os.path.join(config_bucket, config_dir, config_name))
            cfg_file_full_path = self.download_file_from_s3(config_s3, self.path)
        else:
            raise ValueError('Environment variable to get configuration files were not set')

        return cfg_file_full_path

    def footprint_generate(self, file_, config_file, granule_id):
        """function to generate footprint file and upload to s3

        Parameters
        ----------
        file_: list
            dictionary contain data about a granule file
        config_file:
            file path of configuration file that was downloaded from s3
        granule_id:
            ganule_id of the granule the footprint are generated for

        Returns
        ----------
        list
            list of dictionary of the footprint information that was uploaded to s3
        """

        collection = self.config.get('collection').get('name')
        execution_name = self.config.get('execution_name')
        output_bucket = os.environ.get('FOOTPRINT_OUTPUT_BUCKET')
        output_dir = os.environ.get('FOOTPRINT_OUTPUT_DIR')

        input_file = f's3://{file_["bucket"]}/{file_["key"]}'
        data_type = file_['type']

        if not re.match(f"{self.processing_regex}", input_file) and data_type != "data":
            return None

        try:
            local_file = s3.download(input_file, path=self.path)
        except botocore.exceptions.ClientError as ex:
            self.logger.error("Error downloading granule from s3: {}".format(ex), exc_info=True)
            raise ex

        with open(config_file) as config_f:
            read_config = json.load(config_f)

        longitude_var = read_config.get('lonVar')
        latitude_var = read_config.get('latVar')
        is360 = read_config.get('is360', False)

        thinning_fac = read_config.get('footprint', {}).get('thinning_fac', 100)
        alpha = read_config.get('footprint', {}).get('alpha', 0.05)
        strategy = read_config.get('footprint', {}).get('strategy', None)
        simplify = read_config.get('footprint', {}).get('simplify', 0.1)

        # Generate footprint
        with xr.open_dataset(local_file, decode_times=False) as ds:
            lon_data = ds[longitude_var]
            lat_data = ds[latitude_var]
            wkt_representation = forge.generate_footprint(lon_data, lat_data, thinning_fac=thinning_fac, alpha=alpha, is360=is360, simplify=simplify, strategy=strategy)

        wkt_json = {
            "FOOTPRINT": wkt_representation,
            "EXTENT": ""
        }

        # Generate json footprint file
        footprint_file_name = f"{granule_id}_{execution_name}.fp"
        footprint_json_file = os.path.join(self.path, footprint_file_name)

        with open(footprint_json_file, "w") as json_file:
            json.dump(wkt_json, json_file)

        # Upload json footprint file
        upload_file_dict = {
            "key": f'{output_dir}/{collection}/{footprint_file_name}',
            "fileName": footprint_file_name,
            "bucket": output_bucket,
            "size": os.path.getsize(footprint_json_file),
            "type": "metadata",
        }

        s3_link = f's3://{upload_file_dict["bucket"]}/{upload_file_dict["key"]}'
        self.upload_file_to_s3(footprint_json_file, s3_link)

        return upload_file_dict

    def process(self):
        """Main process to generate footprints for granules

        Returns
        ----------
        dict
            Payload that is returned to the cma which is a dictionary with list of granules
        """

        config_file_path = self.get_config()

        granules = self.input['granules']
        append_output = {}

        if self.kwargs.get('context', None):
            try:
                aws_request_id = self.kwargs.get('context').aws_request_id
                collection_name = self.config.get('collection').get('name')
                message = json.dumps({
                    "aws_request_id": aws_request_id,
                    "collection": collection_name
                })
                self.logger.info(message)
            except AttributeError:
                pass

        for granule in granules:
            granule_id = granule['granuleId']
            for file_ in granule['files']:
                file_dict = self.footprint_generate(file_, config_file_path, granule_id)
                if file_dict:
                    append_output[granule_id] = append_output.get(granule_id, []) + [file_dict]
            if granule_id in append_output:
                granule['files'] += append_output[granule_id]

        return self.input

    @classmethod
    def handler(cls, event, context=None, path=None, noclean=False):
        """ General event handler """
        return cls.run(path=path, noclean=noclean, context=context, **event)

    @classmethod
    def run(cls, *args, **kwargs):
        """ Run this payload with the given Process class """
        noclean = kwargs.pop('noclean', False)
        process = cls(*args, **kwargs)
        try:
            output = process.process()
        finally:
            if not noclean:
                process.clean_all()
        return output


def handler(event, context):
    """handler that gets called by aws lambda

    Parameters
    ----------
    event: dictionary
        event from a lambda call
    context: dictionary
        context from a lambda call

    Returns
    ----------
        string
            A CMA json message
    """

    levels = {
        'critical': logging.CRITICAL,
        'error': logging.ERROR,
        'warn': logging.WARNING,
        'warning': logging.WARNING,
        'info': logging.INFO,
        'debug': logging.DEBUG
    }
    logging_level = os.environ.get('LOGGING_LEVEL', 'info')
    cumulus_logger.logger.level = levels.get(logging_level, 'info')
    cumulus_logger.setMetadata(event, context)
    clean_tmp()
    return FootprintGenerator.cumulus_handler(event, context=context)


if __name__ == "__main__":
    FootprintGenerator.cli()
