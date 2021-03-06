#i Transform tabularized Terraform data into Terraform resources
#
# Copyright IBM Corporation 2021
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import argparse
import json
import yaml
import shutil
import numpy as np
import pandas as pd

# Constants

# Following static string is included in binary - update version here.
COPYRIGHT = 'tabular-terraform 1.19.0.0 - Copyright IBM Corporation 2021'

genheader = '# Generated by tabular-terraform'

dataheader = 'data "%s" "%s" {'
moduleheader = 'module "%s" {'
outputheader = 'output "%s" {'
providerheader = 'provider "%s" {'
resourceheader = 'resource "%s" "%s" {'
terraformheader = 'terraform {'
variableheader = 'variable "%s" {'

enddata = '}'
endmodule = '}'
endoutput = '}'
endprovider = '}'
endresource = '}'
endterraform = '}'
endvariable = '}'

# Messages

toolheader = 'Transform tabularized Terraform data into Terraform resources\n'
starttfmessage = 'Generating Resources with input from %s\n'
startprovidermessage = 'Generating Resource for provider\n'
startversionsmessage = 'Generating Resource for versions\n'
donetfmessage = '\nCompleted Resources for %s with output to folder %s\n'
backupdirectorymessage = 'Backed up existing output directory %s to %s\n'
invalidinputdirectorymessage = '(Error) Invalid input directory: %s'
invalidinputfilemessage = '(Error) Invalid input file: %s'
invalidprotocolmessage = '(Error) Invalid protocol: %s'
invalidgatewayspecmessage = '(Error) Invalid gateway specification: %s'
invalidnicmessage = '(Error) Invalid nic: %s'
invalidsecondarynicmessage = '(Error) Invalid secondary nic: %s'
missinginputmessage = '(Error) No input files found: %s'
missingimagemessage = '(Error) Image %s not found'
missingzonemessage = '(Error) Zone %s not found'
missingsubnetmessage = '(Error) Subnet for %s not found'
missingimageprofilemessage = '(Error) Image profile %s not found'
missingvolumeprofilemessage = '(Error) Volume profile %s not found'
missingvaluemessage = '(Error) Required value missing on column %s, row %s'
processingsheetmessage = 'Processing %s'

# User options

options = {
'generation': '2',
'datapath': 'data',
'datatype': 'xlsx',
'genpath': 'resources',
'propext': 'xlsx',
'propfile': '',
'propname': '*'
}

# Resource names

# Translate sheet names to resource names.
# Resource names are not used as sheet names due to sheet name limit.
resources = {
'aclheaders': 'ibm_is_network_acl',
'aclrules': 'ibm_is_network_acl',
'cisdomains': 'ibm_cis_domain',
'cisglbs': 'ibm_cis_global_load_balancer',
'cishealthchecks': 'ibm_cis_healthcheck',
'cisinstances': 'ibm_cis',
'cisoriginpools': 'ibm_cis_origin_pool',
'floatingips': 'ibm_is_floating_ip',
'flowlogs': 'ibm_is_flow_log',
'ikepolicies': 'ibm_is_ike_policy',
'images': 'ibm_is_image',
'instances': 'ibm_is_instance',
'instancegroups': 'ibm_is_instance_group',
'instancemanagers': 'ibm_is_instance_group_manager',
'instancepolicies': 'ibm_is_instance_group_manager_policy',
'instancetemplates': 'ibm_is_instance_template',
'ipsecpolicies': 'ibm_is_ipsec_policy',
'loadbalancers': 'ibm_is_lb',
'lblisteners': 'ibm_is_lb_listener',
'lbmembers': 'ibm_is_lb_pool_member',
'lbpolicies': 'ibm_is_lb_listener_policy',
'lbpools': 'ibm_is_lb_pool',
'lbrules': 'ibm_is_lb_listener_policy_rule',
'networkinterfaces': 'ibm_is_instance_nic',
'publicgateways': 'ibm_is_public_gateway',
'resourcegroups': 'ibm_resource_group',
'sgheaders': 'ibm_is_security_group',
'sgnics': 'ibm_is_security_group_network_interface_attachment',
'sgrules': 'ibm_is_security_group_rule',
'sshkeys': 'ibm_is_ssh_key',
'subnets': 'ibm_is_subnet',
'transitconnections': 'ibm_tg_connection',
'transitgateways': 'ibm_tg_gateway',
'volumes': 'ibm_is_volume',
'vpcaddresses': 'ibm_is_vpc_address_prefix',
'vpcroutes': 'ibm_is_vpc_route',
'vpcs': 'ibm_is_vpc',
'vpnconnections': 'ibm_is_vpn_gateway_connection',
'vpngateways': 'ibm_is_vpn_gateway'
}

