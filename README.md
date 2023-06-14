[![AWS Deploy](https://github.com/czech-it-net/exitrock.cz/actions/workflows/main.yml/badge.svg?branch=main)](https://github.com/czech-it-net/exitrock.cz/actions/workflows/main.yml)

# exitrock.cz
Static band website

Basic info - contact, links to social, set list

## Technical info
Repo has LFS enabled - install git-lfs locally before cloning

### Infrastructure
Served from AWS

1. Content of src directory is synchronized to S3 bucket
2. Domain and subdomains have DNS in Route53 hosted zone and AWS issued auto-renewed TLS certificates
3. Cloudfront distribution is providing cache and TLS termination
4. Subdomains are directed to src subdirectories via CloudFront viewer-request function
