FROM ubuntu:20.04 AS root
# Shared libs, used to build and run SEV tool
RUN  apt-get update && apt-get install -y libssl-dev openssl uuid-dev

FROM root AS builder
RUN apt-get update && apt-get install -y autoconf gcc g++ make

COPY sev-tool /usr/src/sev-tool
WORKDIR /usr/src/sev-tool

RUN autoreconf -vif
RUN ./configure
RUN make

FROM root

COPY --from=builder /usr/src/sev-tool/src/sevtool /usr/bin/sevtool
ENTRYPOINT ["/usr/bin/sevtool"]
