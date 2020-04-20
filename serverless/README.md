## STG Disco

Repository for core Sentinel services for STG Labs. Various sentinel types modeled after https://www.halopedia.org/Sentinel.

## Style guides and tools

This project holds an opinionated view on code formatting and styling. It enforces a consistent style to help promote a unified developer experience.

Plugins being used:

- [Prettier - VS Code](https://marketplace.visualstudio.com/items?itemName=esbenp.prettier-vscode)
- [Flake8]()

Style guides referenced:

Local development tools used:

- [LocalStack](https://github.com/localstack/localstack)
- [Docker Desktop](https://www.docker.com/products/docker-desktop)

## Getting started with Python

To create a virtual environment, go to your project's directory and run `venv`.

On macOS and Linux:

```zsh
python3 -m venv venv
```

On Windows:

```zsh
py -m venv venv
```

The second argument is the location to create the virtual environment. Generally, you can just create this in your project and call it `venv`. The `venv` will create a virtual Python installation in the `venv` folder.

Before you can start installing or using packages in your virtual environment you'll need to activate it. Activating a virtual environment will put the virtual environment-specific python and pip executables into your shell's PATH.

On macOS and Linux:

```zsh
source venv/bin/activate
```

On Windows:

```zsh
.\venv\Scripts\activate
```

You can confirm you're in the virtual environment by checking the location of your Python interpreter, it should point to the `venv` directory.

On macOS and Linux:

```zsh
which python
.../venv/bin/python
```

On Windows:

```zsh
where python
.../venv/bin/python.exe
```

As long as your virtual environment is activated, pip will install packages into that specific environment and youj'll be able to import and use packages in your Python application.

If you want to switch projects or otherwise leave your virtual environment, simply run:

```zsh
deactivate
```

If you want to re-enter the virtual environment just follow the same instructions above about activating a virtual environment. There's no need to re-create the virtual environment.

Once the virtual environment is activated, then install all of the packages for this project using `pip3` and the `-r` flag.

```zsh
pip3 install -r requirements.txt
```

Now you should have all the Python dependencies needed to build/run the solution.

## Getting started with Serverless

To get going quickly, first clone the repository and install some dependencies.

- Install the `serverless` framework from here: https://serverless.com/framework/docs/providers/aws/guide/installation/.
- Install the `LocalStack` local AWS cloud stack for offline testing.
- Install the `Docker Desktop` tooling to run `LocalStack` and other docker services.

Once the `serverless` framework, `LocalStack` offline cloud stack, and `Docker Desktop` are installed, install the project dependencies stored in the `package.json` file.

Then install the serverless plugin for Python compatibility.

```zsh
sls plugin install -n serverless-python-requirements
```

Now you're ready to crack open the `serverless.yml` file in the root of this project and confirm that the defaults are what you want. When you're good with the `serverless.yml` file, start the `LocalStack` instance for offline services and move on to unit testing.

```zsh
# Pass any other environment variables in front of localstack command.
docker-compose up -d

# Create offline testing topics.
aws sns create-topic --endpoint-url=http://localhost:4575 --name localtopic
```

**Note:** you can also use `docker compose up` if you prefer instead of `localstack` command.

Once tests are passing, run the function locally without touching AWS platform.

```zsh
# Use the --environment local flag to make sure we're not trying to resolve
# any AWS SSM parameter store values.
sls invoke local --verbose \
    --environment local \
    --function SCPDeploy -l \
    --data '{"RequestType" : "NoAction", "RequestId" : "9db53695-b0a0-47d6-908a-ea2d8a3ab5d7", "ResponseURL" : "https://...", "ResourceType" : "Custom::ServiceControlPolicy", "LogicalResourceId" : "SCPPolicy1", "StackId" : "arn:aws:cloudformation:us-west-2:446581252830:stack/STGDisco-Organization-SCPs-P-CF/09a94f60-0f07-11ea-80f0-0a6d23b8818c", "ResourceProperties" : {"PolicyName": "SCP_DENY_EXCEPT_WHITELIST_REGION", "PolicyDescription": "This SCP denies access to any operations outside of the specified AWS Region, except for actions in the listed services (These are global services that cannot be whitelisted based on region).", "PolicyContents": "{}"}}'
```

Deploy Lambda functions and resources.

```bash
# Note that if deploying to another region you may need to include the following:
# --zoneName "realrxapis.com" \
# --cfnRole "arn:aws:iam::446581252830:role/StandardCloudFormationDeployRole"

profile="stgmeridian-prod"
region="us-west-2"
account="meridian"
environment="prod"
customer="RealRx"

iamStack="STGPillarOfAutumn-Lambda-IAMRoles-P-CF"
route53Stack="STGPillarOfAutumn-Route53-ExtendedZones1-P-CF"
acmStack="STGPillarOfAutumn-ACM-ExtendedZones1-P-CF"
hostedZoneName="realrxapis.com"
cfnRole="arn:aws:iam::748468055876:role/StandardCloudFormationDeployRole"

# Deploy serverless functions & APIs.
sls deploy --verbose --aws-profile $profile \
    --environment $environment \
    --region $region \
    --account $account \
    --customer $customer \
    --iamStack $iamStack \
    --route53Stack $route53Stack \
    --acmStack $acmStack \
    --hostedZoneName $hostedZoneName \
    --cfnRole $cfnRole
```

Test the functions out remote once deployed.

```bash
profile="stgmaethrillian-nonprod"
sls invoke --verbose --aws-profile $profile \
  --function SCPDeploy \
  --data '{"RequestType" : "NoAction", "RequestId" : "9db53695-b0a0-47d6-908a-ea2d8a3ab5d7", "ResponseURL" : "https://...", "ResourceType" : "Custom::ServiceControlPolicy", "LogicalResourceId" : "SCPPolicy1", "StackId" : "arn:aws:cloudformation:us-west-2:446581252830:stack/STGDisco-Organization-SCPs-P-CF/09a94f60-0f07-11ea-80f0-0a6d23b8818c", "ResourceProperties" : {"PolicyName": "SCP_DENY_EXCEPT_WHITELIST_REGION", "PolicyDescription": "This SCP denies access to any operations outside of the specified AWS Region, except for actions in the listed services (These are global services that cannot be whitelisted based on region).", "PolicyContents": "{}"}}'
```

Use `curl` to check the health check in API Gateway endpoints.

```zsh
curl --request GET \
  --url "https://disco.realrxapis.com/v1/prod/api/healthcheck" \
  --header "content-type: application/json"
```

Use `curl` to send a mail relay request through the AWS SES service.

```zsh
# For normal authorized request.
curl --request POST \
  --url "https://disco.realrxapis.com/v1/prod/api/controllers/mail/relay" \
  --header "content-type: application/json" \
  --header "X-API-Key: 5zVlYaXFU41cRvPZeFYd3akE2cMj5YD9ao27AEFd" \
  --data '{"subject":"SENTINELS - RealRx site inquiry","recipient":"fireteamosiris@withstg.com","message":"This is my body. Do you like it?"}'

# For suspected bot request.
curl --request POST \
  --url "https://disco.realrxapis.com/v1/prod/api/controllers/mail/relay" \
  --header "content-type: application/json" \
  --header "X-API-Key: 5zVlYaXFU41cRvPZeFYd3akE2cMj5YD9ao27AEFd" \
  --data '{"subject":"SENTINELS - RealRx site inquiry","recipient":"fireteamosiris@withstg.com","message":"This is my body. Do you like it?","expedite":"not empty"}'
```

## Integration testing

This project uses [Postman](https://www.getpostman.com/) and [Newman](https://learning.getpostman.com/docs/postman/collection_runs/command_line_integration_with_newman/) for integration tests. To run the integration tests, import the Postman API collection in to Postman and run via the UI or the cli.

## Contributing

Want to get involved? Fork this repo, make some changes, submit a **pull request** and we'll get the brain trust to review and merge your changes. All are encouraged to join in this effort.
