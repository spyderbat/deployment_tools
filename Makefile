IMAGE_NAME=cluster-collector
VERSION=latest

push:
	aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws/a6j2k0g1
	docker buildx build --push --platform linux/arm64,linux/amd64 -t public.ecr.aws/a6j2k0g1/$(IMAGE_NAME):$(VERSION) .

