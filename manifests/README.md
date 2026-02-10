# Forex – Kubernetes manifests (K3s)

Deploy Valkey, One-Frame, Forex API (Deployment), and Forex Refresher (CronJob) to your K3s cluster.

## Connect to K3s (PetitoLabs)

From **petitolabs-infrastructure** you need an SSH tunnel and the local kubeconfig:

```bash
# 1) In petitolabs-infrastructure: start tunnel + get kubeconfig
cd ~/petitolabs/petitolabs-infrastructure
./scripts/setup-petitolabs.sh full

# 2) Use k3s (alias) or kubectl with kubeconfig
export KUBECONFIG="$PWD/k3s-kubeconfig-local.yaml"
k3s get nodes   # or: kubectl get nodes
```

To apply from **this repo** (forex):

```bash
export KUBECONFIG=~/petitolabs/petitolabs-infrastructure/k3s-kubeconfig-local.yaml
kubectl apply -f manifests/
```

Ensure the tunnel is running (`./scripts/setup-petitolabs.sh status` in the infra repo).

## Apply order

Apply all at once (namespace first is created automatically):

```bash
kubectl apply -f manifests/
```

Or step by step:

```bash
kubectl apply -f manifests/namespace.yaml
kubectl apply -f manifests/valkey-deployment.yaml
kubectl apply -f manifests/valkey-service.yaml
kubectl apply -f manifests/one-frame-deployment.yaml
kubectl apply -f manifests/one-frame-service.yaml
kubectl apply -f manifests/forex-api-deployment.yaml
kubectl apply -f manifests/forex-api-service.yaml
kubectl apply -f manifests/forex-refresher-cronjob.yaml
```

## Registry auth (optional)

If `registry.leanstax.com` requires login, create a pull secret in `forex` and uncomment `imagePullSecrets` in the API deployment and CronJob:

```bash
kubectl create secret docker-registry registry-auth-secret -n forex \
  --docker-server=registry.leanstax.com \
  --docker-username=admin \
  --docker-password='YOUR_PASSWORD'
```

Then uncomment the `imagePullSecrets` block in `forex-api-deployment.yaml` and `forex-refresher-cronjob.yaml`.

## What gets deployed

| Resource        | Name           | Description                                      |
|----------------|----------------|--------------------------------------------------|
| Namespace      | `forex`        | All resources live here                          |
| Deployment     | `valkey`       | Valkey (Redis-compatible); API + Refresher use it |
| Service        | `valkey`       | `redis://valkey.forex.svc.cluster.local:6379`    |
| Deployment     | `one-frame`    | One-Frame rate API (Refresher calls it)          |
| Service        | `one-frame`    | `http://one-frame.forex.svc.cluster.local:8080` |
| Deployment     | `forex-api`    | Forex API (2 replicas), SUBSCRIBE + GET from Valkey |
| Service        | `forex-api`    | ClusterIP :8080                                 |
| CronJob        | `forex-refresher` | Every 4 min: One-Frame → Valkey → PUBLISH rates_updated |

## Check status

```bash
kubectl -n forex get pods,svc,cronjobs
kubectl -n forex logs -l app=forex-api -f
kubectl -n forex logs -l app=valkey -f
kubectl -n forex get jobs
```

## Expose API (optional)

To reach the API from outside the cluster, add an Ingress (e.g. in your main Helm chart) pointing to `forex-api.forex.svc.cluster.local:8080`, or use port-forward:

```bash
kubectl -n forex port-forward svc/forex-api 8080:8080
# then: curl "http://localhost:8080/rates?from=USD&to=EUR"
```
