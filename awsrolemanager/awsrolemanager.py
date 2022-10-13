#!/usr/bin/env python3
"""
This module is intended to help manage AWS STS credentials
when managing multiple roles.
"""

import sys

import argparse
import subprocess
import datetime
import json
import os
import prettytable
import termcolor

def get_account_number_from_arn(arn: str) -> str:
    """"
    Gets the AWS account number from an ARN
    Parameters:
    arn - The arn string to extract the account number from

    Returns:
    An AWS account number in string format
    """
    account_number = arn.split(':')[4]
    return account_number

def get_role_name_from_arn(arn: str) -> str:
    """
    Gets the role name from an ARN
    Parameters:
    arn - The arn string to extract the role name from

    Returns:
    A string containing the name of the role
    """
    role_name = arn.split('/')[1]
    return role_name

def get_session_name_from_arn(arn: str) -> str:
    """
    Gets the role name from an ARN
    Parameters:
    arn - The arn string to extract the session name from

    Returns:
    A string containing the name of the session
    """
    session_name = arn.split('/')[2]
    return session_name

def save_credentials(sts_creds: dict) -> str:
    """
    Saves a set of credentials to the AWS credentials file
    and saves relevant metadata to the configuration file.

    Parameters:
    creds - A dictionary containing the credential material required to assume
            the role

    Returns:
    The name of the profile
    """
    arn = sts_creds['AssumedRoleUser']['Arn']
    account_number = get_account_number_from_arn(arn)
    role_name = get_role_name_from_arn(arn)
    session_name = get_session_name_from_arn(arn)
    expiration = sts_creds['Credentials']['Expiration']

    profile_name = f"{account_number}-{role_name}-{session_name}"

    with open(os.path.expanduser("~/.aws/credentials"), 'a', encoding="utf-8") as file:
        access_key_id = sts_creds['Credentials']['AccessKeyId']
        secret_access_key = sts_creds['Credentials']['SecretAccessKey']
        session_token = sts_creds['Credentials']['SessionToken']

        block = f"""
[{profile_name}]
aws_access_key_id = {access_key_id}
aws_secret_access_key = {secret_access_key}
aws_session_token = {session_token}
"""
        file.write(block)
        file.close()

    with open(os.path.expanduser("~/.aws/config"), 'a', encoding="utf-8") as file:

        block = f"""
[{profile_name}]
region = us-east-1
output = json
session_name = {session_name}
expiration = {expiration}
role_name = {role_name}
"""
        file.write(block)
        file.close()

    return profile_name


def parse_config_file(config_file_path: str) -> dict:
    """
    Parses an AWS configuration file and return a dictionary
    representing the file.

    Parameters:
    config_file_path - A string containing the file path of the configuration
                       file

    Returns:
    A dictionary representing a configuration file
    """
    return_data = {}
    with open(config_file_path, 'r', encoding="utf-8") as file:
        text = file.read()
        lines = text.split('\n')

        config_item = ''

        for line in lines:
            # Remove any whitespace
            line = line.strip()
            if len(line) == 0:
                continue

            if line.startswith('#'):
                continue

            if line.startswith('['):
                config_item = line.strip('[]')
                return_data[config_item] = {}
            else:
                try:
                    key,value = line.split('=', 1)
                    if not config_item:
                        continue

                    return_data[config_item][key.strip()] = value.strip()

                except ValueError as exc:
                    import pdb; pdb.set_trace()
                    print(f"[!] invalid line in configuration file: {line}")
                    print(str(exc))
                    return None

    return return_data


def parse_configuration_data() -> dict:
    """
    Reads configuration files in the .aws folder and populates
    a dictionary with  the data.

    Returns:
    A dictionary representing the AWS profiles
    """

    config_file = os.path.expanduser("~/.aws/config")
    creds_file = os.path.expanduser("~/.aws/credentials")

    config_items = parse_config_file(config_file)
    if not config_items:
        return None
    cred_items = parse_config_file(creds_file)
    if not cred_items:
        return None

    profiles = {}

    for key, value in cred_items.items():
        if key not in config_items:
            profiles[key] = value
        else:
            profiles[key] = value | config_items[key]

    return profiles

