# portsvc

`portsvc` is a `ports` management helper service, primarily used for publishing new app releases. The current design is
flaky and requires refactoring.

The service provides two endpoints:

*Add new app release*: should be called to add a new app record into the SQL database.

*Publish new app release*: propagates the new app's data (covers, screenshots) into the CDN.

The first endpoint is called twice from [ports](https://github.com/yag-im/ports): first to update the local SQL database
for testing, and then using the production `portsvc`'s URL to publish the new app release to the production environment.

## Development

### Prerequisite

Mount ports_data storage on the host machine at:

    /mnt/ports_data

Make sure it contains a `media` folder with a following structure:

    media/
        covers/
        screenshots/

Create *.devcontainer/secrets.env* file:

    SQLDB_PASSWORD=***VALUE***

The following devcontainers should be up and running:

    sqldb

Then simply open this project in any IDE that supports devcontainers (VSCode is recommended).