# Utility functions

# isna returns True for NA values such as None or numpy.NaN.
# isna returns False for empty strings or numpy.inf unless
# set pandas.options.mode.use_inf_as_na = True
# Note:
# Empty spreadsheet values start out as NaN but if a value is
# added and later deleted then the value can be an empty string.
# Checking pd.isna here doesn't work as value is 'nan'.
def novalue(value):
   empty = pd.isna(value)
   if empty:
      return True
   if type(value) == str:
      value = value.replace(' ', '')
      if value == '':
         return True
   if isinstance(value, str):
      value = value.replace(' ', '')
      if value == '':
         return True
      else:
         return False
   else:
      return False

def loadfile(options):
   propext = options['propext']
   propfile = options['propfile']

   if (propext.lower() == 'xls' or propext.lower() == 'xlsx'):
      sheets = pd.read_excel(propfile, sheet_name=None, dtype=object, header=0)
   else:
      print(invalidinputfilemessage % propfile)
      sheets = None

   return sheets

def loadframe(options, pd, sheet):
   propext = options['propext']
   propfile = options['propfile']

   df = pd.DataFrame(sheet)

   if (propext.lower() == 'xls' or propext.lower() == 'xlsx'):
      # Remove leading asterisk from column names
      df.rename(columns=lambda x: x[1:] if x[0]=='*' else x, inplace=True)
   else:
      print(invalidinputfilemessage % propfile)
      sheets = None

   return df

def printline(options, tfname, line):
   genpath = options['genpath']

   pathname = os.path.join(genpath, tfname)
   filepath, filename = os.path.split(pathname)

   # Check for existing module directory.
   if not os.path.exists(filepath):
      # Create new module directory.
      os.makedirs(filepath)

   if not os.path.exists(pathname):
      tf = open(pathname, 'w')
      tf.write(genheader)
      tf.write('\n')
      tf.close()

   tf = open(pathname, 'a')
   tf.write(line)
   tf.write('\n')
   tf.close()

   return

# Generate functions

def genproviders(options, name, sheet, df):
   genpath = options['genpath']

   print(processingsheetmessage % name)

   name = name.replace(' ', '')
   pos = name.find('-')
   if pos >= 0:
      sheettype = name[0:pos]
      sheetgroup = name[pos+1:]
   else:
      sheettype = name
      sheetgroup = ''

   columns = df.columns

   # Loop thru rows.
   for rowindex, row in df.iterrows():
      tfname = row['file']
      # Skip empty rows.
      empty = novalue(tfname)
      if empty:
         continue
      else:
         tfname = tfname.replace(' ', '')

      #resource = row['resource']
      #empty = novalue(resource)
      #if empty:
      #   print(missingvaluemessage % ('resource', rowindex))
      #   continue

      module = row['module']
      empty = novalue(module)
      if empty:
         module = '.'
      else:
         module = module.replace(' ', '')
 
      tfname = os.path.join(module, tfname)

      comments = row['comments']
      empty = novalue(comments)
      if not empty:
        printline(options, tfname, '# ' + comments)

      #printline(options, tfname, providerheader % name)
      printline(options, tfname, providerheader % 'ibm')

      savegroup = None

      # Loop through columns skipping first column (file) and last 2 columns (modules and comments).
      for columnindex in range(columns.size-2):
         if columnindex < 1:
            continue

         column = columns[columnindex]
         value = row[column]
         empty = novalue(value)
         if empty:
            continue

         if isinstance(value, int):
            value = str(value)

         column = column.replace(' ', '')

         dotpos = column.find('.')
         if dotpos >= 0:
            subgroup = column[0:dotpos]
            subcolumn = column[dotpos+1:]
            column = subcolumn
            if savegroup == None:
               # No group yet so start group.
               savegroup = subgroup
               # Remove trailing digits from duplicated columns of arrays.
               subgroup = subgroup.rstrip('0123456789')
               printline(options, tfname, subgroup + ' {')
            elif savegroup != subgroup:
               # Adjacent groups so close previous group and start next group.
               savegroup = subgroup
               # Remove trailing digits from duplicated columns of arrays.
               subgroup = subgroup.rstrip('0123456789')
               printline(options, tfname, '}')
               printline(options, tfname, subgroup + ' {')
         elif savegroup != None:
            # End of group so close group.
            savegroup = None
            printline(options, tfname, '}')

         if column != 'name':
            printline(options, tfname, column + ' = ' + value)

      if savegroup != None:
         # End of row so close group.
         savegroup = None
         printline(options, tfname, '}')

      printline(options, tfname, endprovider)

   return

