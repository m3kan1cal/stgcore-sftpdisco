#!/bin/zsh

# Capture user input for replication in AWS CLI and
# other scripting commands.
read '?AWS CLI profile (stgmeridian-prod): ' profile
profile="${profile:-stgmeridian-prod}"

# Options: us-west-2/us-east-1
read '?AWS region (us-west-2): ' region
region="${region:-us-west-2}"

# Options: sandbox/nonprod/prod
read '?Environment (nonprod): ' environment
environment="${environment:-nonprod}"

read '?Account set (meridian): ' accountSet
accountSet="${accountSet:-meridian}"

# User or service account to create. For service accounts, pattern is:
# usertocreateX_svc where X is a numerical sequence.
# Example: medispan1_svc or optum1_svc
read '?User to create (user1_svc): ' username
username="${username:-user1_svc}"

# Password: https://www.lastpass.com/password-generator
# 16 characters, upper/lower/numbers/symbols/easy to read
read '?Password for user (Z8xHEB8VrN@RZdHj): ' password
password="${password:-'Z8xHEB8VrN@RZdHj'}"

# Public SSH key for user being created. Optional.
read '?Public SSH key for user (optional): ' publicKey
publicKey="${publicKey:-optional}"

# Set the user-specific variables.
sharesBucket="$accountSet-$environment-shares"
homeDirectory="/$sharesBucket/home/$username"
scopedPolicy=`cat ./scopedpolicy_tmpl.json`
secret=`cat ./secretuser_tmpl.json`

# Get the SFTP IAM role for standard use.
sftpRole=$(aws iam list-roles --profile $profile \
    --region $region \
    | jq -r '.Roles[] | select(.RoleName == "StandardSFTPUserRole") | .Arn')

# Get the SFTP Transfer server ID.
sftpServer=$(aws transfer list-servers --profile $profile \
    --region $region \
    | jq -r '.Servers[] | select(.EndpointType == "PUBLIC") | .ServerId')

# Update secret template with dynamic values.
secret=${secret/USER_PASSWORD/$password}
secret=${secret/SFTP_ROLE/$sftpRole}
secret=${secret/HOME_DIRECTORY/$homeDirectory}
secret=${secret/PUBLIC_KEY/$publicKey}

# Need to escape the double quotes for dynamic JSON.
scopedPolicy=${scopedPolicy//\"/\\\"}
secret=${secret/SCOPED_POLICY/$scopedPolicy}

# Create a new secret.
aws secretsmanager create-secret --profile $profile \
    --region $region \
    --name "$environment/SFTP/core/$username" \
    --description "Access to SFTP server for core STG services in sandbox environment." \
    --secret-string "$secret" \
    --tags Key="ResourceGoup",Value="STGPillarOfAutumn-ResourceGroup" \
        Key="Name",Value="STGPillarOfAutumn-SFTPTransferUser" \
        Key="Customer",Value="RealRx" \
        Key="Environment",Value=$environment \
        Key="Application",Value="STGPillarOfAutumn" \
        Key="ApplicationVersion",Value="1.0.0" \
        Key="ApplicationRole",Value="Security" \
        Key="InfrastructureVersion",Value="1.0.0" \
        Key="ProjectCostCenter",Value="9493076548" \
        Key="OperatingCostCenter",Value="9493076548" \
        Key="Owner",Value="fireteamosiris@withstg.com" \
        Key="SecurityContact",Value="fireteamosiris@withstg.com" \
        Key="Confidentiality",Value="PII/PHI" \
        Key="Compliance",Value="HIPAA" \
        Key="AutomateOption",Value="OptIn" \
        Key="AutomateAt",Value="9999-12-31 13:37"
