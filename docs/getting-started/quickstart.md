# Quickstart

Get a Dependency-Track to DefectDojo sync running in 5 minutes.

## What you'll need

- A running Dependency-Track instance with at least one project
- A running DefectDojo instance with an API token for a service user
- A Kubernetes cluster with the Helm chart installed (or Python 3.11+ for running locally)

## Step 1: Provision the DefectDojo token

If you don't already have one:

1. Create a dedicated DefectDojo user for Ponvara, allowed to create products and engagements and to import scans.
2. Copy that user's API v2 key.
3. Store it in OCI Vault under the key `ponvara-dd-token`.

## Step 2: Install via Helm

The chart is not published to a Helm repository, so install it from a checkout:

```bash
git clone https://github.com/MagmaMoose/ponvara
cd ponvara

helm install ponvara charts/ponvara \
  --namespace security \
  --create-namespace \
  --set image.tag=vX.Y.Z \
  --set defectDojo.url=https://defectdojo.example.com \
  --set dependencyTrack.url=https://dtrack.example.com
```

Set `image.tag` to a published release tag; the chart's default (its `appVersion`) is not one. The chart assumes your OCI Vault keys are provisioned. If they're not, the ExternalSecret cannot create the Secret and the job's pods fail to start.

## Step 3: Verify

Start a run now instead of waiting for the hourly schedule, then read its log:

```bash
kubectl create job --from=cronjob/ponvara ponvara-first-run -n security
kubectl logs -n security job/ponvara-first-run --follow
```

You should see lines like:

```text
ponvara: found 2 active Dependency-Track project(s)
ponvara: [my-service (1.4.0)] imported into DefectDojo
ponvara: [my-library] imported into DefectDojo
ponvara: done: 2 synced, 0 skipped
```

Then check DefectDojo: a new product should have appeared for each Dependency-Track project, with findings reimported.

## (Optional) Enable GitHub Advanced Security sync

Provision `ponvara-github-token` in OCI Vault, then add the second CronJob:

```bash
helm upgrade ponvara charts/ponvara --namespace security --reuse-values \
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
- Run `kubectl get externalsecret -n security` and `kubectl describe pod -n security -l app.kubernetes.io/name=ponvara`, and look for secret errors.

**No findings appear in DefectDojo:**
- Check that Dependency-Track has projects with findings.
- Check the pod logs: `kubectl logs -n security -l app.kubernetes.io/name=ponvara`.
- Verify the DefectDojo service is reachable from the cluster: `kubectl run curl-test -n security --rm -it --restart=Never --image=curlimages/curl -- curl -sI http://defectdojo-django.security.svc.cluster.local/`.

**Wrong URL or token:**
- URLs: re-run `helm upgrade ponvara charts/ponvara --namespace security --reuse-values --set ...`.
- Tokens: update the key in OCI Vault. The ExternalSecret refreshes it within an hour (`externalSecrets.refreshInterval`).

For more, see [Configuration](../reference/configuration.md) and [CLI reference](../reference/cli.md).