def get_time_difference(timestamp: str) -> int:
    """
    Gets the difference in seconds between UTC now and the provided timeestamp
    Parameters:
    timestamp - A string timestamp in the form %Y-%m-%dT%H:%M:%S+00:00

    Returns:
    An integer representing the difference in seconds
    """
    expire_date = datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S+00:00')
    now = datetime.datetime.utcnow()

    return (expire_date - now).total_seconds()



def print_table(profile_data: dict) -> list:
    """
    Prints all of the AWS profiles in a table format and returns the list
    of profile names presented

    Parameters:
    profile_data - A dictionary containing all of the AWS profiles and their
                   corresponding configuration data
    """

    table = prettytable.PrettyTable(["Index", "Name", "Role Name",
        "Session Name", "Time Remaining"])
    i = 0
    keys = profile_data.keys()
    for key in keys:
        i += 1
        expiration = "N/A"
        role_name = ""
        session_name = ""
        if 'expiration' in profile_data[key]:
            expiration_seconds = get_time_difference(profile_data[key]['expiration'])
            if expiration_seconds < 0:
                expiration = termcolor.colored(
                    f"Expired {abs(int(expiration_seconds/60))} minutes ago",
                    'red')
            else:
                color = 'green'
                if int(expiration_seconds) < 600:
                    color = 'yellow'
                if int(expiration_seconds) < 60:
                    color = 'red'
                expiration = termcolor.colored(f"{int(expiration_seconds)} seconds", color)

        if "role_name" in profile_data[key]:
            role_name = profile_data[key]['role_name']

        if "session_name" in profile_data[key]:
            session_name = profile_data[key]['session_name']

        table.add_row([i, key, role_name, session_name, expiration])


    print(table)
    return list(keys)

def launch_role(profile_name: str, config_data: dict) -> None:
    """
    launch_role will launch a new x-terminal-emulator with the appropriate
    environment variables set for the selected role.

    Parameters:
    profile_name - The name of the AWS profile
    config_data - A dictionary containing all of the configuration data for
                  the AWS profile
    """
    custom_env = os.environ.copy()


    custom_env.pop('AWS_PROFILE', '')
    custom_env.pop('AWS_DEFAULT_PROFILE', '')
    custom_env.pop('AWS_ACCESS_KEY_ID', '')
    custom_env.pop('AWS_SECRET_ACCESS_KEY', '')
    custom_env.pop('AWS_SESSION_TOKEN', '')


    custom_env['AWS_PROFILE'] = profile_name
    #custom_env['AWS_ACCESS_KEY_ID'] = config_data['aws_access_key_id']
    #custom_env['AWS_SECRET_ACCESS_KEY'] = config_data['aws_secret_access_key']
    #if 'aws_session_token' in config_data:
    #    custom_env['AWS_SESSION_TOKEN'] = config_data['aws_session_token']

    subprocess.Popen('/usr/bin/x-terminal-emulator', env=custom_env)


def run_ui() -> None:
    """
    run_UI prints the table and prompts the user to select a role to use
    """
    data = parse_configuration_data()
    if not data:
        return

    keys = print_table(data)
    number_of_roles = len(keys)
    if number_of_roles == 0:
        print("[*] No configured roles found")
        return

    role_number = 0
    while role_number not in range(1, number_of_roles+1):
        try:
            keyboard_intput = input(f"Select a role [1 - {number_of_roles}]: ")
        except KeyboardInterrupt:
            print('\n')
            return
        try:
            role_number = int(keyboard_intput)
        except ValueError:
            print("[!] Not a valid number")
            continue

        if role_number not in range(1,number_of_roles+1):
            print(f"[!] Invalid selection. Pick a number between 1 - {number_of_roles}")

    profile_name = keys[role_number-1]

    launch_role(profile_name, data[profile_name])

def main():
    if len(sys.argv) > 1:
        # Parse args and follow command
        parser = argparse.ArgumentParser()
        if sys.argv[1] == "menu":
            run_ui()
    else:
        try:
            creds = sys.stdin.read()
        except KeyboardInterrupt:
            sys.exit(0)
        try:
            cred_obj = json.loads(creds)
            config_name = save_credentials(cred_obj)
            print(f"[*] Profile saved as {config_name}")

        except json.JSONDecodeError:
            print(f"[!] Invalid json: {creds}")

if __name__ == "__main__":
    main()