def genversions(options, name, sheet, df):

   #printline(options, tfname, 'terraform {')
   #printline(options, tfname, 'required_version = ">= ' + terraformversion + '"')
   #printline(options, tfname, 'required_providers {')
   #printline(options, tfname, 'ibm = {')
   #printline(options, tfname, 'source = "ibm-cloud/ibm"')
   #printline(options, tfname, 'version = "' + providerversion + '"')
   #printline(options, tfname, '}')
   #printline(options, tfname, '}')
   #printline(options, tfname, '}')

   genpath = options['genpath']

   print(processingsheetmessage % name)

   name = name.replace(' ', '')
   pos = name.find('-')
   if pos >= 0:
      sheettype = name[0:pos]
      sheetgroup = name[pos+1:]
   else:
      sheettype = name
      sheetgroup = ''

   columns = df.columns

   # Loop thru rows.
   for rowindex, row in df.iterrows():
      tfname = row['file']
      # Skip empty rows.
      empty = novalue(tfname)
      if empty:
         continue
      else:
         tfname = tfname.replace(' ', '')

      #resource = row['resource']
      #empty = novalue(resource)
      #if empty:
      #   print(missingvaluemessage % ('resource', rowindex))
      #   continue

      module = row['module']
      empty = novalue(module)
      if empty:
         module = '.'
      else:
         module = module.replace(' ', '')
 
      tfname = os.path.join(module, tfname)

      comments = row['comments']
      empty = novalue(comments)
      if not empty:
        printline(options, tfname, '# ' + comments)

      printline(options, tfname, terraformheader)

      savegroup = None

      # Loop through columns skipping first column (file) and last 2 columns (modules and comments).
      for columnindex in range(columns.size-2):
         if columnindex < 1:
            continue

         column = columns[columnindex]
         value = row[column]
         empty = novalue(value)
         if empty:
            continue

         if isinstance(value, int):
            value = str(value)

         column = column.replace(' ', '')

         dotpos = column.rfind('.')
         if dotpos >= 0:
            subgroup = column[0:dotpos]
            subcolumn = column[dotpos+1:]
            column = subcolumn
            if savegroup == None:
               # No group yet so start group.
               savegroup = subgroup
               # Remove trailing digits from duplicated columns of arrays.
               subgroup = subgroup.rstrip('0123456789')
               if subgroup == 'required_providers.ibm':
                  printline(options, tfname, 'required_providers {')
                  printline(options, tfname, 'ibm = {')
               else:
                  printline(options, tfname, subgroup + ' {')
            elif savegroup != subgroup:
               # Adjacent groups so close previous group and start next group.
               savegroup = subgroup
               # Remove trailing digits from duplicated columns of arrays.
               subgroup = subgroup.rstrip('0123456789')
               printline(options, tfname, '}')
               if subgroup == 'required_providers.ibm':
                  printline(options, tfname, 'required_providers {')
                  printline(options, tfname, 'ibm = {')

               else:
                  printline(options, tfname, subgroup + ' {')
         elif savegroup != None:
            # End of group so close group.
            savegroup = None
            printline(options, tfname, '}')
            if subgroup == 'required_providers.ibm':
               printline(options, tfname, '}')

         if column != 'name':
            printline(options, tfname, column + ' = ' + value)

      if savegroup != None:
         # End of row so close group.
         savegroup = None
         printline(options, tfname, '}')
         if subgroup == 'required_providers.ibm':
            printline(options, tfname, '}')

      printline(options, tfname, endterraform)

   return

