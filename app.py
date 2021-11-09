"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

import os
from pathlib import Path
from aws_cdk import (
    aws_lambda as lambda_,
    aws_apigateway as api_gw,
    aws_efs as efs,
    aws_ec2 as ec2,
    core as cdk,
)


class ServerlessHuggingFaceStack(cdk.Stack):
    def __init__(self, scope: cdk.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # EFS needs to be setup in a VPC
        vpc = ec2.Vpc(self, "Vpc", max_azs=2)

        # creates a file system in EFS to store cache models
        fs = efs.FileSystem(
            self, "FileSystem", vpc=vpc, removal_policy=cdk.RemovalPolicy.DESTROY
        )
        access_point = fs.add_access_point(
            "MLAccessPoint",
            create_acl=efs.Acl(owner_gid="1001", owner_uid="1001", permissions="750"),
            path="/export/models",
            posix_user=efs.PosixUser(gid="1001", uid="1001"),
        )

        # %%
        # iterates through the Python files in the docker directory
        docker_folder = os.path.dirname(os.path.realpath(__file__)) + "/inference"
        pathlist = Path(docker_folder).rglob("*.py")
        for path in pathlist:
            base = os.path.basename(path)
            filename = os.path.splitext(base)[0]
            # Lambda Function from docker image
            function = lambda_.DockerImageFunction(
                self,
                filename,
                code=lambda_.DockerImageCode.from_image_asset(
                    docker_folder, cmd=[filename + ".handler"]
                ),
                memory_size=8096,
                timeout=cdk.Duration.seconds(600),
                vpc=vpc,
                filesystem=lambda_.FileSystem.from_efs_access_point(
                    access_point, "/mnt/hf_models_cache"
                ),
                environment={"TRANSFORMERS_CACHE": "/mnt/hf_models_cache"},
            )

            api = api_gw.RestApi(
                self,
                f"{filename}-api",
                rest_api_name=f"{filename} Service",
                description=f"This service serves {filename}.",
                default_cors_preflight_options=api_gw.CorsOptions(
                    allow_origins=api_gw.Cors.ALL_ORIGINS,
                    allow_methods=api_gw.Cors.ALL_METHODS,
                ),
            )

            # adds method for the function
            lambda_integration = api_gw.LambdaIntegration(function)

            api.root.add_method("ANY")
            api_resource = api.root.add_resource(filename)
            api_resource.add_method("GET", lambda_integration)
            api_resource.add_method("POST", lambda_integration)


app = cdk.App()

ServerlessHuggingFaceStack(app, "ServerlessHuggingFaceStack")

app.synth()
# %%
