FROM python:3.11-slim@sha256:cce12316475d7d56d605f76e1d811d0dc4e7227f2d4afd29951521264f504ff8

RUN apt-get update -qq \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
        gcc \
        libc6-dev \
    && python -m pip install --no-cache-dir \
        "numpy==1.26.4" \
        "pandas==2.3.3" \
        "scipy==1.17.1" \
        "openpyxl==3.1.5" \
        "matplotlib==3.11.2" \
        "scikit-learn==1.9.1" \
        "statsmodels==0.15.0" \
        "Jinja2==3.1.6" \
        "seaborn==0.13.2" \
        "pyTsetlinMachine==0.6.6" \
    && apt-get purge -y -qq --auto-remove gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONPATH=/workspace/src \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /workspace

ENTRYPOINT ["python", "-m", "cbct_artifact_analysis", "rtm-feasibility"]
