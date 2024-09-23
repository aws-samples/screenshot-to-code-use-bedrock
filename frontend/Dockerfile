FROM public.ecr.aws/docker/library/node:22-bullseye-slim AS build-stage

# Set the environment
ARG VITE_BEHIND_SAME_ALB
ENV VITE_BEHIND_SAME_ALB=$VITE_BEHIND_SAME_ALB

# Set the working directory in the container
WORKDIR /app

# Copy package.json and yarn.lock
COPY package.json yarn.lock /app/

# Set the environment variable to skip Puppeteer download
ENV PUPPETEER_SKIP_DOWNLOAD=true

# Install dependencies
RUN yarn install

# Copy the current directory contents into the container at /app
COPY ./ /app/

# Build the application
RUN yarn build

# Build the production image
FROM nginx:stable-alpine AS production-stage

# Copy the build output to replace the default nginx contents
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Expose port 80 to the outside world
EXPOSE 80