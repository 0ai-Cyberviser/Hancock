FROM gcr.io/oss-fuzz-base/base-builder-python

RUN apt-get update && apt-get install -y python3-dev

# Copy the project source
COPY . $SRC/hancock

WORKDIR $SRC/hancock

# Install project dependencies and atheris
RUN pip3 install --upgrade pip && \
    pip3 install -r requirements.txt && \
    pip3 install atheris

COPY fuzz/oss-fuzz/build.sh $SRC/
