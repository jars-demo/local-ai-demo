# A disposable "offline Linux server" for testing the bundle: Docker Engine (in Docker) plus the
# few OS packages a real server has (bash, coreutils, curl, iproute2). Built while connected; it is
# then started on a Docker network with `internal: true`, so neither it nor its inner Docker daemon
# can reach the internet. See scripts/airgap-simulate.sh.
FROM docker:28.5.2-dind
RUN apk add --no-cache bash coreutils curl iproute2 tar gzip
