"""lambda function used for image generation in aws lambda with cumulus"""

import json
import logging
import os
import re
from shutil import rmtree
import requests

import botocore
from cumulus_logger import CumulusLogger
from cumulus_process import Process, s3
from podaac.forge_py import forge
from podaac.lambda_handler.cumulus_cli_handler.handlers import activity

cumulus_logger = CumulusLogger('image_generator')


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
    Image generation class to generate image for a granule file and upload to s3


    Attributes
    ----------
    processing_regex : str
        regex for nc file to generate image
    logger: logger
        cumulus logger
    config: dictionary
        configuration from cumulus


    Methods
    -------
    upload_file_to_s3('/user/test/test.png', 's3://bucket/path/test.png')
        uploads a local file to s3
    get_file_type(test.png, [....])
        gets the file type for a png
    get_bucket(test.png, [....], {....})
        gets the bucket where png to be stored
    process()
        main function ran for image generation
    generate_file_dictionary({file_data}, /user/test/test.png, test.png, [....], {....})
        creates the dictionary data for a generated image
    image_generate({file_data}, "/tmp/configuration.cfg", "/tmp/palette_dir", "granule.nc" )
        generates all images for a nc file
    get_config()
        downloads configuration file for tig
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

    @staticmethod
    def get_file_type(filename, files):
        """Get custom file type, default to metadata

        Parameters
        ----------
        filename: str
            filename of a file
        files: str
            collection list of files with attributes of specific file type
        """

        for collection_file in files:
            if re.match(collection_file.get('regex', '*.'), filename):
                return collection_file['type']
        return 'metadata'

    @staticmethod
    def get_bucket(filename, files, buckets):
        """Extract the bucket from the files

        Parameters
        ----------
        filename: str
            filename of a file
        files: list
            collection list of files with attributes of specific file type
        buckets: list
            list of buckets

        Returns
        ----------
        str
            string of the bucket the file to be stored in
        """
        bucket_type = "public"
        for file in files:
            if re.match(file.get('regex', '*.'), filename):
                bucket_type = file['bucket']
                break
        return buckets[bucket_type]

    @classmethod
    def cumulus_activity(cls, arn=os.getenv('ACTIVITY_ARN')):
        """ Run an activity using Cumulus messaging (cumulus-message-adapter) """
        activity(cls.cumulus_handler, arn)

    def get_config(self):
        """Get configuration file for image generations
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

    def process(self):
        """Main process to generate images for granules

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

                uploaded_images = self.image_generate(file_, config_file_path, self.path, granule_id)
                if uploaded_images:
                    append_output[granule_id] = append_output.get(granule_id, []) + uploaded_images
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