# screenshot-to-code

A simple tool to convert screenshots, mockups and Figma designs into clean, functional code using Bedrock.

Supported stacks:

- HTML + CSS
- HTML + Tailwind
- React + Tailwind
- Vue + Tailwind
- Bootstrap
- Ionic + Tailwind
- SVG

Supported AI models:

- Claude 3.5 Sonnet - Best model!
- Claude 3 Opus
- Claude 3 Sonnet
- Claude 3 Haiku

## deploy on docker-composer

- Run the following commond to create an .env file in the root directory of the project.

```linux
touch .env
```

Note: You can enter the environment variables to be set in the .env file.

- Run the following command in the root directory of the project.

```linux
docker-compose up --build
```

Note: You can remove the '--build' without changing anything

## deploy on ecs

- Run the following commands to set the relevant ACCOUNT_ID and AWS_REGION.

```linux
export ACCOUNT_ID=$(aws sts get-caller-identity --output text --query Account)
export AWS_REGION=<your-region-name>
```

- Run the following commands to create the relevant image repository.

```linux
aws ecr get-login-password --region ${AWS_REGION} \
  | docker login --username AWS \
  --password-stdin ${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

aws ecr create-repository \
  --repository-name screenshot-to-code-frontend \
  --region ${AWS_REGION}

aws ecr create-repository \
  --repository-name screenshot-to-code-backend \
  --region ${AWS_REGION}
```

- Run the following commands to package the multi-architecture image and upload it to ECR.

```linux
cd frontend
docker buildx build \
  --build-arg VITE_BEHIND_SAME_ALB=true \
  --tag ${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/screenshot-to-code-frontend:latest \
  --platform linux/amd64,linux/arm64 \
  --push .

cd ../backend
docker buildx build \
  --tag ${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/screenshot-to-code-backend:latest \
  --platform linux/amd64,linux/arm64 \
  --push .

cd ..
```
- Run the following commands to create the stack template.

```linux
cp deploy-on-ecs.yaml template.yaml
sed -i "s/<your-account-id>/${ACCOUNT_ID}/g" template.yaml
sed -i "s/<your-region>/${AWS_REGION}/g" template.yaml
```

- Run the following commands to create an ECS-based deployment.

```linux
aws cloudformation create-stack \
  --stack-name screenshot-to-code-stack \
  --template-body file://template.yaml \
  --capabilities CAPABILITY_IAM \
  --region ${AWS_REGION}

aws cloudformation wait stack-create-complete \
  --stack-name screenshot-to-code-stack \
  --region ${AWS_REGION}
```

- Run the following commands to view the access link.

```linux
aws cloudformation describe-stacks \
  --region ${AWS_REGION} \
  --query "Stacks[?StackName=='screenshot-to-code-stack'][].Outputs[?OutputKey=='LoadBalancerDNS'].OutputValue" \
  --output text
```

- Clean up the environment: Empty the S3 bucket used to store the generated images.

```linux
aws s3 rm s3://screenshot-to-code-${ACCOUNT_ID}/ --recursive --region ${AWS_REGION}
```

- Clean up the environment: Delete the created Stack.

```linux
aws cloudformation delete-stack \
  --stack-name screenshot-to-code-stack \
  --region ${AWS_REGION}
```

- Clean up the environment: Delete the image.

```linux
aws ecr delete-repository \
  --repository-name screenshot-to-code-frontend \
  --region ${AWS_REGION} \
  --force

aws ecr delete-repository \
  --repository-name screenshot-to-code-backend \
  --region ${AWS_REGION} \
  --force
```