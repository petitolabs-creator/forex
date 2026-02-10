FROM eclipse-temurin:17-jdk AS builder

WORKDIR /build

# Install SBT
RUN apt-get update && \
    apt-get install -y curl && \
    echo "deb https://repo.scala-sbt.org/scalasbt/debian all main" | tee /etc/apt/sources.list.d/sbt.list && \
    echo "deb https://repo.scala-sbt.org/scalasbt/debian /" | tee /etc/apt/sources.list.d/sbt_old.list && \
    curl -sL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x2EE0EA64E40A89B84B2DF73499E82A75642AC823" | apt-key add && \
    apt-get update && \
    apt-get install -y sbt && \
    rm -rf /var/lib/apt/lists/*

# Copy project files
COPY build.sbt .
COPY project project/
COPY src src/

# Compile the project and collect dependencies
RUN sbt clean compile && \
    mkdir -p /build/lib && \
    find /root/.ivy2 /root/.cache/coursier -name "*.jar" -type f 2>/dev/null | xargs -I {} cp {} /build/lib/ 2>/dev/null || true

# Create runtime image
FROM eclipse-temurin:17-jre

WORKDIR /app

# Copy compiled classes and dependencies
COPY --from=builder /build/target/scala-2.13/classes /app/classes
COPY --from=builder /build/lib /app/lib

# Copy configuration
COPY --from=builder /build/src/main/resources /app/resources

# Create classpath from lib directory
RUN find /app/lib -name "*.jar" | tr '\n' ':' > /app/classpath.txt

# Create entrypoint script
RUN echo '#!/bin/bash\n\
CP=$(cat /app/classpath.txt):/app/classes:/app/resources\n\
if [ "$1" = "refresher" ]; then\n\
  exec java -cp "$CP" forex.RefresherMain\n\
elif [ "$1" = "api" ]; then\n\
  exec java -cp "$CP" forex.Main\n\
else\n\
  echo "Usage: $0 {refresher|api}"\n\
  exit 1\n\
fi' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh", "api"]
