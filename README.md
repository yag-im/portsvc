# portsvc

`portsvc` is a `ports` management helper service, primarily used for publishing new app releases. The current design is
flaky and requires refactoring.

The service provides two endpoints:

*Add new app release*: should be called to add a new app record into the SQL database.

*Publish new app release*: propagates the new app's data (covers, screenshots) into the CDN.

The first endpoint is called twice from [ports](https://github.com/yag-im/ports): first to update the local SQL database
for testing, and then using the production `portsvc`'s URL to publish the new app release to the production environment.

## Development

Before starting a `devcontainer`:

Mount ports_data storage on the host machine at:

    /mnt/ports_data

Make sure it contains a `media` folder with a following structure:

    media/
        covers/
        screenshots/

Create files below:

.devcontainer/secrets.env

    SQLDB_PASSWORD=***VALUE***

Then simply open the project in any IDE that supports devcontainers (VSCode is recommended), and you can begin working
right away.