def genoutputs(options, name, sheet, df):
   genpath = options['genpath']
   
   print(processingsheetmessage % name)

   columns = df.columns

   # Loop thru rows.
   for rowindex, row in df.iterrows():
      tfname = row['file']
      # Skip empty rows.
      empty = novalue(tfname)
      if empty:
         continue
      else:
         tfname = tfname.replace(' ', '')

      name = row['name']
      empty = novalue(name)
      if empty:
         print(missingvaluemessage % ('name', rowindex))
         continue
      
      value = row['value']
      empty = novalue(value)
      if empty:
         print(missingvaluemessage % ('value', rowindex))
         continue

      module = row['module']
      empty = novalue(module)
      if empty:
         module = '.'
      else:
         module = module.replace(' ', '')

      tfname = os.path.join(module, tfname)

      comments = row['comments']
      empty = novalue(comments)
      if not empty:
        printline(options, tfname, '# ' + comments)

      printline(options, tfname, outputheader % name)
      printline(options, tfname, 'value = ' + str(value))
      printline(options, tfname, endoutput)

   return

def gencloudinits(options, name, sheet, df):
   genpath = options['genpath']
   
   print(processingsheetmessage % name)

   columns = df.columns

   # Loop thru rows.
   for rowindex, row in df.iterrows():
      tfname = row['file']
      # Skip empty rows.
      empty = novalue(tfname)
      if empty:
         continue
      else:
         tfname = tfname.replace(' ', '')

      resource = row['resource']
      empty = novalue(resource)
      if empty:
         print(missingvaluemessage % ('resource', rowindex))
         continue
      
      module = row['module']
      empty = novalue(module)
      if empty:
         module = '.'
      else:
         module = module.replace(' ', '')

      datapath = options['datapath']
      initspath = os.path.join(datapath, 'cloudinits')
      tfname = os.path.join(initspath, tfname)

      if os.path.isdir(initspath) and os.path.isfile(tfname):
         filepath = os.path.join(genpath, module)
         # Check for existing module directory.
         if not os.path.exists(filepath):
            # Create new module directory.
            os.makedirs(filepath)
         shutil.copy(tfname, filepath)

   return

def genvariables(options, name, sheet, df):
   genpath = options['genpath']
   
   print(processingsheetmessage % name)

   columns = df.columns

   # Loop thru rows.
   for rowindex, row in df.iterrows():
      tfname = row['file']
      # Skip empty rows.
      empty = novalue(tfname)
      if empty:
         continue
      else:
         tfname = tfname.replace(' ', '')

      name = row['name']
      empty = novalue(name)
      if empty:
         print(missingvaluemessage % ('name', rowindex))
         continue
      
      emptyvalue = False
      value = row['value']
      empty = novalue(value)
      if empty:
         emptyvalue = True
         #print(missingvaluemessage % ('value', rowindex))
         #continue

      module = row['module']
      empty = novalue(module)
      if empty:
         module = '.'
      else:
         module = module.replace(' ', '')

      tfname = os.path.join(module, tfname)

      printline(options, tfname, variableheader % name)

      comments = row['comments']
      empty = novalue(comments)
      if not empty:
         #printline(options, tfname, '# ' + comments)
         printline(options, tfname, 'description = "' + comments + '"')

      if not emptyvalue:
         printline(options, tfname, 'default = ' + str(value))

      printline(options, tfname, endvariable)

   return

