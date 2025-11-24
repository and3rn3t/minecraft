# Minecraft Server - Multi-Architecture Support
# Optimized Dockerfile with multi-stage build support
# Supports: ARM64 (Raspberry Pi 5), ARM32 (Raspberry Pi 4), x86_64

# Build arguments
ARG MINECRAFT_VERSION=1.20.4
ARG BUILD_TYPE=standard

# Stage 1: Base image with Java and tools
# Docker buildx automatically selects the correct base image based on --platform
# Eclipse Temurin supports ARM64 (Raspberry Pi 5), ARM32 (Raspberry Pi 4), and AMD64
# Official OpenJDK images were deprecated, using Eclipse Temurin as replacement
FROM eclipse-temurin:21-jdk-jammy AS base

# Install required packages in a single layer with BuildKit cache mount for faster rebuilds
# Cache mount speeds up subsequent builds by caching apt package lists
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        procps \
        screen \
        wget \
        && \
    apt-get clean && \
    rm -rf /tmp/* \
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

# Add labels for better image metadata
LABEL org.opencontainers.image.title="Minecraft Server" \
      org.opencontainers.image.description="Minecraft Server optimized for Raspberry Pi 5" \
      org.opencontainers.image.version="${MINECRAFT_VERSION}" \
      org.opencontainers.image.vendor="Minecraft Server Management" \
      org.opencontainers.image.licenses="MIT" \
      minecraft.version="${MINECRAFT_VERSION}"

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

# Copy configuration files (grouped for better layer caching)
# Copy files that change less frequently first
COPY --chown=minecraft:minecraft scripts/start.sh /minecraft/start.sh
COPY --chown=minecraft:minecraft server.properties /minecraft/server/
COPY --chown=minecraft:minecraft eula.txt /minecraft/server/

# Make start script executable (combined with copy for efficiency)
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
