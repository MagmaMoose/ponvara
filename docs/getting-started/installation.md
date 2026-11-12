# Installation

<!-- sources: charts/ponvara, pyproject.toml, .github/workflows -->

## Via Helm chart (Kubernetes)

This is the recommended method for production deployments. The chart is not published to a Helm repository, so install it from a checkout.

1. Clone the repository:

   ```bash
   git clone https://github.com/MagmaMoose/ponvara
   cd ponvara
   ```

2. Provision the required OCI Vault secrets (see [Prerequisites](prerequisites.md)):
   - `dependency-track-api-key`
   - `ponvara-dd-token`

3. Install the chart:

   ```bash
   helm install ponvara charts/ponvara \
     --namespace security \
     --create-namespace \
     --set image.tag=vX.Y.Z \
     --set defectDojo.url=https://defectdojo.example.com \
     --set dependencyTrack.url=https://dtrack.example.com
   ```

   Set `image.tag` to a published release tag. The default is the chart's `appVersion`, which is not a published image tag.

4. Verify the CronJob is created:

   ```bash
   kubectl get cronjob -n security
   kubectl describe cronjob ponvara -n security
   ```

### Enabling GitHub Advanced Security sync

To enable the GitHub Advanced Security sync, provision `ponvara-github-token` in OCI Vault and add the second CronJob:

```bash
helm upgrade ponvara charts/ponvara --namespace security --reuse-values \
  --set github.enabled=true \
  --set github.org=my-org
```

Or edit the values file:

```yaml
github:
  enabled: true
  org: my-org  # or set github.repos: "owner/repo,owner/repo2"
```

## From source

For development or testing locally:

1. Clone the repository:

   ```bash
   git clone https://github.com/MagmaMoose/ponvara
   cd ponvara
   ```

2. Install dependencies:

   ```bash
   pip install -e .
   ```

   Or using `uv`:

   ```bash
   uv sync
   ```

3. Set environment variables:

   ```bash
   export DTRACK_API_URL=https://dtrack.example.com
   export DTRACK_API_KEY=<your-key>
   export DEFECTDOJO_URL=https://defectdojo.example.com
   export DEFECTDOJO_TOKEN=<your-token>
   ```

4. Run a sync:

   ```bash
   ponvara sync          # or: uv run ponvara sync
   ```

## Via Docker image

The image is published to `ghcr.io/magmamoose/ponvara`, tagged `latest` and with each release version (`vX.Y.Z`). Its entrypoint is `ponvara` and its default command is `sync`; pass `sync-github` to run the GitHub sync instead.

```bash
docker run \
  -e DTRACK_API_URL=https://dtrack.example.com \
  -e DTRACK_API_KEY=<your-key> \
  -e DEFECTDOJO_URL=https://defectdojo.example.com \
  -e DEFECTDOJO_TOKEN=<your-token> \
  ghcr.io/magmamoose/ponvara:latest
```

## Verification

After installation, verify the setup by checking:

1. A run succeeds. Start one now instead of waiting for the schedule:

   ```bash
   kubectl create job --from=cronjob/ponvara ponvara-first-run -n security
   kubectl logs -n security job/ponvara-first-run --follow
   ```

2. Findings appear in DefectDojo in the reimported products.

3. No error messages about missing credentials in the logs.
