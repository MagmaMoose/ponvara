# Deployment

<!-- sources: charts/ponvara/values.yaml, charts/ponvara/templates/ -->

Ponvara is deployed as Kubernetes CronJobs via a Helm chart. Phase 1 runs two scheduled one-shot commands; future phases will add a long-lived FastAPI service.

## Helm chart overview

The chart creates:

- **CronJob** for `ponvara sync` (Dependency-Track → DefectDojo), scheduled hourly.
- **CronJob** for `ponvara sync-github` (GitHub Advanced Security → DefectDojo), scheduled every 6 hours (optional, disabled by default).
- **ExternalSecret** to materialize API keys from OCI Vault into environment variables.

## Configuration

Key Helm values:

```yaml
image:
  repository: ghcr.io/magmamoose/ponvara
  tag: "" # defaults to Chart.appVersion
  pullPolicy: IfNotPresent

schedule: "0 * * * *" # hourly for Dependency-Track sync

concurrencyPolicy: Forbid # only one pod at a time
backoffLimit: 1 # don't retry failed pods
activeDeadlineSeconds: 1800 # kill pods that run longer than 30 minutes

dependencyTrack:
  url: http://dependency-track-api-server.security.svc.cluster.local:8080

defectDojo:
  url: http://defectdojo-django.security.svc.cluster.local
  productType: "Dependency-Track"
  engagement: "Dependency Track"

github:
  enabled: false
  schedule: "0 */6 * * *" # every 6 hours

# Resource limits (house convention: request CPU, limit memory only)
resources:
  requests:
    cpu: 50m
    memory: 128Mi
  limits:
    memory: 256Mi

# Security hardening
podSecurityContext:
  runAsNonRoot: true
  runAsUser: 10001
  seccompProfile:
    type: RuntimeDefault
securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop: ["ALL"]
```

See the [full values.yaml](https://github.com/MagmaMoose/ponvara/blob/main/charts/ponvara/values.yaml) for all options.

## Secrets handling

The chart uses ExternalSecrets Operator to pull secrets from OCI Vault:

```yaml
externalSecrets:
  enabled: true
  store: oci-vault
  storeKind: ClusterSecretStore
  dtrackApiKeyRef: dependency-track-api-key
  defectDojoTokenRef: ponvara-dd-token
  githubTokenRef: ponvara-github-token # only when github.enabled=true
```

Each `*Ref` is the key name in OCI Vault. The values are materialized into environment variables that the pods read.

## Scheduling

### Dependency-Track sync

- **Default:** Every hour at `:00` (`0 * * * *`)
- **Why:** Reimport scan dedupes findings, so hourly is safe. Original legacy job was hourly.

### GitHub Advanced Security sync

- **Default:** Every 6 hours (`0 */6 * * *`)
- **Why:** GitHub advanced security doesn't change as rapidly; 6 hours reduces API quota pressure.

Both are configurable via `schedule` (Dependency-Track) and `github.schedule` (GitHub) in `values.yaml`.

## Rollback

If a sync pod crashes or gets stuck:

1. Check the pod logs:

   ```bash
   kubectl logs -n security <pod-name>
   ```

2. The pod will not be retried (`backoffLimit: 1`), but the next scheduled run will proceed.

3. If you need to force an immediate manual sync, run the image as a one-shot:

   ```bash
   kubectl run -it --rm \
     -e DTRACK_API_KEY=$DTRACK_API_KEY \
     -e DEFECTDOJO_TOKEN=$DEFECTDOJO_TOKEN \
     --image=ghcr.io/magmamoose/ponvara:0.1.0 \
     ponvara-manual \
     -- ponvara sync
   ```

## Monitoring and observability

Phase 1 has no built-in metrics. Future phases (Phase 3+) will add:

- Prometheus metrics (`/metrics` endpoint)
- ServiceMonitor for integration with Prometheus
- Health checks (`/health`)

For now, monitoring is via pod logs and DefectDojo's audit trail.

## Upgrading the chart

To upgrade Ponvara to a new version:

```bash
helm repo update magmamoose
helm upgrade ponvara magmamoose/ponvara --namespace security
```

The next scheduled run will pick up the new image. No downtime (pods are stateless).

## Uninstalling

```bash
helm uninstall ponvara --namespace security
```

This removes the CronJobs and ExternalSecret. Findings already in DefectDojo are not deleted.