def genmodules(options, name, sheet, df):
   genpath = options['genpath']
   
   print(processingsheetmessage % name)

   tfname = 'modules.tf'
   module = name.split('-')[1]

   printline(options, tfname, moduleheader % module)

   columns = df.columns

   # Loop thru rows.
   for rowindex, row in df.iterrows():
      tfnameignore = row['file']
      # Skip empty rows.
      empty = novalue(tfnameignore)
      if empty:
         continue

      name = row['name']
      empty = novalue(name)
      if empty:
         print(missingvaluemessage % ('name', rowindex))
         continue
      
      emptyvalue = False
      value = row['value']
      empty = novalue(value)
      if empty:
         emptyvalue = True
         #print(missingvaluemessage % ('value', rowindex))
         #continue

      module = row['module']
      empty = novalue(module)
      if empty:
         module = '.'
      else:
         module = module.replace(' ', '')

      #tfname = os.path.join(module, tfname)

      #printline(options, tfname, moduleheader % name)

      comments = row['comments']
      empty = novalue(comments)
      if not empty:
         printline(options, tfname, '# ' + comments)
         #printline(options, tfname, 'description = "' + comments + '"')

      if not emptyvalue:
         #printline(options, tfname, 'default = ' + str(value))
         printline(options, tfname, name + ' = ' + value)

      #printline(options, tfname, endvariable)

   printline(options, tfname, endmodule)

   return

def genaclresources(options, name, sheet, df):
   genpath = options['genpath']
   
   print(processingsheetmessage % name)

   name = name.replace(' ', '')
   pos = name.find('-')
   if pos >= 0:
      sheettype = name[0:pos]
      sheetgroup = name[pos+1:]
   else:
      sheettype = name
      sheetgroup = ''

   columns = df.columns

   header = True
   tfname = None

   # Loop thru rows.
   for rowindex, row in df.iterrows():
      if header:
         tfname = row['file']
         # Skip empty rows.
         empty = novalue(tfname)
         if empty:
            continue
         else:
            tfname = tfname.replace(' ', '')

         resource = row['resource']
         empty = novalue(resource)
         if empty:
            print(missingvaluemessage % ('resource', rowindex))
            continue
         else:
            resource = resource.replace(' ', '')

         #resource_data = False
         #resource = resource.replace(' ', '')
         #pos = resource.find('.')
         #if pos >= 0:
         #   if resource[0:pos] == 'data':
         #      resource_data = True
         #      resource = resource[pos+1:]

         header = False

         module = row['module']
         empty = novalue(module)
         if empty:
            module = '.'
         else:
            module = module.replace(' ', '')

         tfname = os.path.join(module, tfname)

         comments = row['comments']
         empty = novalue(comments)
         if not empty:
            printline(options, tfname, '# ' + comments)

         #if resource_data == True:
         #   printline(options, tfname, dataheader % (resources[sheettype], resource))
         #else:
         printline(options, tfname, resourceheader % (resources[sheettype], resource))

         # Loop through columns skipping first 2 columns (file and resource) and last 2 columns (module and comments).
         for columnindex in range(columns.size-2):
            if columnindex < 2:
               continue

            column = columns[columnindex]
            value = row[column]
            empty = novalue(value)
            if empty:
               continue

            if isinstance(value, int):
               value = str(value)

            printline(options, tfname, column + ' = ' + value)
      else:
         name = row['name']
         # End of rule group when name is empty.
         empty = novalue(name)
         if empty:
            printline(options, tfname, '}')
            header = True
            continue

         printline(options, tfname, 'rules {')

         savegroup = None

         # Loop through columns skipping first 2 columns (file and resource) and last 2 columns (module and comments).
         for columnindex in range(columns.size-2):
            if columnindex < 2:
               continue

            column = columns[columnindex]
            value = row[column]
            empty = novalue(value)
            if empty:
               continue

            if isinstance(value, int):
               value = str(value)

            column = column.replace(' ', '')
            dotpos = column.find('.')
            if dotpos >= 0:
               subgroup = column[0:dotpos]
               subcolumn = column[dotpos+1:]
               column = subcolumn
               if savegroup == None:
                  # No group yet so start group.
                  savegroup = subgroup
                  # Remove trailing digits from duplicated columns of arrays.
                  subgroup = subgroup.rstrip('0123456789')
                  printline(options, tfname, subgroup + ' {')
               elif savegroup != subgroup:
                  # Adjacent groups so close previous group and start next group.
                  savegroup = subgroup
                  # Remove trailing digits from duplicated columns of arrays.
                  subgroup = subgroup.rstrip('0123456789')
                  printline(options, tfname, '}')
                  printline(options, tfname, subgroup + ' {')
            elif savegroup != None:
               # End of group so close group.
               savegroup = None
               printline(options, tfname, '}')

            printline(options, tfname, column + ' = ' + value)

         if savegroup != None:
            # End of row so close group.
            savegroup = None
            printline(options, tfname, '}')

         printline(options, tfname, '}')

   if tfname != None:
      printline(options, tfname, endresource)

   return

