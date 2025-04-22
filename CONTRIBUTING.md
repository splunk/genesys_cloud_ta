# Contributing
For reporting unexpected behavior, documentation gaps, entirely new features, please open an [issue](https://github.com/splunk/genesys_cloud_ta/issues)

Contributions via pull requests are also welcome:
* Create a branch for the issue / new feature
* Make your changes on your branch
* Open a [pull request](https://github.com/splunk/genesys_cloud_ta/pulls)
* Add as reviewers [@edro15](https://www.github.com/edro15) and [@ahoang-splunk](https://www.github.com/ahoang-splunk)

Thank you for your interest in this project! :heart: :rocket:

## Development Environment
### Splunk running in Docker
```bash
$~ cd genesys_cloud_ta
$~ make run
```
* In a web browser, go to http://localhost:8000/
* Login with `admin` and `changed!`
* To reload the front-end elements in cache, after you make local changes:
    * `https://localhost:8000/en-US/_bump`
    * `https://localhost:8000/en-US/debug/refresh` in case of new files added

```bash
# Build the TA
$~ cd genesys_cloud_ta
$~ make build
# Package the TA for distribution
$~ cd genesys_cloud_ta
$~ make package
```

:warning: Restart Splunk if `.conf` files were changed

### Splunk running locally
```bash
# Build the TA
$~ cd genesys_cloud_ta
$~ make build
# Copy to Splunk Apps directory
$~ cp -R output/genesys_cloud_ta/ $SPLUNK_HOME/etc/apps/
```

### Splunk running on a remote instance
```bash
# Build the TA
$~ cd genesys_cloud_ta
$~ make build
```
Copy / sync the `output/genesys_cloud_ta` folder with the remote splunk instance
> In the current environment this symlink is configured: `$SPLUNK_HOME/etc/apps/genesys_cloud_ta -> /home/splunker/genesys_cloud_ta/output/genesys_cloud_ta/`

## Tests
A CI/CD workflow will automatically perform tests when a PR is opened. The Genesys Cloud server is mocked using [Mockoon](https://mockoon.com/).

To execute tests on your local environment:
* Install Mockoon and import `tests/genesyscloud_mock.json`
* Run the server
    > By default it will listen on `localhost:3004`

### Integration
Scope is avoid introducing regressions in the `package/bin/genesyscloud_client.py`

```bash
$~ cd genesys_cloud_ta
$~ make run-tests
```

### Functional
Scope is testing the correct behaviour of the TA when executed in Splunk.

Additional requirements to run these tests on your local environment:
* Configure `tests/pytest.ini` to connect to your Splunk instance
    ```bash
        $~ cd tests
        $~ python -m pytest --help
            [...]
            Splunk Options:
                --splunk-url=SPLUNK_URL
                    The url of splunk instance, defaults to localhost
                --username=USERNAME   Splunk username, defaults to admin
                --password=PASSWORD   Splunk password, defaults to password
                --splunkd-port=SPLUNKD_PORT
                    Splunk Management port, defaults to 8089
    ```
* Install the TA in your Splunk instance
* Copy `etc/cicd/inputs.conf` in `$SPLUNK_HOME/etc/apps/genesys_cloud_ta/local`
    > Create `local` dir if it does not exist


```bash
$~ cd genesys_cloud_ta
$~ make run-functional-tests
```

:point_right: For debugging purposes, you can enable logging to stdout by adding `-o log_cli=true` to the pytest command executed in `run-functional-tests`

## Documentation
Documentation made with [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) and served by a CI/CD workflow.

[MkDocs](https://www.mkdocs.org/getting-started/) comes with a built-in dev-server that lets you preview your documentation as you work on it.

```bash
# Preview your docs
$~ cd genesys_cloud_ta
$~ make run-docs
```