FROM ubuntu:latest

# Set environment variables to avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install Python and required dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    vim \
    python3 \
    python3-pip \
    python3-venv \
    postgresql-client \
    libpq-dev \
    lsb-release \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt-get/lists/*

# Set Python3 as default
RUN ln -s /usr/bin/python3 /usr/bin/python

RUN python3 -m venv /opt/devenv \
    && . /opt/devenv/bin/activate \
    && pip install poetry==1.8.3

RUN wget -O - https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/hashicorp.list \
    && apt-get update && apt-get install -y vault
 
# Set the workdir
ENV HOME=/root

ENV KUBECTL_PATH="$HOME/.vs-kubernetes/tools/kubectl"
ENV KREW_ROOT="$HOME/.krew"
ENV PATH="$PATH:$KUBECTL_PATH:${KREW_ROOT:-$HOME/.krew}/bin"

RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x kubectl  && \
    mkdir -p $KUBECTL_PATH &&\
    mv kubectl $KUBECTL_PATH/kubectl

RUN cd "$(mktemp -d)" && \
    OS="$(uname | tr '[:upper:]' '[:lower:]')" && \
    ARCH="$(uname -m | sed -e 's/^arm64$/arm64/' -e 's/^aarch64$/arm64/' -e 's/^x86_64$/amd64/')" && \
    KREW="krew-${OS}_${ARCH}" && \
    curl -fsSLO "https://github.com/kubernetes-sigs/krew/releases/latest/download/${KREW}.tar.gz" && \
    tar zxvf "${KREW}.tar.gz" && \
    ./"${KREW}" install krew && \
    echo 'export KREW_ROOT="$HOME/.krew"' >> ~/.bashrc && \
    echo 'export PATH="$KREW_ROOT/bin:$PATH"' >> ~/.bashrc && \
    export PATH="${KREW_ROOT:-$HOME/.krew}/bin:$PATH"
  

RUN kubectl krew install ns

ENV RSCRIPTS=/root/rscripts
# Update path with tools
ENV KUBECONFIG="$RSCRIPTS/kubeconfig"
ENV PATH="$PATH:$KUBECTL_PATH:/root/google-cloud-sdk/bin/"

# Install gcloud sdk 
RUN curl -sSL https://sdk.cloud.google.com | bash

# Install new auth
RUN gcloud components install gke-gcloud-auth-plugin --quiet

# Install flux
RUN curl -s https://fluxcd.io/install.sh | bash

# Install okteto
RUN curl https://get.okteto.com -sSfL | sh

RUN echo "source $RSCRIPTS/setup_dev_terminal.sh" >> /root/.bashrc