def genresources(options, name, sheet, df):
   genpath = options['genpath']
   
   print(processingsheetmessage % name)

   name = name.replace(' ', '')
   pos = name.find('-')
   if pos >= 0:
      sheettype = name[0:pos]
      sheetgroup = name[pos+1:]
   else:
      sheettype = name
      sheetgroup = ''

   columns = df.columns

   # Loop thru rows.
   for rowindex, row in df.iterrows():
      tfname = row['file']
      # Skip empty rows.
      empty = novalue(tfname)
      if empty:
         continue
      else:
         tfname = tfname.replace(' ', '')

      resource = row['resource']
      empty = novalue(resource)
      if empty:
         print(missingvaluemessage % ('resource', rowindex))
         continue
      else:
         resource = resource.replace(' ', '')

      resource_data = False
      resource = resource.replace(' ', '')
      pos = resource.find('.')
      if pos >= 0:
         if resource[0:pos] == 'data':
            resource_data = True
            resource = resource[pos+1:]

      module = row['module']
      empty = novalue(module)
      if empty:
         module = '.'
      else:
         module = module.replace(' ', '')
 
      tfname = os.path.join(module, tfname)

      comments = row['comments']
      empty = novalue(comments)
      if not empty:
         printline(options, tfname, '# ' + comments)

      if resource_data == True:
         printline(options, tfname, dataheader % (resources[sheettype], resource))
         value = row['name']
         empty = novalue(value)
         if empty:
            print(missingvaluemessage % ('resource', rowindex))
            continue
         printline(options, tfname, 'name = ' + value)
         printline(options, tfname, enddata)
         continue

      printline(options, tfname, resourceheader % (resources[sheettype], resource))

      savegroup = None

      # Loop through columns skipping first 2 columns (file and resource) and last 2 columns (module and comments).
      for columnindex in range(columns.size-2):
         if columnindex < 2:
            continue

         column = columns[columnindex]
         value = row[column]
         empty = novalue(value)
         if empty:
            continue

         if isinstance(value, int):
            value = str(value)

         column = column.replace(' ', '')

         dotpos = column.find('.')
         if dotpos >= 0:
            subgroup = column[0:dotpos]
            subcolumn = column[dotpos+1:]
            column = subcolumn
            if savegroup == None:
               # No group yet so start group.
               savegroup = subgroup
               # Remove trailing digits from duplicated columns of arrays.
               subgroup = subgroup.rstrip('0123456789')
               printline(options, tfname, subgroup + ' {')
            elif savegroup != subgroup:
               # Adjacent groups so close previous group and start next group.
               savegroup = subgroup
               # Remove trailing digits from duplicated columns of arrays.
               subgroup = subgroup.rstrip('0123456789')
               printline(options, tfname, '}')
               printline(options, tfname, subgroup + ' {')
         elif savegroup != None:
            # End of group so close group.
            savegroup = None
            printline(options, tfname, '}')

         printline(options, tfname, column + ' = ' + value)

      if savegroup != None:
         # End of row so close group.
         savegroup = None
         printline(options, tfname, '}')

      printline(options, tfname, endresource)

   return

def gentf(options):
   genpath = options['genpath']
   propfile = options['propfile']
   propname = options['propname']

   print(starttfmessage % propfile)

   sheets = loadfile(options)
   for name, sheet in sheets.items():
      name = name.replace(' ', '')

      df = loadframe(options, pd, sheet)

      if name.find('variables', 0, 9) >= 0:
         genvariables(options, name, sheet, df)
      elif name.find('outputs', 0, 7) >= 0:
         genoutputs(options, name, sheet, df)
      elif name.find('cloudinits', 0, 10) >= 0:
         gencloudinits(options, name, sheet, df)
      elif name.find('modules', 0, 7) >= 0:
         genmodules(options, name, sheet, df)
      elif name.find('providers', 0, 9) >= 0:
         genproviders(options, name, sheet, df)
      elif name.find('versions', 0, 8) >= 0:
         genversions(options, name, sheet, df)
      elif name.find('aclrules', 0, 8) >= 0:
         genaclresources(options, name, sheet, df)
      else:
         genresources(options, name, sheet, df)

   print(donetfmessage % (propname, genpath))

   return

