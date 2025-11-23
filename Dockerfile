# Minecraft Server - Multi-Architecture Support
# Optimized Dockerfile with multi-stage build support
# Supports: ARM64 (Raspberry Pi 5), ARM32 (Raspberry Pi 4), x86_64

# Build arguments
ARG MINECRAFT_VERSION=1.20.4
ARG BUILD_TYPE=standard

# Stage 1: Base image with Java and tools
# Docker buildx automatically selects the correct base image based on --platform
# For ARM64: uses arm64v8/openjdk
# For ARM32: uses arm32v7/openjdk
# For AMD64: uses openjdk (default)
FROM openjdk:21-jdk-slim AS base

# Install required packages in a single layer to reduce image size
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget \
        curl \
        ca-certificates \
        screen \
        procps \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* \
        /tmp/* \
        /var/tmp/*

# Stage 2: Runtime image (final)
FROM base AS runtime

# Set environment variables
ENV MINECRAFT_VERSION=${MINECRAFT_VERSION} \
    MINECRAFT_JAR=server.jar \
    MEMORY_MIN=1G \
    MEMORY_MAX=2G \
    SERVER_PORT=25565 \
    SERVER_TYPE=vanilla \
    JAVA_OPTS="" \
    TZ=UTC

# Create minecraft user and directories in a single layer
RUN groupadd -r minecraft && \
    useradd -r -g minecraft -d /minecraft -s /bin/bash minecraft && \
    mkdir -p /minecraft/server \
             /minecraft/backups \
             /minecraft/plugins \
             /minecraft/config && \
    chown -R minecraft:minecraft /minecraft

# Set working directory
WORKDIR /minecraft/server

# Copy configuration files
COPY --chown=minecraft:minecraft server.properties /minecraft/server/
COPY --chown=minecraft:minecraft eula.txt /minecraft/server/
COPY --chown=minecraft:minecraft scripts/start.sh /minecraft/start.sh

# Make start script executable
RUN chmod +x /minecraft/start.sh

# Switch to minecraft user (security best practice)
USER minecraft

# Expose Minecraft port
EXPOSE ${SERVER_PORT}

# Volume for persistent data
VOLUME ["/minecraft/server", "/minecraft/backups", "/minecraft/plugins"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=60s \
    CMD pgrep -f java || exit 1

# Start command
CMD ["/minecraft/start.sh"]
