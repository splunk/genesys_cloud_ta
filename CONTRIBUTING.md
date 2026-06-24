# Contributing
For reporting unexpected behavior, documentation gaps, entirely new features, please open an [issue](https://github.com/splunk/genesys_cloud_ta/issues).

Contributions via pull requests are also welcome:
* Create a branch for the issue / new feature
* Make your changes on your branch
* Open a [pull request](https://github.com/splunk/genesys_cloud_ta/pulls)
* Add as reviewers [@edro15](https://www.github.com/edro15) and [@ahoang-splunk](https://www.github.com/ahoang-splunk)

Thank you for your interest in this project! :heart: :rocket:

## Development Environment
### Splunk running in Docker
```bash
$~ make run
```
* In a web browser, go to http://localhost:8000/
* Log in with `admin` and `changed!`
* To reload the front-end elements in cache, after you make local changes:
    * `https://localhost:8000/en-US/_bump`
    * `https://localhost:8000/en-US/debug/refresh` in case of new files added

```bash
# Build the TA
$~ make build
# Package the TA for distribution
$~ make package
```

:warning: Restart Splunk if `.conf` files were changed

### Splunk running locally
```bash
# Build the TA
$~ make build
# Copy to Splunk Apps directory
$~ cp -R output/genesys_cloud_ta/ $SPLUNK_HOME/etc/apps/
```

### Splunk running on a remote instance
```bash
# Build the TA
$~ make build
```
Copy / sync the `output/genesys_cloud_ta` folder with the remote Splunk instance
> In the current environment this symlink is configured: `$SPLUNK_HOME/etc/apps/genesys_cloud_ta -> /home/splunker/genesys_cloud_ta/output/genesys_cloud_ta/`

## Tests
A CI/CD workflow will automatically perform tests when a PR is opened. The Genesys Cloud server is mocked using [Mockoon](https://mockoon.com/).

### Integration
Scope is to avoid introducing regressions in the `package/bin/genesyscloud_client.py`, to run these tests in your **local environment** execute:

```bash
$~ make run-tests
```

### Functional
Scope is testing the correct behaviour of the TA when executed in Splunk.

**Requirements**
- `Docker compose`, to spin up both Splunk and a Genesys Cloud Mock.

Please download and install it as per [instructions](https://docs.docker.com/compose/install/) if you don't have it on your local machine.

**Getting Started**

To execute tests in your **local environment** follow these instructions:

```bash
# 1. Build the TA -> will generate the 'output' folder
$ make build

# 2. Copy the configuration file
#    !! Create 'local' dir if it does not exist !!
$ cp ./etc/cicd/inputs.conf ./output/genesys_cloud_ta/local

# 3. Spin up the test environment
$ cd tests/vendor && \
  export APP_NAME=genesys_cloud_ta && \
  docker compose up -d

# 4. Test whether Splunk is ready
$ export EXPECTED="Ansible playbook complete, will begin streaming splunkd_stderr.log"
$ docker logs splunk 2>&1 | tail -n 20 | grep -F "$EXPECTED" && echo "Found expected line near end of logs." || (echo "Expected line not found." && exit 1)

# 5. Test connectivity between Splunk and Genesys Cloud Mock
$ docker exec splunk curl -v http://mockoon:3004/ || echo "Failed to reach Genesys Cloud Mock from Splunk"

# 6. Go back to the project root folder and run
$ make run-functional-tests
```

:point_right: For debugging purposes, you can enable logging to stdout by adding `-o log_cli=true` to the pytest command executed in `run-functional-tests`

## Release the Add-on
A CI/CD workflow will automatically create a release. To trigger it:

- Bump the Add-On version according to [Semantic Versioning](http://semver.org/) in `package/app.manifest` and `globalConfig.json`
- Update the `CHANGELOG` following [guidelines](#changelog)
- Push to `main`

On push to `main`, the following checks will be executed before releasing a new version of the Add-On:

- **Build**: Creates app package
- **Sanity Check**: Validates version consistency between the `CHANGELOG` file and the Add-On. They must match.

### Changelog
A `CHANGELOG.md` file is used to document changes between versions. The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).

## Documentation
Documentation made with [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) and served by a CI/CD workflow.

[MkDocs](https://www.mkdocs.org/getting-started/) comes with a built-in dev-server that lets you preview your documentation as you work on it.

```bash
# Preview your docs
$~ make run-docs
```