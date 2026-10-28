:point_right: Please ensure your pull request (PR) adheres to our [Contribution Guidelines](https://github.com/splunk/genesys_cloud_ta/blob/main/CONTRIBUTING.md) :point_left:

## Pull Request Checklist

#### Please check if your PR fulfills the following requirements:
- [ ] Testing of all the changes has been performed (for bug fixes / features)
- [ ] The `docs/*` have been reviewed and updated if needed (for bug fixes / features)
- [ ] Provide release notes as part of the PR submission which describe high level points about the changes
- [ ] Verify all checks are passing
- [ ] Do NOT use the `main` branch of the forked repo. Create separate feature branch for raising the PR

## Pull Request Type

#### Please check the type of change your PR introduces:
- [ ] Bugfix
- [ ] Feature
- [ ] Code style update (formatting, renaming)
- [ ] Refactoring (no functional changes, no api changes)
- [ ] Documentation
- [ ] Other (please describe):

## Security Considerations (REQUIRED)
- [ ] If you are adding a new modular input to the add-on
    - [ ] Please document in the `docs/ConfigureGenesysCloud/index.md` permissions and OAuth scopes needed to fetch data from the integrated endpoint(s)
    - [ ] Please add opportune tests and update the vendor mock

## Release Notes (REQUIRED)
- Provide release notes as part of the PR submission which describe high level points about the changes for the upcoming release.

---
Thanks for contributing! :heart: