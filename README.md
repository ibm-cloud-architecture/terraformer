# Tabularize Terraform Resources

## Overview

- Latest release: [Terraformer 1.11.0.0](/releases/releases.md)
- Improve viewability and maintainability by representating some Terraform resources as data.
- For simple usage, use constants and resource references in data.
- For complex usage, also include functional references in data.
- For partial usage, only represent specific components in data (e.g. network ACLs, Security Groups, etc).
- Data representation may not be possible for every resource or field but can be useful where possible.
- Provided with no formal support but problems can be reported by opening a GitHub issue.
- Data format is subject to change.

## Implementation

1. For column names, asterisk denotes a required field.
2. For complex lists, copy existing column and add a number to group name (e.g. network_interfaces.subnet becomes network_interfaces2.subnet).
3. For data fields, values are copied directly to generated Terraform.
4. For changed data, regenerate data and let Terraform handle changes. 
5. For sheet names, use either basename (e.g. instances) or basename-groupname (e.g. instances-group1).
6. For OS images, variables-system sheet is provided for reference but is subject to change.
7. For generated backups, existing output directories are backed up to directory.backupNNN. 

## Prerequisites

Install the following software:
1. [IBM Cloud Terraform Provider v1.11.0](https://github.com/IBM-Cloud/terraform-provider-ibm/releases)
2. [Terraform v0.12.23+](https://www.terraform.io/downloads.html)
3. [Ansible 2.9.11](https://docs.ansible.com/ansible/latest/index.html)
4. [Python v3.8.2](https://www.python.org/downloads/) with libraries:
    - numpy
    - pandas
    - cython (for compiling)
    - xlrd (for xlsx)
    - odfpy (for ods)
    - pyyaml (for yaml)

Note: Install Python 3 from python.org separately from Mac default of Python 2 - installing with brew, pipenv, or pyenv use different directories that won't work.

## Deploy VPC Infrastructure using Terraform and Ansible

1. [Deploy Infrastructure using Terraform](/docs/terraform.md)
2. TBD

## License

This application is licensed under the Apache License, Version 2.  Separate third-party code objects invoked by this application are licensed by their respective providers pursuant to their own separate licenses.  Contributions are subject to the [Developer Certificate of Origin, Version 1.1](https://developercertificate.org/) and the [Apache License, Version 2](https://www.apache.org/licenses/LICENSE-2.0.txt).
