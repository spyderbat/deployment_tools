FROM python:3.11-bookworm
ARG TARGETARCH
RUN apt-get update && apt-get install -y jq
RUN pip install pyyaml toollib termtables
RUN <<EOT bash
    curl -fSsLo /usr/local/bin/kubectl "https://dl.k8s.io/release/$(curl -Ls https://dl.k8s.io/release/stable.txt)/bin/linux/${TARGETARCH}/kubectl"
    chmod a+x /usr/local/bin/kubectl
EOT
RUN <<EOF
    curl -fSsLo /usr/local/bin/kubectl-nodepools.tar.gz "https://github.com/grafana/kubectl-nodepools/releases/download/v0.0.6/kubectl-nodepools_v0.0.6_linux_${TARGETARCH}.tar.gz"
    tar -xzf /usr/local/bin/kubectl-nodepools.tar.gz -C /usr/local/bin/
    chmod a+x /usr/local/bin/kubectl-nodepools
EOF
ADD cluster_collect.py .
ADD cluster_analyze.py .
ADD toollib.py .
ADD collector.py .
ENV PYTHONUNBUFFERED=1
CMD ["python", "collector.py"]

