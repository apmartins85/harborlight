# Harborlight

![Harborlight pixel-art lighthouse](assets/harborlight-pixel.svg)

A lightweight status page for real Kubernetes services. The Killercoda example deploys three real open-source applications: **ntfy**, **IT-Tools**, and **CyberChef**. Harborlight checks them over Kubernetes DNS and shows availability and response times.

## What runs

| Component | Helm release | Namespace | Purpose |
| --- | --- | --- | --- |
| ntfy | `ntfy` | `notifications` | Real HTTP publish/subscribe notification server |
| IT-Tools | Kubernetes manifest | `utilities` | Developer utilities: JSON, hashes, UUIDs, conversions |
| CyberChef | Kubernetes manifest | `utilities` | Browser-based encoding, decoding, and data recipes |
| Harborlight | `demo` | `harborlight` | Checks ntfy's `/v1/health` endpoint |

The repository contains the dashboard and one compact Killercoda example. ntfy uses its published Helm chart; the two static web apps share one Kubernetes manifest and use upstream images.

ntfy's [official installation guide](https://docs.ntfy.sh/install/#helm) documents the **community-maintained HelmForge chart**. It is not an official ntfy-maintained chart. This example pins chart version **1.6.2**, which specifies upstream image `binwiederhier/ntfy:v2.31.1`. Chart source: [helmforgedev/charts](https://github.com/helmforgedev/charts/tree/main/charts/ntfy). Application source: [binwiederhier/ntfy](https://github.com/binwiederhier/ntfy).

## 1. Start Killercoda

