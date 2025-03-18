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

### Splunk running on a remote instance (e.g. NOVA)
```bash
# Build the TA
$~ cd genesys_cloud_ta
$~ make build
```
Copy / sync the `output/genesys_cloud_ta` folder with the remote splunk instance
> In the current environment this symlink is configured: `$SPLUNK_HOME/etc/apps/genesys_cloud_ta -> /home/splunker/genesys_cloud_ta/output/genesys_cloud_ta/`

### Documentation
Documentation made with [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) and served by a CI/CD workflow.

[MkDocs](https://www.mkdocs.org/getting-started/) comes with a built-in dev-server that lets you preview your documentation as you work on it.

```bash
# Preview your docs
$~ cd genesys_cloud_ta
$~ make run-docs
```