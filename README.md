# aws_role_manager
A python script for quickly managing and assuming AWS roles and users. Only supports Linux at the moment, Windows support will be implemented as needed.

## Installation
Installing from pip
```
pip install awsrolemanager
```

Installing from source
```
git clone https://github.com/hotnops/aws_role_manager
cd aws_role_manager
pip install -r requirements.txt
python setup.py install
```


## Usage

Easily save credentials by piping them to aws_role_manager

```
aws sts assume-role --role-arn <role arn> --role-session-name | aws_role_manager
```

Launch new command prompts with specified roles
```
aws_role_manager menu
```