def main():
   print(COPYRIGHT)
   print(toolheader)

   parser = argparse.ArgumentParser(description=toolheader)

   parser.add_argument('inputvalue', nargs='?', default=options['datapath'], help='input folder (default: ' + options['datapath'] + ')')

   parser.add_argument('-o', action='store', dest='outputfolder', default=options['genpath'], help='output folder (default: ' + options['genpath'] + ')')

   parser.add_argument('-t', dest='datatype', default=options['datatype'], help='type of input files (default: ' + options['datatype'] + ')')

   parser.add_argument('--version', action='version', version='tabular-terraform ' + COPYRIGHT.split(' ')[1])

   results = parser.parse_args()

   options['datapath'] = results.inputvalue.replace(' ', '')
   options['datatype'] = results.datatype.replace(' ', '')
   options['genpath'] = results.outputfolder.replace(' ', '')

   datapath = options['datapath']
   datatype = options['datatype']
   genpath = options['genpath']
  
   # Check for existing input directory and exit if not valid.
   if not os.path.isdir(os.path.join(datapath, datatype)):
      print(invalidinputdirectorymessage % os.path.join(datapath, datatype))
      return

   genbackup = None
   # Check for existing output directory and backup if exists.
   if os.path.exists(genpath):
      backup = 1
      found = False
      genbackup = None
      # Find a new backup directory.
      while not found:
         genbackup = genpath + '.backup' + str(backup)
         if os.path.exists(genbackup):
            backup += 1
         else:
            found = True
      # Move existing output directory to backup directory.
      shutil.move(genpath, genbackup)
      print(backupdirectorymessage % (genpath, genbackup))

   # Create new empty output directory.
   os.makedirs(genpath)

   # Copy existing terraform.tfstate to output directory.
   if genbackup != None and os.path.isfile(os.path.join(genbackup, 'terraform.tfstate')):
      shutil.copy(os.path.join(genbackup, 'terraform.tfstate'), os.path.join(genpath, 'terraform.tfstate'))

   # Copy existing .terraform to output directory.
   if genbackup != None and os.path.isdir(os.path.join(genbackup, '.terraform')):
      shutil.copytree(os.path.join(genbackup, '.terraform'), os.path.join(genpath, '.terraform'))

   datapath = options['datapath']
   datatype = options['datatype']
   filelist = os.listdir(os.path.join(datapath, datatype))

   # Copy terraform-cloudinits if exists to output directory.
   #if os.path.isdir(os.path.join(datapath, 'terraform-cloudinits')):
   #   terraformfiles = os.listdir(os.path.join(datapath, 'terraform-cloudinits'))
   #   for terraformfile in terraformfiles:
   #      shutil.copy(os.path.join(datapath, 'terraform-cloudinits', terraformfile), genpath)

   # Copy ansible-playbooks if exists to output directory.
   if os.path.isdir(os.path.join(datapath, 'playbooks')):
      shutil.copytree(os.path.join(datapath, 'playbooks'), os.path.join(genpath, 'playbooks'))         

   # Generate provider.
   #print(startprovidermessage)
   #genprovider(options)

   # Generate versions.
   #print(startversionsmessage)
   #genversions(options)

   # Process all files in specified directory.
   found = False
   for afile in filelist:
      propfile = os.path.join(datapath, datatype, afile)
      propfilenopath = os.path.basename(propfile)
      propname = os.path.splitext(propfilenopath)[0]
      propext = os.path.splitext(propfilenopath)[1][1:]
      if (os.path.isfile(propfile)):
         found = True
         options['propfile'] = propfile
         options['propname'] = propname
         options['propext'] = propext
         gentf(options)
   if (not found):
      print(missinginputmessage % results.inputvalue)

   return
      
main()