Open the [Kubernetes playground](https://killercoda.com/playgrounds/scenario/kubernetes), sign in, and start the environment. In its terminal:

```sh
kubectl get nodes
helm version
```

Both nodes should be ready. If Helm is missing, follow its [official installation instructions](https://helm.sh/docs/intro/install/).

## 2. Clone and deploy the lab

```sh
git clone https://github.com/apmartins85/harborlight.git
cd harborlight
sh examples/killercoda/deploy.sh
```

If you already cloned the repository, run `git pull` from its directory before deploying. The script installs ntfy from its chart repository, applies the two utility apps, waits for readiness, then installs/upgrades Harborlight. `--reset-values` clears settings from previous installations.

Equivalent commands:

```sh
helm repo add helmforge https://repo.helmforge.dev --force-update
helm repo update helmforge
helm upgrade --install ntfy helmforge/ntfy --version 1.6.2 \
  --namespace notifications --create-namespace \
  -f examples/killercoda/ntfy-values.yaml --wait --timeout 180s
kubectl apply -f examples/killercoda/utilities.yaml
kubectl -n utilities rollout status deployment/it-tools --timeout=180s
kubectl -n utilities rollout status deployment/cyberchef --timeout=180s
helm upgrade --install demo ./charts/harborlight \
  --namespace harborlight --create-namespace \
  --reset-values --wait --timeout 120s
kubectl -n notifications get pods,svc
kubectl -n harborlight get pods,svc
```

This lab disables ntfy persistence so it works without a storage provisioner. Its data disappears when the pod is replaced. The ntfy application is real; the deployment settings are intentionally temporary for Killercoda.

## 3. Open Harborlight

The default dashboard Service uses NodePort **30080**:

1. Open **☰ → Traffic / Ports** in the playground.
2. Under **Host 1 → Custom Ports**, enter **30080**.
3. Click **Access**. Harborlight opens in a separate tab.
4. After the first check, **ntfy notifications**, **IT-Tools**, and **CyberChef** should show **Operational**.

Do not reuse another session's URL: Killercoda generates a new hostname for every environment.

## 4. Port-forward Harborlight (alternative)

In a Killercoda terminal:

```sh
kubectl -n harborlight port-forward --address 0.0.0.0 svc/demo-harborlight 8080:80
```

Leave that terminal running. You should see `Forwarding from 0.0.0.0:8080 -> 8080`. Open **☰ → Traffic / Ports → Host 1 → 8080**. Use a second terminal for other commands. Ctrl+C stops forwarding.

For an internal-only dashboard Service, first run:

```sh
helm upgrade demo ./charts/harborlight -n harborlight --set service.type=ClusterIP --wait
```

The forwarding command works with either Service type. `--address 0.0.0.0` lets the Killercoda proxy connect; outside this lab, omit it to bind only to localhost. If a pod restarts and the forward stops, rerun the command. Your computer's `localhost:8080` is not the remote playground; use **Traffic / Ports**.

## 5. Open the real ntfy web app

In a separate Killercoda terminal:

```sh
kubectl -n notifications port-forward --address 0.0.0.0 svc/ntfy 8082:80
```

Keep it running, then open **Traffic / Ports → Host 1 → Custom Ports → 8082 → Access**. The ntfy web interface opens. Subscribe to a topic named `harborlight-lab` on this instance. Browser notifications are optional; the topic page displays messages without enabling them.

Publish a test message from inside the cluster. This request runs in the Harborlight pod so Kubernetes DNS resolves the ntfy Service:

```sh
kubectl -n harborlight exec deployment/demo-harborlight -- python -c \
  'import urllib.request; r=urllib.request.Request("http://ntfy.notifications.svc.cluster.local/harborlight-lab",data=b"Hello from Kubernetes",headers={"Title":"Harborlight test"}); print(urllib.request.urlopen(r, timeout=5).read().decode())'
```

Or, while the ntfy port-forward is active, use `curl -d 'Hello from Kubernetes' http://localhost:8082/harborlight-lab` in another Killercoda terminal. This sends only to your lab instance, not the public ntfy.sh service.

## Open IT-Tools and CyberChef

The utility apps use pinned images published by their own projects:

| App | Upstream image | License | Killercoda port |
| --- | --- | --- | --- |
| [IT-Tools](https://github.com/CorentinTh/it-tools) | `ghcr.io/corentinth/it-tools:2024.10.22-7ca5933` | GPL-3.0 | 8083 |
| [CyberChef](https://github.com/gchq/CyberChef) | `ghcr.io/gchq/cyberchef:11.5.0` | Apache-2.0 | 8084 |

Run each port-forward in its own Killercoda terminal:

```sh
kubectl -n utilities port-forward --address 0.0.0.0 svc/it-tools 8083:80
```

```sh
kubectl -n utilities port-forward --address 0.0.0.0 svc/cyberchef 8084:80
```

Then open **Traffic / Ports → Host 1 → Custom Ports**, enter **8083** or **8084**, and click **Access**. Keep the corresponding terminal running. Try IT-Tools' JSON formatter or CyberChef's Base64 conversion. Both apps serve browser tools and need no database or persistent volume.

To test an independent outage, run `kubectl -n utilities scale deployment/it-tools --replicas=0`. Only IT-Tools should become unavailable in Harborlight. Restore it with `--replicas=1`. The same procedure works for CyberChef.

## 6. Test a real outage and recovery

Stop ntfy:

```sh
kubectl -n notifications scale deployment/ntfy --replicas=0
```

After pod termination and the next check, Harborlight shows ntfy as unavailable. Allow up to about one minute. Restore it:

```sh
kubectl -n notifications scale deployment/ntfy --replicas=1
kubectl -n notifications rollout status deployment/ntfy --timeout=120s
```

After readiness and the next check cycle, Harborlight returns to operational. Restart the ntfy port-forward if it stopped when its pod disappeared. The temporary ntfy message cache is lost when its pod is removed.

## Screenshots from Killercoda

The following screenshots show the initial ntfy scenario; a fresh deployment also lists IT-Tools and CyberChef.

### Application operational

![Harborlight monitoring the real ntfy application](docs/screenshots/ntfy-up.jpg)

### Application outage

![Harborlight detecting an ntfy outage](docs/screenshots/ntfy-issue.jpg)

## Monitor other services

Create `my-values.yaml`:

```yaml
services:
  - name: ntfy notifications
    url: http://ntfy.notifications.svc.cluster.local/v1/health
  - name: My API
    url: http://my-api.default.svc.cluster.local:8080/health
```

```sh
helm upgrade demo ./charts/harborlight -n harborlight -f my-values.yaml --wait
```

Harborlight checks every 15 seconds by default, with a three-second socket timeout per target. The page refreshes every five seconds. HTTP 200–399 responses count as operational; redirects are followed. This measures HTTP availability, not delivery of notifications or database health, and does not inspect ntfy's JSON `healthy` field. The publish/receive exercise tests application behavior separately.

## Development and troubleshooting

```sh
helm lint ./charts/harborlight
helm template demo ./charts/harborlight -n harborlight > /tmp/harborlight.yaml
kubectl -n harborlight logs deployment/demo-harborlight
kubectl -n notifications logs deployment/ntfy
kubectl -n notifications describe pods
```

Edit the dashboard source directly in `charts/harborlight/files/app.py` and `index.html`. These are the only copies. The source is mounted through ConfigMaps for a build-free lab. Chart configuration changes trigger a dashboard restart. Failed monitored checks do not restart Harborlight. If port 30080 is allocated, set `service.nodePort=30081` and open that port instead. Image pulls require access to Docker Hub and GHCR.

## Cleanup

```sh
helm uninstall demo -n harborlight
helm uninstall ntfy -n notifications
kubectl delete -f examples/killercoda/utilities.yaml
```

The utilities namespace is removed along with its lab apps; the Helm release namespaces remain. Killercoda sessions are temporary. This lab has anonymous ntfy read/write access; use test messages only. Persistent storage, authentication, TLS, and backups should be configured for a lasting deployment.

## Open-source licenses

Harborlight uses the [MIT license](LICENSE). ntfy and the HelmForge chart are separate upstream projects; their own [application license](https://github.com/binwiederhier/ntfy) and [chart license](https://github.com/helmforgedev/charts) apply. IT-Tools uses GPL-3.0 and CyberChef uses Apache-2.0; their upstream licenses apply to their images.
