# SFTP Transfer CloudFormation stacks & related resources

AWS Transfer for SFTP is a fully managed service that enables the transfer of files directly into and out of Amazon S3 using the Secure File Transfer Protocol (SFTP)— also known as Secure Shell (SSH) File Transfer Protocol. AWS helps to seamlessly migrate file transfer workflows to AWS Transfer for SFTP—by integrating with existing authentication systems, and providing DNS routing with Amazon Route 53 so nothing changes for customers and partners, or their applications. With data in S3, we can use it with AWS services for processing, analytics, machine learning, and archiving.

By default, a new AWS SFTP server uses its internal user directory for SSH key-based authentication. We're going to change it to use an IdP of our choice. To do this, we're going to specify `--identity-provider-type API_GATEWAY` with an API Gateway endpoint to map access to the custom authentication provider. We're going to build both the SFTP service and the custom IdP in this solution.

## Creating the API Gateway and Lambda (IdP) stack

For Part 1, we need to create the custom IdP stack with API Gateway and Lambda. We're going to make these assumptions:

- Python 3 (with pip3, venv) is installed and on your path - https://www.python.org/downloads/
- Node.js and npm are installed - https://nodejs.org/en/download/
- Current version of AWS CLI is installed - https://aws.amazon.com/cli/
- Serverless framework is installed - https://serverless.com/framework/docs/providers/aws/guide/installation/

To get going, focus on the contents of the `serverless` folder. Review `serverless.yml` for any changes (app name, IAM roles, and S3 buckets.) Make those changes before you move on. The S3 buckets this base example uses end up being `stoic-nonprod-artifacts` with an object key of `cloudformation/disco`, but you can change to what you want it to be.

When you're ready, move on via the command line. Switch to the serverless directory.

```zsh
cd serverless
```

Install the `serverless` dependencies.

```zsh
npm i
```

Activate your virtual Python 3 environment.

```zsh
python3 -m venv venv
source venv/bin/activate
```

Use `pip3` to install the Python dependencies.

```zsh
pip3 install -r requirements.txt
```

Install the `serverless` plugin for Python compatibility. The shorthand for `serverless` commands is `sls`.

```zsh
sls plugin install -n serverless-python-requirements
```

Review the `resources\lambdaroles_tmpl.yml` CloudFormation template and make any changes you see fit. Deploy the IAM role that Lambda functions will execute under.

```zsh
profile="stoic"
region="us-west-2"
stack="STGDisco-Lambda-IAMRoles-P-CF"

# Build AWS IAM roles for security.
aws cloudformation deploy --profile $profile \
    --region $region \
    --stack-name $stack \
    --template-file ./resources/lambdaroles_tmpl.yml \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides AccountSet="stoic" \
        Environment="nonprod"
```

Using the name of the CloudFormation stack we created above, deploy the Serverless payload to create the API Gateway, Lambda function, and other AWS resources for your API. Replace the `iamStack` variable with the stack named previously.

```zsh
profile="stoic"
region="us-west-2"
environment="nonprod"

# Deploy serverless functions & APIs.
sls deploy --verbose --aws-profile $profile \
    --environment $environment \
    --region $region \
    --iamStack="STGDisco-Lambda-IAMRoles-P-CF"
```

At this point, we have a fully functioning identity provider that relies on API Gateway as the interface mechanism and harnesses Lambda and Secrets Manager as the actual IDP. Note the endpoints that Serverless generates during the creation of our resources. We're going to use the SFTP Authorize Lambda function and the API Gateway endpoint in the next part. Our endpoint for SFTP authorization is also protected through the use of AWS Resource Policies that we've attached to prevents calls of our API from outside our own AWS account.

To lightly kick the tires on the services, use `curl` to check the health check endpoint we created via the API Gateway endpoint.

```zsh
curl --request GET \
  --url "https://ehugtybas1.execute-api.us-west-2.amazonaws.com/nonprod/api/health" \
  --header "content-type: application/json"
```

Now we can move on to Part 2 and actually create the SFTP service.

## Creating the AWS Transfer for SFTP server stack

