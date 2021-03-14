# How to Attach to a Container from VS Code

## Prelude

When we would like to run our code in a container environment; we can do the following:
- Modify the container entrypoint and exec into the container [1]
  - docker run -i -d entrypoint=bash *container_id*
  - docker exec -it *container_id* bash
  - Shell is now running in the container and we can manually run commands in it.
- Copy files to and from the container for inspection/comparison [1]
  - Write log-like files to the container and then copy them to the host to check.

**However, can we do better?**

In this guide, we will detail on how to debug in a container created with a multi-stage image **without** using VS Code Remote Development Extention.
- We will exemplify:
  - 2 debugger alternatives.
  - 1 simple script and 1 flask service
  - Both docker and docker-compose version

## Multi-Stage Containers with Debugger [1, 2]

- This technique differs from VS Code Remote Development Extension in several ways:
  - We do not open VS Code project in a container; instead we attach to the container which serves the debugger.
  - We may add our desired debugger. (Should check options in Remote Development Extension)

This approach has several drawbacks in comparison to VS Code Remote Development Extention:
- We need to re-build the image for each change.
  - We can overcome this problem by using volumes.
  - However, we still need to re-run the container each time we need to execute/debug our code.
- If required extensions (linters etc.) is not installed on our local machine, we may not use aiding features in coding~.

**Steps:**
1) Prepare a multi-stage dockerfile [3]
2) Prepare launch.json to specify how VS CODE will attach to the container.
3) Build image and run the container.
4) Run the desired file (add debug points if needed).

We will be able to observe the variables; step in/over the code; see output in debug console etc.


*Dockerfile:*
- When we have a multi-stage dockerfile, we can build any desired stage by using "--target" option.
- Such a multi-stage dockerfile can be used both for development and production where we build the corresponding stage only.
- We copy requirements and install them; assuming they will change rarely.

*Here is an example dockerfile which keeps 2 alternative debugger stages:*

```dockerfile
FROM python:3.7.3-alpine3.9 AS base

WORKDIR /workspace
COPY ./requirements.txt /workspace/requirements.txt
RUN pip install -r requirements.txt

WORKDIR /workspace/sources

# debugger1

FROM base AS debugger1
RUN pip install debugpy
ENTRYPOINT ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "--wait-for-client"]

# debugger2

FROM base AS debugger2
RUN pip install ptvsd
ENTRYPOINT ["python", "-m", "ptvsd", "--host", "0.0.0.0", "--port", "5678", "--wait"]

# primary

FROM base AS primary
ENTRYPOINT ["python"]
```

Here is how we build and run it:

```shell
docker build . --target debugger -t example1

docker run -p 5678:5678 -v /absolute_path_till_project_folder/vscode_primitive_docker_env/example/sources:/workspace/sources example case.py
```

Let's say we would like to debug case2.py (under basic_example sources) which requires port 5000, by using "ptvsd".

```shell
cd /absolute_path_till_project_folder/vscode_primitive_docker_env/basic_example

docker build . --target debugger2 -t basic_example

docker run -p 5000:5000 -p 5678:5678 -v /absolute_path_till_project_folder/vscode_primitive_docker_env/basic_example/sources:/workspace/sources example case2.py
```

**Gotchas**
- We will have a docker volume to avoid copying file and re-building the image each time.
- We add the port mapping for the debugger (also add other port mappings if your service/script needs).
- When the container is up, it will wait for user to execute the code from VS Code.
  - When we have a service, we may omit "--wait-for-client"/"--wait" as the container will not exit.
  - However, for a usual script, we need it; as the container will exit immediate after executing the script.
- Having ENTRYPOINT rather than CMD allows us to define the intended script dynamically.
- You may add desired options (e.g. --multiprocessing for ptvsd) for debuggers in the dockerfile; so check them.
- Use 0.0.0.0 in your service as the host. Otherwise, e.g. if localhost is used, it will remain in docker network; and we will not be able to access it from our host.


## Utilizing Docker-Compose

By utilizing docker-compose [4], we may run multiple services and debug the ones we are interested in.
- It is a handy way when we have multiple services which need to communicate each other.
- However, in the technique we will share, we need to compose-down and compose-up all the services when we made a change.
  - Alternatively, we can manually compose-up the one we are debugging.

