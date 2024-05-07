"""lambda function used for image generation in aws lambda with cumulus"""
# pylint: disable=R0801

import json
import logging
import os
from shutil import rmtree
import requests
import botocore
from cumulus_process import Process, s3
from cumulus_logger import CumulusLogger


cumulus_logger = CumulusLogger('forge_branching')


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


class FootprintBranch(Process):
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
    process()
        main function ran for image generation
    get_config()
        downloads configuration file for tig
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
        with open(config_file_path) as config_f:
            read_config = json.load(config_f)

        forge_type = read_config.get('footprinter', 'forge')
        self.input['forge_version'] = forge_type
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
    result = FootprintBranch.cumulus_handler(event, context=context)

    result['meta']['collection']['meta']['workflowChoice']['forge_version'] = result['payload']['forge_version']
    del result['payload']['forge_version']
    return result


if __name__ == "__main__":
    FootprintBranch.cli()