For Part 2, we're going to create the AWS Transfer for SFTP server and the users that can connect to it. We will create a scoped down policy user that only has access to their own home directory. We'll also provide tips on creating our own admin user that isn't limited to the confines of a specific home directory in S3.

Change directories so that you're at the root directory. Then create the SFTP server.

```zsh
profile="stoic"
region="us-west-2"
stack="STGDisco-SFTPTransfer1-P-CF"

# Build Route53 zones and record sets.
aws cloudformation deploy --profile $profile \
    --stack-name $stack \
    --region $region \
    --template-file ./resources/sftptransfer_tmpl.yml \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides IDPAPIStack="STGDisco-BaseService-SLSLambda-P-CF" \
        Environment="nonprod"
```

For each user to be added to the Transfer SFTP server in the future, they'll need to be created in the identity provider secrets store. They'll also need to have their public SSH key and/or their password added along with their user.

Generally, users will create their own SSH key pair and send us the public key to add to their user. In the event that our teams are the ones creating the SSH key pair, this command should be run with filling the prompts as required.

```zsh
useremail="someemail@somedomain.com"
ssh-keygen -t rsa -b 4096 -C $useremail
```

Once the SSH public key is located somewhere that can be retrieved, run the following commands to create the SFTP user. Occasionally, we're going to run in to clients that can't support SSH public keys, so we have the option of bypassing SSH keys and using password authentication. Whichever route is decided upon, replace the values below with the ones you want to attach to the user being created.

## Creating secrets for users

We're going to first create our normal user that is considered a "scoped down policy" user so they're locked in to only their home directory in the S3 bucket of your choosing. For this solution, our user home directories will be in the `stoic-nonprod-shares` bucket and will have a bucket key similar to `home/username`.

```zsh
profile="stoic"
region="us-west-2"
environment="nonprod"

# Set the user-specific login credentials.
username="normaluser1_svc"
password='S8zCV4kqCDDqRHG!'
publicKey="somekey"

# Set user home directory and policies.
sharesBucket="stoic-$environment-shares"
homeDirectory="/$sharesBucket/home/$username"
scopedPolicy=`cat ./resources/scopedpolicy_tmpl.json`
secret=`cat ./resources/secretuser_tmpl.json`

# Get the SFTP IAM role for standard use.
sftpRole=$(aws iam list-roles --profile $profile \
    --region $region \
    | jq -r '.Roles[] | select(.RoleName == "StandardSFTPUserRole") | .Arn')

# Get the SFTP Transfer server ID.
sftpServer=$(aws transfer list-servers --profile $profile \
    --region $region \
    | jq -r '.Servers[] | select(.EndpointType == "PUBLIC") | .ServerId')

# Update secret template with dynamic values using search/replace pattern.
secret=${secret/USER_PASSWORD/$password}
secret=${secret/SFTP_ROLE/$sftpRole}
secret=${secret/HOME_DIRECTORY/$homeDirectory}
secret=${secret/PUBLIC_KEY/$publicKey}

# Need to escape the double quotes for dynamic JSON.
scopedPolicy=${scopedPolicy//\"/\\\"}
secret=${secret/SCOPED_POLICY/$scopedPolicy}

# Create a new secret in secrets manager for new user.
aws secretsmanager create-secret --profile $profile \
    --region $region \
    --name "$environment/SFTP/core/$username" \
    --description "Access to SFTP server for core STG services in sandbox environment." \
    --secret-string "$secret" \
    --tags Key="ResourceGoup",Value="STGDisco-ResourceGroup" \
        Key="Name",Value="STGDisco-SFTPTransferUser" \
        Key="Customer",Value="STG" \
        Key="Environment",Value="nonprod" \
        Key="Application",Value="STGDisco" \
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
```

To create an admin user, slightly modify the commands from the above section.

- `secretuser_tmpl.json` should reference instead `secretadmin_tmpl.json`
- Comment out the line that looks like this: `scopedPolicy=${scopedPolicy//\"/\\\"}`
- Comment out this line, also: `secret=${secret/SCOPED_POLICY/$scopedPolicy}`

