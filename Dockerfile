ARG BUILD_FROM
FROM $BUILD_FROM

# Install requirements for add-on
RUN \
  apk add --no-cache \
    python3 \
    py3-pip \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev

# Set working directory
WORKDIR /app

# Copy data for add-on
COPY requirements.txt /app/
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt

# Clean up build dependencies to keep image small
RUN apk del gcc musl-dev python3-dev libffi-dev

COPY run.sh /
COPY app.py /app/
COPY templates /app/templates/
COPY static /app/static/

RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