*Project Structure:*
- Please see the compose-example for  better understanding the project structure.
- Each service may have their own sources, requirements.txt (in-case of python) and Dockerfile.
- In the project folder, docker-compose.yml should be on the same level as the service folders.
- In the docker-compose.yml:
  - Define services
  - For each service, provide build, ports, volumes, environments etc.
  - For build, carefully provide the context and target.
    - *context* is where the dockerfile of the service exists.
    - *target* indicates which stage of the dockerfile to be build.
  - Provide volume paths carefully which can be both found in the host and container file system.
  - Ensure that ports are not colliding among services.
    - In case, change the binding port.

*Here is an example docker-compose.yml:*

```yml
version: "3.9"
services:
  service1:
    build:
      context: ./service1
      target: debugger1
    command: case.py
    ports:
      - 5678:5678
    volumes:
      - ./service1/sources:/workspace/sources
  service2:
    build:
      context: ./service2
      target: debugger2
    command: case.py
    ports:
      - 5000:5000
      - 5679:5678
    volumes:
      - ./service2/sources:/workspace/sources
```

To start debugging, (build and) run containers and then run your script from VS Code.
- Note that when the script exits or terminated, the corresponding container will go down.
- Hence, we need to re-run containers (either by compose or manually).

```shell
cd /absolute_path_till_project_folder/vscode_primitive_docker_env/compose_example
docker-compose up
```

## A Note on CMD and Services

In our example docker-compose.yml, "command" will be passed to the end of the ENTRYPOINT in the dockerfile. Similarly, when we directly execute via dockerfile, we pass the "command" as argument from the command line.
- This information is added to ENTRYPOINT.
  - It enables us to choose the desired file in our sources to debug.
  - However, when we consider services, each service will (probably) have a single entrypoint.
    - Hence, we may not need the entrypoint to be dynamic.
    - Also, we may use CMD instead of ENTRYPOINT.

Here is a few CMD examples (replace them with ENTRYPOINT in dockerfile, also we may need to add some environment variables depending on the usage):

```dockerfile
CMD python -m debugpy --listen 0.0.0.0:5678 --wait-for-client case.py
```

```dockerfile
ENV FLASK_APP=case.py
CMD python -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m flask run -h 0.0.0 -p 5000 
```

```dockerfile
CMD python -m ptvsd --host 0.0.0.0 --port 5678 --wait --multiprocessing case.py
```

```dockerfile
ENV FLASK_APP=case.py
CMD python -m ptvsd --host 0.0.0.0 --port 5678 --wait --multiprocess -m flask run -h 0.0.0 -p 5000
```

When we use flask module to run our service, we should remove any self-run in our service. E.g. remove the following from the service:

```python
if __name__ == "__main__":
    app.run(host='0.0.0.0')
```


## Run/Debug Configurations (launch.json)
- Create launch.json under ".vscode" (manually or by using vscode commands).
- It is for keeping the run/debug configurations.
  - They will be shown at run/debug tab of VS Code, which we can be chosen to run/debug the interested script in a desired environment.
- For each service (for each container to be attached), we will have a separate configuation.
- For an attach configuration, we need:
  - The type of the application
  - The connection information to the container
  - Path mappings, indicating the workspaces both in the host and in the container.

Notice that for compose-example, we have 2 services running.
- To avoid colliding ports, we defined the port of service2 as 5679.
- Also, please observe the docker-compose.yml
- launch.json should be placed under ".vscode" which is at the top level in the project workspace.

*Here is an example launch.json:*

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Basic Example DevEnv",
            "type": "python",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5678
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}/basic_example/sources",
                    "remoteRoot": "/workspace/sources"
                }
            ]
        },
        {
            "name": "Compose Example Service1 DevEnv",
            "type": "python",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5678
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}/compose-example/service1/sources",
                    "remoteRoot": "/workspace/sources"
                }
            ]
        },
        {
            "name": "Compose Example Service2 DevEnv",
            "type": "python",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5679
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}/compose-example/service2/sources",
                    "remoteRoot": "/workspace/sources"
                }
            ]
        }
    ]
}
```


## References

[1] [How to debug Docker containers! (Python + VSCode)](https://www.youtube.com/watch?v=qCCj7qy72Bg)

[2] [Debugging Python in Docker using VSCode](https://www.youtube.com/watch?v=b78Tg-YmJZI)

[3] [Use multi-stage builds](https://docs.docker.com/develop/develop-images/multistage-build/)

[4] [Compose file version 3 reference](https://docs.docker.com/compose/compose-file/compose-file-v3/)