Then run the code snippet again and we should have a user that is more like a traditional admin that can browse any folder in the confines of our SFTP file shares in S3.

## Updating existing secrets for users

Once secrets are created, we may find that we need to update them occasionally. This can be done with a slight variation when updating a secret is required, instead of creating a new one.

```zsh
profile="stoic"
region="us-west-2"
environment="nonprod"
username="normaluser1_svc"

aws secretsmanager update-secret --profile $profile \
    --region $region \
    --secret-id "$environment/SFTP/core/$username" \
    --description "Access to SFTP server for core STG services in sandbox environment." \
    --secret-string "$secret"
```

## Test connectivity to SFTP server with user

Once we have an SFTP user created, we can test the custom SFTP identity provider using password authentication as follows.

```zsh
profile="stoic"
region="us-west-2"
username="normaluser1_svc"
password='S8zCV4kqCDDqRHG!'

# Get the SFTP Transfer server ID.
sftpServer=$(aws transfer list-servers --profile $profile \
    --region $region \
    | jq -r '.Servers[] | select(.EndpointType == "PUBLIC") | .ServerId')

aws transfer test-identity-provider --profile $profile \
    --region $region \
    --server-id $sftpServer \
    --user-name $username \
    --user-password $password
```

If the identity provider succeeds in authenticating a user, it should return a 200 OK response in the JSON payload.

```zsh
{
    "Response": "{\"Policy\": \"{\"Version\":\"2012-10-17\",\"Statement\":[{\"Sid\":\"AllowListingOfUserFolder\",\"Effect\":\"Allow\",\"Action\":[\"s3:ListBucket\",\"s3:GetBucketLocation\"],\"Resource\":\"arn:aws:s3:::stoic-nonprod-shares\",\"Condition\":{\"StringLike\":{\"s3:prefix\":[\"home/normaluser1_svc/*\",\"home/normaluser1_svc\"]}}},{\"Sid\":\"AllowHomeDirObjectAccess\",\"Effect\":\"Allow\",\"Action\":[\"s3:PutObject\",\"s3:GetObject\",\"s3:GetObjectVersion\",\"s3:DeleteObject\",\"s3:DeleteObjectVersion\"],\"Resource\":\"arn:aws:s3:::stoic-nonprod-shares/home/normaluser1_svc*\"}]}\",\"Role\": \"arn:aws:iam::750444023825:role/StandardSFTPUserRole\",\"HomeDirectory\": \"/stoic-nonprod-shares/home/normaluser1_svc\"}",
    "StatusCode": 200,
    "Message": "",
    "Url": "https://ehugtybas1.execute-api.us-west-2.amazonaws.com/nonprod/servers/s-c3948c2e9c764ca98/users/normaluser1_svc/config"
}
```

Once the identify provider verification is passing, it's time to validate the user/service account can connect through SFTP protocols. To verify connection to the SFTP server, use the following on the command line with one of the users created in the identity provider secret store.

```zsh
# For user/service account with SSH public key (note that private key is used to authenticate.)
sftp -i ~/.ssh/id_rsa normaluser1_svc@s-c3948c2e9c764ca98.server.transfer.us-west-2.amazonaws.com

# For user/service account with password authentication.
sftp normaluser1_svc@s-c3948c2e9c764ca98.server.transfer.us-west-2.amazonaws.com
```

## Connectivity for traditional SFTP clients

Clients and users will need to connect to the SFTP server periodically. Sometimes this will be manual through an SFTP client or through automation scripts. Configuring SFTP connections in automation scripts and/or SFTP clients will differ slightly depending on the tool. In general, the settings below are what clients and users/service accounts will need to connect.

**Host:** s-c3948c2e9c764ca98.server.transfer.us-west-2.amazonaws.com
**Port:** 22
**User:** normaluser1_svc
**Password:** S8zCV4kqCDDqRHG!
**SSH Private Key:** somekey

## Contributing

Want to get involved? Fork this repo, make some changes, submit a **pull request** and we'll get the brain trust to review and merge your changes. All are encouraged to join in this effort.
