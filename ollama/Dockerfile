# A CPU-only Ollama image, cut down from the official one.
#
#   docker build -t local-ai-demo-ollama ollama/
#
# The official ollama/ollama image is about 5.6 GB because it ships CUDA, MLX and Vulkan libraries
# for every GPU it supports. CPU inference needs only the `ollama` binary, the `llama-server`
# runner and the `libggml-cpu-*` variants (one per CPU generation; Ollama picks the best one at
# runtime). This multi-stage build copies exactly those files onto a plain Ubuntu base. For NVIDIA
# GPUs use compose.gpu.yaml, which switches back to the official image.

ARG OLLAMA_IMAGE=ollama/ollama:0.40.3
ARG RUNTIME_IMAGE=ubuntu:noble-20260917

# Stage 1: the official image, used only as a source of files.
FROM ${OLLAMA_IMAGE} AS official

# Stage 2: collect the CPU runtime: every top-level file in /usr/lib/ollama (libraries, the
# `llama-server` runner, license files) but none of the GPU directories (cuda_v12, cuda_v13,
# mlx_cuda_v13, vulkan). `cp -a` keeps symlinks as symlinks, so versioned .so files are not stored
# twice. The two checks at the end fail the build if a future Ollama changes this layout.
FROM ${OLLAMA_IMAGE} AS collect
RUN mkdir -p /out/usr/lib/ollama /out/usr/bin \
 && cp -a /usr/bin/ollama /out/usr/bin/ \
 && find /usr/lib/ollama -mindepth 1 -maxdepth 1 \( -type f -o -type l \) ! -name include \
      -exec cp -a {} /out/usr/lib/ollama/ \; \
 && test -x /out/usr/lib/ollama/llama-server \
 && ls /out/usr/lib/ollama/libggml-cpu-*.so > /dev/null

# Stage 3: the runtime. No package manager runs here and nothing is downloaded. The CA bundle is
# only used by ./scripts/pull-model.sh on a connected machine; the running stack sits on an
# internal network with no route to the internet.
FROM ${RUNTIME_IMAGE} AS runtime
ARG OLLAMA_VERSION=0.40.3
LABEL org.opencontainers.image.title="local-ai-demo-ollama" \
      org.opencontainers.image.description="Ollama ${OLLAMA_VERSION}, CPU-only runtime for the Local AI workshop" \
      org.opencontainers.image.version="${OLLAMA_VERSION}" \
      org.opencontainers.image.source="https://github.com/jars-demo/local-ai-demo" \
      org.opencontainers.image.licenses="MIT"
COPY --from=collect /out/usr/ /usr/
COPY --from=official /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
# Models live in /models (a named volume). Creating it here, owned by the runtime user, means a
# fresh Docker volume mounted on it inherits that ownership: no root init step is needed.
RUN groupadd --gid 10001 ollama \
 && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin ollama \
 && mkdir -p /models \
 && chown 10001:10001 /models
ENV OLLAMA_HOST=0.0.0.0:11434 \
    OLLAMA_MODELS=/models \
    HOME=/tmp
USER 10001
EXPOSE 11434
# `ollama list` is an HTTP call to the server: it passes only when the API answers.
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=6 \
  CMD ["/usr/bin/ollama", "list"]
ENTRYPOINT ["/usr/bin/ollama"]
CMD ["serve"]
