# Quickstart

Get a Dependency-Track to DefectDojo sync running in 5 minutes.

## What you'll need

- A running Dependency-Track instance with at least one project
- A running DefectDojo instance with an API token for a service user
- A Kubernetes cluster with the Helm chart installed (or Python 3.11+ for running locally)

## Step 1: Provision the DefectDojo token

If you don't already have one, create a new service-user API token in DefectDojo:

1. Go to DefectDojo **Admin → Users**.
2. Click **Add User**.
3. Set the username to `ponvara` and mark it as an **API user**.
4. Copy the token that DefectDojo generates.
5. Store it in OCI Vault under the key `ponvara-dd-token`.

## Step 2: Install via Helm

```bash
helm repo add magmamoose https://magmamoose.github.io/helm-charts
helm repo update

helm install ponvara magmamoose/ponvara \
  --namespace security \
  --create-namespace \
  --set defectDojo.url=https://defectdojo.example.com \
  --set dependencyTrack.url=https://dtrack.example.com
```

The chart assumes your OCI Vault keys are provisioned. If they're not, the pods will fail to start with a vault error.

## Step 3: Verify

Wait a moment for the CronJob to schedule, then check the logs:

```bash
kubectl logs -n security -l app=ponvara --tail=50
```

You should see lines like:

```text
ponvara: syncing Dependency-Track projects to DefectDojo
ponvara: project_1: created product in DefectDojo
ponvara: done
```

Then check DefectDojo: a new product should have appeared for each Dependency-Track project, with findings reimported.

## (Optional) Enable GitHub Advanced Security sync

Add the second CronJob:

```bash
helm upgrade ponvara magmamoose/ponvara \
  --set github.enabled=true \
  --set github.org=my-org
```

Ponvara will now run `sync-github` every 6 hours (or set `github.schedule` to change the cron expression).

## What happens next

- The Dependency-Track sync runs **hourly**. Each run reimports the latest findings from Dependency-Track.
- The GitHub sync (if enabled) runs **every 6 hours** and reimports code scanning, Dependabot, and secret scanning alerts.
- Findings are deduplicated by DefectDojo's `reimport-scan` endpoint, so re-runs don't create duplicates.

## Troubleshooting

**Pod fails to start:**
- Check that your OCI Vault keys (`dependency-track-api-key`, `ponvara-dd-token`) are provisioned.
- Run `kubectl describe pod -n security` and look for vault-related errors.

**No findings appear in DefectDojo:**
- Check that Dependency-Track has projects with findings.
- Check the pod logs: `kubectl logs -n security -l app=ponvara`.
- Verify the DefectDojo service is reachable from the cluster: `kubectl run --rm -it --image=curlimages/curl -l app=test -- curl http://defectdojo-django.security.svc.cluster.local/health/`.

**Wrong URL or token:**
- Edit the Helm values and re-run `helm upgrade ponvara magmamoose/ponvara --set ...`.

For more, see [Configuration](../reference/configuration.md) and [CLI reference](../reference/cli.md).
