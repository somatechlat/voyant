FROM r-base:4.3.1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    && rm -rf /var/lib/apt/lists/*

# Install R packages
# jsonlite: for JSON I/O
# Rserve: for remote execution
# forecast: for time series (Phase 3 prep)
# tseries: for time series analysis
# dplyr: for data manipulation
RUN R -e "install.packages(c('jsonlite', 'Rserve', 'forecast', 'tseries', 'dplyr', 'readr'), repos='http://cran.rstudio.com/')"

# Create user
RUN useradd -m -s /bin/bash voyant
USER voyant

# Expose Rserve port
EXPOSE 6311

# Start Rserve in non-interactive mode
CMD ["R", "-e", "library(Rserve); Rserve(debug=FALSE, args='--no-save --RS-enable-remote')"]
