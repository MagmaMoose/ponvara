# Installation

## Via Helm chart (Kubernetes)

This is the recommended method for production deployments.

1. Add the MagmaMoose Helm repository (if not already added):

   ```bash
   helm repo add magmamoose https://magmamoose.github.io/helm-charts
   helm repo update
   ```

2. Provision the required OCI Vault secrets (see [Prerequisites](prerequisites.md)):
   - `dependency-track-api-key`
   - `ponvara-dd-token`

3. Install the chart:

   ```bash
   helm install ponvara magmamoose/ponvara \
     --namespace security \
     --create-namespace \
     --set defectDojo.url=https://defectdojo.magmamoose.com \
     --set dependencyTrack.url=https://dtrack.magmamoose.com
   ```

4. Verify the CronJob is created:

   ```bash
   kubectl get cronjob -n security
   kubectl describe cronjob ponvara -n security
   ```

### Enabling GitHub Advanced Security sync

To enable the GitHub Advanced Security sync, add the second CronJob:

```bash
helm install ponvara ... \
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
   ponvara sync
   ```

## Via Docker image

The image is published to `ghcr.io/magmamoose/ponvara:latest`.

```bash
docker run \
  -e DTRACK_API_URL=https://dtrack.example.com \
  -e DTRACK_API_KEY=<your-key> \
  -e DEFECTDOJO_URL=https://defectdojo.example.com \
  -e DEFECTDOJO_TOKEN=<your-token> \
  ghcr.io/magmamoose/ponvara:latest \
  ponvara sync
```

## Verification

After installation, verify the setup by checking:

1. The CronJob runs successfully:

   ```bash
   kubectl logs -n security -l app=ponvara --tail=50
   ```

2. Findings appear in DefectDojo in the reimported products.

3. No error messages about missing credentials in the logs.
