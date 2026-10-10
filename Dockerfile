# Minecraft Server - Multi-Architecture Support
# Supports: ARM64 (Raspberry Pi 5), x86_64. Temurin 25 publishes no 32-bit ARM
# image, so linux/arm/v7 is not buildable.
#
# Docker buildx selects the correct base image per --platform. Eclipse Temurin
# replaces the deprecated official OpenJDK images. The JRE variant is used
# because the server only ever runs jars; nothing in the image compiles Java.

# Pinned by digest (the multi-arch index) so builds are reproducible; Renovate
# bumps the tag and digest together.
FROM eclipse-temurin:25-jre-noble@sha256:d9a39a23634650173f1e2bbc176227af9728587ecf0f4b62d53e9355cd7a19ab

ARG MINECRAFT_VERSION=26.3

# ca-certificates and curl are needed to resolve and fetch server jars,
# procps provides the pgrep that the management scripts rely on.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        procps \
        && \
    apt-get clean && \
    rm -rf /tmp/* /var/tmp/*

ENV MINECRAFT_VERSION=${MINECRAFT_VERSION} \
    MINECRAFT_JAR=server.jar \
    MEMORY_MIN=1G \
    MEMORY_MAX=2G \
    SERVER_PORT=25565 \
    SERVER_TYPE=vanilla \
    JAVA_OPTS="" \
    TZ=UTC

LABEL org.opencontainers.image.title="Minecraft Server" \
      org.opencontainers.image.description="Minecraft Server optimized for Raspberry Pi 5" \
      org.opencontainers.image.version="${MINECRAFT_VERSION}" \
      org.opencontainers.image.vendor="Minecraft Server Management" \
      org.opencontainers.image.licenses="MIT" \
      minecraft.version="${MINECRAFT_VERSION}"

RUN groupadd -r minecraft && \
    useradd -r -g minecraft -d /minecraft -s /bin/bash minecraft && \
    mkdir -p /minecraft/server \
             /minecraft/backups \
             /minecraft/plugins \
             /minecraft/config \
             /minecraft/scripts && \
    chown -R minecraft:minecraft /minecraft

WORKDIR /minecraft/server

# server.properties and eula.txt are deliberately not copied: /minecraft/server
# is a volume (bind-mounted ./data in compose), which hides anything baked in
# there, and start.sh writes eula.txt itself. Copying them only invalidated
# the layers below on every edit.
# Least-frequently-changed files first, for layer caching.
# download-server.sh resolves the jar URL for MINECRAFT_VERSION at runtime, so
# the image is not pinned to a single hard-coded download.
COPY --chown=minecraft:minecraft scripts/download-server.sh /minecraft/scripts/download-server.sh
COPY --chown=minecraft:minecraft scripts/start.sh /minecraft/start.sh

RUN chmod +x /minecraft/start.sh /minecraft/scripts/download-server.sh

# Run unprivileged
USER minecraft

EXPOSE ${SERVER_PORT}

VOLUME ["/minecraft/server", "/minecraft/backups", "/minecraft/plugins"]

# Healthy means "accepting connections on the game port", not merely "a java
# process exists" - a server stuck in startup or a crash loop would otherwise
# look healthy. start-period covers world generation on first boot.
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=180s \
    CMD bash -c 'exec 3<>/dev/tcp/127.0.0.1/${SERVER_PORT}' || exit 1

CMD ["/minecraft/start.sh"]
