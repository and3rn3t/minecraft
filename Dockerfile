# Minecraft Server for Raspberry Pi 5 (ARM64)
FROM arm64v8/openjdk:21-jdk-slim

# Set environment variables
ENV MINECRAFT_VERSION=1.20.4
ENV MINECRAFT_JAR=server.jar
ENV MEMORY_MIN=1G
ENV MEMORY_MAX=2G
ENV SERVER_PORT=25565

# Create minecraft user and directories
RUN useradd -m -U -d /minecraft -s /bin/bash minecraft && \
    mkdir -p /minecraft/server /minecraft/backups /minecraft/plugins && \
    chown -R minecraft:minecraft /minecraft

# Install required packages
RUN apt-get update && \
    apt-get install -y wget curl screen && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /tmp/* /var/tmp/*

# Set working directory
WORKDIR /minecraft/server

# Switch to minecraft user
USER minecraft

# Copy configuration files
COPY --chown=minecraft:minecraft server.properties /minecraft/server/
COPY --chown=minecraft:minecraft eula.txt /minecraft/server/
COPY --chown=minecraft:minecraft start.sh /minecraft/

# Make start script executable
USER root
RUN chmod +x /minecraft/start.sh
USER minecraft

# Expose Minecraft port
EXPOSE ${SERVER_PORT}

# Volume for persistent data
VOLUME ["/minecraft/server"]

# Start command
CMD ["/minecraft/start.sh"]
