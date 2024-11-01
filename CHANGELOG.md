# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
### Deprecated
### Removed
### Fixed


## [0.10.0]

### Added
- Added a new input argument *granule-list-file* to input a specific list of granules to process,
  and ignore start-date, end-date, cycles, etc
  - List can be a list of GranuleURs or granule concept-IDs
- Update db size from t2.micro to t3.micro
- Made arguments *--cumulus-configurations* and *--default-message-config* optional in preview mode
### Deprecated
### Removed
### Fixed


## [0.9.0]

### Added
- Updated regression and memory profiling scripts
- Updated CLI preview message to note that messages sent count might not be same as actual execution
- Moved repo to Github.com [hitide-backfill-tool](https://github.com/podaac/hitide-backfill-tool)
  - Updated cumulus cluster template
  - Made default_message_config.json an argument file
  - Implemented Github Actions to Build and Deploy to AWS
### Deprecated
### Removed
### Fixed


## [0.8.1]

### Added
- Updated to use Github.com [hitide-backfill-lambdas](https://github.com/podaac/hitide-backfill-lambdas) repo
- Updated cluster settings
### Deprecated
### Removed
- Removed using hitide-backfill-post-step and hitide-backfill-sqs-to-step
### Fixed


## [0.8.0]

### Added
- Updated to terraform 1.5.3
- Added Dmrpp Lambda and update to 5.0.1
- Updated tig to 0.12.0 to allow terraform 1.5.3 update
- Updated forge to 0.11.0 to allow terraform 1.5.3 update
- Updated post to cmr and hyrax metadata updates lambda modules from cumulus 18.2.0
- Updated postworkflow normalizer now it computes a workflow flag for ecs_lambda to help determine to use lambda or ecs based on a granule size.
- Updated to use Github.com [cumulus-postworkflow-normalizer](https://github.com/podaac/cumulus-postworkflow-normalizer) repo
### Deprecated
### Removed
### Fixed


## [0.7.0]

### Added
- Added forge-py to generate footprints for specific collections 
- Update to deploy
### Deprecated
### Removed
### Fixed


## [0.6.0]

### Added
- Updated tig to 0.11.0
- Updated to have a regression test to call backfilling on all forge/tig collections
- Added a sort order for cmr based on date
- Changed tig memory to 3.5 gb
- Added in a memory profiler for lambda functions maily for tig
- updated message_visibility_timeout to 18000
### Deprecated
### Removed
### Fixed


## [0.5.1]

### Added
- Updated tig to 0.10.0
### Deprecated
### Removed
### Fixed


## [0.5.0]

### Added
- Updated tig to 0.9.0 
- Updated forge 0.10.0
- Updated backfill-post to 0.3.0
- Updated backfill-sqs-to-step to 0.3.0
- Updated how tig, forge, backfill_post_step, and backfill_sqs_to_step is deployed to each environment with override variables
- Added output granule count with both footprint and bbox
- Renamed monthly_counts to monthly_results.  Now return full granule object instead of just the count
- Updated python dependency libraries
### Deprecated
### Removed
### Fixed


## [0.4.1]

### Added
- Updated service uat disk space to from 100 GB to 600 GB
- Updated number of ec2 to 2 for dmrpp
- Added a replay script to move messages from dead letter queue to regular queue
- Updated number of ec2 servers to t3.micro and 50 with 50 gb each
- Updated python libraries
- Updated tig fargate memory to 16 gb
- Updated to cumulus 16.1.2
- Updated CMA layer to 2.0.3
- Updated forge 0.9.0 and tig 0.8.0
- Updated library versions to latest to fix security issues
- Added cumulus normalizer to filter out unecessary data for forge tig dmrpp workflows
### Deprecated
### Removed
### Fixed

## [0.4.0]

### Added
- Updated the cmr request to retry on failures
- Updated Jenkins docker image to a snyk base image
- Added output granule concept IDs for missing images, footprints, and dmrpps
- Updated forge 0.8.0 and tig 0.7.0
- Updated library versions to latest to fix security issues
### Deprecated
### Removed
### Fixed

## [0.3.4]

### Added
- Fix dmrpp workflow to keep revision id 
- Add cycle parameter to cli
- Update Updated dmrpp-generator v4.0.9
- Update tig to public 0.6.2
- Update forge to public 0.7.5
- Add a monthly count totals table output by Year-Month
### Deprecated
### Removed
### Fixed


## [0.3.3]

### Added
- **PODAAC-5418**
  - Add ability to backfil swot collections
- **PODAAC-5320**
  - Add timeout to forge and tig fargate steps
- **PODAAC-5321**
  - Allow tig and forge fargate to scale to 100
- **PODAAC-5280**
  - Check forge/tig configuration before backfilling collection to make sure we can for footprints
- **update aggregator**
  - Updated cumulus-metadata-aggregator v8.4.0
- **PODAAC-5274**
  - update post step lambda to make raw sql query count
- **update_ebs**
  - turn on docker debug mode
  - update ops ebs to 600 gb
  - change ops running container to 50
  - update jenkins to deploy to ops on changelog
- **update dmrpp-generator**
  - Updated dmrpp-generator v4.0.7
- **update tig and forge**
  - Updated tig v0.5.0
  - Updated forge v0.7.0
### Deprecated
### Removed
### Fixed
### Security


## [0.3.2]

### Added
- **update_ebs
  - update ebs volume type to gp3 and ops size to 400gb
### Deprecated
### Removed
### Fixed
### Security


## [0.3.1]

### Added
- **PODAAC-5126**
  - Added DMRPP file generation and CMR OpenDAP URL update capability
- **Fargate Changes**
  - Added fargate terraform resources, added in forge and tig fargate
- **PODAAC-5128**
  - Add DMRPP workflow.
- **PODAAC-5143**
  - added ECS facility for docker image to run upon
- **PODAAC-5229**
  - update post lambda to process dmrpp workflows
### Deprecated
### Removed
### Fixed
### Security


## [0.2.0]

### Added
- **PODAAC-4881**
  - Add script failed_workflow.py to find unique errors in step function workflows
- **Update jenkins**
  - Update jenkins branch to have deploy sit and uat triggers
  - Now using tig v0.4.0, forge v0.5.1, and cumulus-metadata-aggregator v8.1.0
### Deprecated
### Removed
### Fixed
### Security


## [0.1.0]

### Added
- **PODAAC-4425**
  - Initial development of cli tool
  - Includes backfill and create-backfill-config scripts
- **PODAAC-4424**
  - Implementation of hitide backfill terraform infrastructure.
### Deprecated
### Removed
### Fixed
- **PODAAC-4771**
  - Properly parses s3 bucket information from s3 urls that
    contain multiple directories in the path.
### Security
